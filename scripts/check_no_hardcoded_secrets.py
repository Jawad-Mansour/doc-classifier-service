from __future__ import annotations

import pathlib
import re
import sys


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
APP_ROOT = REPO_ROOT / "app"

PATTERNS = [
    re.compile(r'os\.getenv\("VAULT_TOKEN",\s*"[^"]+"\)'),
    re.compile(r'os\.getenv\("JWT_SECRET_KEY",\s*"[^"]+"\)'),
    re.compile(r'os\.getenv\("SECRET_KEY",\s*"[^"]+"\)'),
    re.compile(r'os\.getenv\("MINIO_SECRET_KEY",\s*"[^"]+"\)'),
    re.compile(r'os\.getenv\("SFTP_PASSWORD",\s*"[^"]+"\)'),
    re.compile(r'os\.getenv\("DEMO_[A-Z_]*PASSWORD",\s*"[^"]+"\)'),
    re.compile(r'DATABASE_PASSWORD_FIELD:\s*settings\.DATABASE_PASSWORD\s+or\s+"[^"]+"'),
    re.compile(r'SECRET_KEY:\s*str\s*=\s*Field\([^)]*"change-me-in-production"'),
]


def main() -> int:
    violations: list[str] = []
    for path in APP_ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            for pattern in PATTERNS:
                if pattern.search(line):
                    violations.append(f"{path.relative_to(REPO_ROOT)}:{lineno}:{line.strip()}")

    if violations:
        print("Hardcoded secret defaults found:")
        for violation in violations:
            print(violation)
        return 1

    print("PASS: no hardcoded secret defaults detected in app/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
