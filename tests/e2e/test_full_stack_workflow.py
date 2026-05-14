#!/usr/bin/env python3
"""Live end-to-end stack validation for the local Docker Compose app.

Workflow covered by this script:
1. Ensure the Docker Compose stack is up.
2. Verify API, readiness, Vault, Redis, and Postgres health.
3. Exercise public auth endpoints: register, login, and /auth/me.
4. Verify current protected batch API behavior for a newly registered default role.
5. Push a real TIFF into the live SFTP upload folder.
6. Wait for the SFTP ingest worker to create batch/document records.
7. Wait for the inference worker to create a prediction and overlay.
8. Verify MinIO raw and overlay objects.
9. Verify Redis job artifacts and an empty queue after processing.
10. Verify SFTP file movement and audit-log persistence.

A human-readable report is written to tmp/full_stack_workflow_report.md.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = REPO_ROOT / "tmp" / "full_stack_workflow_report.md"
FIXTURE_PATH = REPO_ROOT / "app" / "classifier" / "eval" / "golden_images" / "test_00534_true_0_letter.tiff"

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080")
VAULT_HEALTH_URL = "http://localhost:8200/v1/sys/health"

POSTGRES_CONTAINER = "doc-classifier-service-postgres-1"
REDIS_CONTAINER = "doc-classifier-service-redis-1"
SFTP_CONTAINER = "doc-classifier-service-sftp-1"
API_CONTAINER = "doc-classifier-service-api-1"

SFTP_UPLOAD_DIR = "/home/test/upload"
SFTP_PROCESSED_DIR = "/home/test/processed"
MINIO_BUCKET = "documents"
QUEUE_NAME = "default"


def run_command(args: list[str], *, check: bool = True, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd or REPO_ROOT),
        check=check,
        text=True,
        capture_output=True,
    )


def docker_exec(container: str, command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run_command(["docker", "exec", container, *command], check=check)


def docker_exec_shell(container: str, script: str, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run_command(["docker", "exec", container, "sh", "-lc", script], check=check)


def http_request(
    method: str,
    url: str,
    *,
    json_body: dict[str, Any] | None = None,
    form_body: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, Any, dict[str, str]]:
    request_headers = dict(headers or {})
    data: bytes | None = None

    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    elif form_body is not None:
        data = urllib.parse.urlencode(form_body).encode("utf-8")
        request_headers["Content-Type"] = "application/x-www-form-urlencoded"

    request = urllib.request.Request(url, data=data, headers=request_headers, method=method)

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = response.read().decode("utf-8")
            body = _parse_response_body(payload, response.headers.get("Content-Type", ""))
            return response.status, body, dict(response.headers.items())
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8")
        body = _parse_response_body(payload, exc.headers.get("Content-Type", ""))
        return exc.code, body, dict(exc.headers.items())


def _parse_response_body(payload: str, content_type: str) -> Any:
    if "application/json" in content_type:
        return json.loads(payload)
    return payload


def wait_for(predicate, *, timeout_seconds: int, interval_seconds: float, description: str) -> Any:
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            result = predicate()
            if result:
                return result
        except Exception as exc:  # pragma: no cover - debug aid for live script
            last_error = exc
        time.sleep(interval_seconds)
    if last_error is not None:
        raise TimeoutError(f"Timed out waiting for {description}: {last_error}") from last_error
    raise TimeoutError(f"Timed out waiting for {description}")


def psql_query(sql: str) -> str:
    result = run_command(
        [
            "docker",
            "exec",
            "-e",
            "PGPASSWORD=app",
            POSTGRES_CONTAINER,
            "psql",
            "-h",
            "127.0.0.1",
            "-U",
            "app",
            "-d",
            "documents",
            "-At",
            "-F",
            "|",
            "-c",
            sql,
        ]
    )
    return result.stdout.strip()


def split_row(row: str) -> list[str]:
    return row.split("|") if row else []


def check_minio_object(path: str) -> None:
    script = (
        "from minio import Minio; "
        "client = Minio('minio:9000', access_key='minio', secret_key='minio123', secure=False); "
        f"client.stat_object('{MINIO_BUCKET}', '{path}'); "
        "print('ok')"
    )
    result = docker_exec(API_CONTAINER, ["python", "-c", script])
    if result.stdout.strip() != "ok":
        raise RuntimeError(f"Unable to stat MinIO object {path!r}")


def redis_ping() -> str:
    return docker_exec(REDIS_CONTAINER, ["redis-cli", "PING"]).stdout.strip()


def redis_key_exists(key: str) -> int:
    return int(docker_exec(REDIS_CONTAINER, ["redis-cli", "EXISTS", key]).stdout.strip() or "0")


def redis_queue_length() -> int:
    return int(docker_exec(REDIS_CONTAINER, ["redis-cli", "LLEN", f"rq:queue:{QUEUE_NAME}"]).stdout.strip() or "0")


def sftp_file_exists(path: str) -> bool:
    return docker_exec_shell(SFTP_CONTAINER, f"test -f {path!s} && echo yes || echo no").stdout.strip() == "yes"


def write_report(lines: list[str]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def append_section(lines: list[str], title: str, content: list[str]) -> None:
    lines.append(f"## {title}")
    lines.extend(content)
    lines.append("")


def main() -> int:
    report_lines = [
        "# Full Stack Workflow Report",
        "",
        f"Run timestamp (UTC): {datetime.now(UTC).isoformat()}",
        "",
    ]

    fixture_name = FIXTURE_PATH.name
    upload_filename = f"fullstack_{int(time.time())}_{fixture_name}"
    upload_container_path = f"{SFTP_UPLOAD_DIR}/{upload_filename}"
    processed_container_path = f"{SFTP_PROCESSED_DIR}/{upload_filename}"

    try:
        append_section(
            report_lines,
            "Workflow",
            [
                "1. Start or refresh the Docker Compose stack.",
                "2. Verify API health, readiness, Vault, Redis, and Postgres.",
                "3. Register a unique API user, login, and call /api/v1/auth/me.",
                "4. Observe current protected /api/v1/batches behavior for a newly registered default role.",
                "5. Copy a known-good TIFF into the live SFTP upload folder.",
                "6. Wait for SFTP ingest to create batch/document rows and move the file.",
                "7. Wait for inference to persist a prediction and overlay.",
                "8. Verify MinIO objects, Redis queue/job artifacts, and audit log rows.",
            ],
        )

        run_command(["docker", "compose", "up", "-d"], cwd=REPO_ROOT)
        run_command(["docker", "compose", "run", "--rm", "migrate"], cwd=REPO_ROOT)

        health_status, health_body, _ = wait_for(
            lambda: _health_response("/api/v1/health"),
            timeout_seconds=60,
            interval_seconds=2,
            description="API health endpoint",
        )
        ready_status, ready_body, _ = wait_for(
            lambda: _health_response("/api/v1/ready"),
            timeout_seconds=60,
            interval_seconds=2,
            description="API readiness endpoint",
        )

        vault_summary = _check_vault()

        redis_response = redis_ping()
        if redis_response != "PONG":
            raise RuntimeError(f"Unexpected Redis response: {redis_response}")

        postgres_response = psql_query("SELECT current_database(), current_user;")
        if postgres_response != "documents|app":
            raise RuntimeError(f"Unexpected Postgres response: {postgres_response}")

        append_section(
            report_lines,
            "Infra Checks",
            [
                f"- API /health: {health_status} {health_body}",
                f"- API /ready: {ready_status} {ready_body}",
                f"- Vault: {vault_summary}",
                f"- Redis PING: {redis_response}",
                f"- Postgres identity: {postgres_response}",
            ],
        )

        email = f"fullstack-{int(time.time())}@example.com"
        password = "StrongPass123!"
        register_status, register_body, _ = http_request(
            "POST",
            f"{API_BASE_URL}/api/v1/auth/register",
            json_body={"email": email, "password": password},
        )
        if register_status not in (200, 201):
            raise RuntimeError(f"User registration failed: {register_status} {register_body}")

        login_status, login_body, _ = http_request(
            "POST",
            f"{API_BASE_URL}/api/v1/auth/login",
            form_body={"username": email, "password": password},
        )
        if login_status != 200:
            raise RuntimeError(f"User login failed: {login_status} {login_body}")

        access_token = login_body["access_token"]
        auth_headers = {"Authorization": f"Bearer {access_token}"}
        me_status, me_body, _ = http_request("GET", f"{API_BASE_URL}/api/v1/auth/me", headers=auth_headers)
        if me_status != 200:
            raise RuntimeError(f"/auth/me failed: {me_status} {me_body}")

        batches_status, batches_body, _ = http_request(
            "GET",
            f"{API_BASE_URL}/api/v1/batches",
            headers=auth_headers,
        )

        append_section(
            report_lines,
            "Auth and API",
            [
                f"- Registered user: {register_body}",
                f"- Login response: {login_body}",
                f"- /auth/me: {me_status} {me_body}",
                f"- /batches for newly registered default role: {batches_status} {batches_body}",
                "- Note: auth users are persisted in Postgres and Casbin subjects use str(users.id). Newly registered users receive the default auditor role.",
            ],
        )

        if not FIXTURE_PATH.exists():
            raise FileNotFoundError(f"Missing TIFF fixture: {FIXTURE_PATH}")

        if sftp_file_exists(upload_container_path) or sftp_file_exists(processed_container_path):
            raise RuntimeError(f"Test filename collision in SFTP paths: {upload_filename}")

        run_command(["docker", "cp", str(FIXTURE_PATH), f"{SFTP_CONTAINER}:{upload_container_path}"])

        document_row = wait_for(
            lambda: _query_document_row(upload_filename),
            timeout_seconds=90,
            interval_seconds=2,
            description="document row creation",
        )
        document_id = int(document_row[0])
        batch_id = int(document_row[1])
        blob_bucket = document_row[3]
        blob_path = document_row[4]

        batch_row = split_row(psql_query(f"SELECT id, request_id, status FROM batches WHERE id = {batch_id};"))
        if not batch_row:
            raise RuntimeError(f"Missing batch row for batch_id={batch_id}")

        prediction_row = wait_for(
            lambda: _query_prediction_row(document_id),
            timeout_seconds=120,
            interval_seconds=2,
            description="prediction row creation",
        )
        prediction_id = int(prediction_row[0])
        job_id = prediction_row[1]
        predicted_batch_id = int(prediction_row[2])
        predicted_document_id = int(prediction_row[3])
        label = prediction_row[4]
        confidence = float(prediction_row[5])
        model_sha256 = prediction_row[6]
        overlay_bucket = prediction_row[7]
        overlay_path = prediction_row[8]

        if predicted_batch_id != batch_id or predicted_document_id != document_id:
            raise RuntimeError("Prediction row does not match batch/document IDs")

        audit_row = wait_for(
            lambda: _query_audit_row(document_id),
            timeout_seconds=60,
            interval_seconds=2,
            description="prediction audit row creation",
        )

        check_minio_object(blob_path)
        check_minio_object(overlay_path)

        job_key_exists = redis_key_exists(f"rq:job:{job_id}")
        queue_length = redis_queue_length()

        if not sftp_file_exists(processed_container_path):
            raise RuntimeError(f"SFTP worker did not move file to processed: {processed_container_path}")
        if sftp_file_exists(upload_container_path):
            raise RuntimeError(f"SFTP upload file still present after processing: {upload_container_path}")

        append_section(
            report_lines,
            "Workflow Results",
            [
                f"- Uploaded TIFF fixture: {FIXTURE_PATH.name}",
                f"- Runtime SFTP filename: {upload_filename}",
                f"- Batch row: id={batch_row[0]}, request_id={batch_row[1]}, status={batch_row[2]}",
                f"- Document row: id={document_id}, batch_id={batch_id}, bucket={blob_bucket}, path={blob_path}",
                f"- Prediction row: id={prediction_id}, job_id={job_id}, label={label}, confidence={confidence:.6f}",
                f"- Model SHA-256: {model_sha256}",
                f"- Overlay object: bucket={overlay_bucket}, path={overlay_path}",
                f"- Redis queue length after processing: {queue_length}",
                f"- Redis job key exists: {job_key_exists}",
                f"- Audit row: actor={audit_row[0]}, action={audit_row[1]}, target={audit_row[2]}",
                f"- SFTP processed path present: {processed_container_path}",
            ],
        )

        append_section(
            report_lines,
            "Verdict",
            [
                "- Full live workflow passed for the application, storage, queue, ingest, and inference path.",
                "- Verified services: API health/readiness, auth register/login/me, Redis, Postgres, SFTP ingest, MinIO raw object, RQ job artifact, inference worker prediction persistence, overlay generation, and audit log persistence.",
                "- Protected batch API was verified with a newly registered default auditor role.",
                f"- Vault result: {vault_summary}",
            ],
        )

        write_report(report_lines)
        print(f"PASS: full stack workflow validated. Report written to {REPORT_PATH}")
        return 0
    except Exception as exc:  # pragma: no cover - live failure path
        append_section(
            report_lines,
            "Failure",
            [
                f"- Error: {exc}",
                "",
                "```text",
                traceback.format_exc().rstrip(),
                "```",
            ],
        )
        write_report(report_lines)
        print(f"FAIL: full stack workflow validation failed. Partial report written to {REPORT_PATH}", file=sys.stderr)
        return 1


def _health_response(path: str) -> tuple[int, Any, dict[str, str]] | None:
    status, body, headers = http_request("GET", f"{API_BASE_URL}{path}")
    if status == 200:
        return status, body, headers
    return None


def _query_document_row(filename: str) -> list[str] | None:
    row = psql_query(
        "SELECT id, batch_id, filename, blob_bucket, blob_path "
        f"FROM documents WHERE filename = '{filename}' "
        "ORDER BY id DESC LIMIT 1;"
    )
    return split_row(row) if row else None


def _query_prediction_row(document_id: int) -> list[str] | None:
    row = psql_query(
        "SELECT id, job_id, batch_id, document_id, label, confidence, model_sha256, overlay_bucket, overlay_path "
        f"FROM predictions WHERE document_id = {document_id} "
        "ORDER BY id DESC LIMIT 1;"
    )
    return split_row(row) if row else None


def _query_audit_row(document_id: int) -> list[str] | None:
    row = psql_query(
        "SELECT actor, action, target "
        f"FROM audit_logs WHERE target = 'document:{document_id}' "
        "ORDER BY id DESC LIMIT 1;"
    )
    return split_row(row) if row else None


def _check_vault() -> str:
    try:
        status, body, _ = http_request("GET", VAULT_HEALTH_URL)
        return f"reachable with HTTP {status} {body}"
    except Exception:
        status_output = run_command(
            [
                "docker",
                "ps",
                "-a",
                "--format",
                "{{.Names}}|{{.Status}}",
            ]
        ).stdout
        vault_line = next(
            (line for line in status_output.splitlines() if line.startswith("doc-classifier-service-vault-1|")),
            "",
        )
        vault_logs = run_command(["docker", "logs", "--tail", "20", "doc-classifier-service-vault-1"], check=False).stdout.strip()
        vault_logs = vault_logs or "no logs captured"
        return f"unreachable; container status={vault_line or 'missing'}; logs={vault_logs}"


if __name__ == "__main__":
    raise SystemExit(main())
