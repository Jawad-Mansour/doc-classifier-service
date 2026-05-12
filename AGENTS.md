# AGENTS.md

## Role ownership
- Jad: `app/classifier/`, `app/workers/inference_worker.py`, `tests/classifier/`, `LICENSES.md`, golden replay test
- Ali: API, auth, permissions, Casbin, routes
- Mohamad: DB, services, repositories, audit, cache
- Aya: infra, Docker, Redis, MinIO, SFTP, Vault, CI

## Architecture rules
- API routes call services only.
- Workers call services for persistence.
- Repositories own SQL only.
- Classifier code does not import FastAPI or SQLAlchemy.
- API must not run inference.
- Worker runs inference.
- Worker must not write SQL directly.
- No local training in `docker-compose`.
- Do not download the RVL-CDIP dataset locally.
- Do not commit secrets.
- Do not commit virtual environments.

## Classifier handoff contract
- Load `app/classifier/models/classifier.pt`.
- Verify SHA-256 against `app/classifier/models/model_card.json`.
- Preprocess with Pillow: open image, convert to RGB, resize to `224x224`, convert with `ToTensor`, then apply ImageNet normalization.
- Return `label_id`, `label`, `confidence`, `top5`, and `model_sha256`.
- For local CPU-only inference and golden replay setup, install:

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements-ml.txt
```

- Validate with:

```bash
python3 app/classifier/eval/golden.py
```
