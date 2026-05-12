# Project Brainstorm — Document Classifier as an Authenticated Service

> Walking through the project phase by phase. This file records the final, confirmed understanding.

---

## Phase 0: Overall Mental Model

- Runs entirely via **docker-compose** on a developer laptop
- The "scanner vendor" is **not a real scanner** — it is simulated by manually dropping TIFF files into an SFTP folder (test case input)
- The system classifies documents by **visual layout** (not text/OCR)

---

## Phase 1: SFTP — File Ingestion Entry Point

- **SFTP = SSH File Transfer Protocol**
- Runs over SSH → encrypted + authenticated by default
- Supports **resumable transfers** via byte-range: if a transfer crashes, it resumes from the last confirmed byte (not from zero)
- **SHA-256** is used for file integrity verification — confirms the file arrived uncorrupted
- In this project: `atmoz/sftp` docker image acts as the SFTP server
- The scanner vendor (simulated) drops TIFF files into a watched SFTP folder

---

## Phase 2: Two Workers

### Worker 1 — sftp-ingest (Polling Worker)
- Continuously **polls** the SFTP folder (checks every ~5 seconds)
- When a new file is detected:
  1. Uploads the file to **MinIO** (blob storage)
  2. **Enqueues** a classification job into Redis via **RQ**

### Worker 2 — worker (Inference Worker)
- **Dequeues** jobs from Redis (RQ)
- Runs the **classifier** (ConvNeXt model) on the file from MinIO
- Writes the **prediction row** to Postgres
- Writes an **annotated overlay PNG** back to MinIO
- Calls the **service layer** to invalidate affected Redis caches

---

## Phase 3: Permission-Gated API

- Users authenticate via **JWT** (fastapi-users)
- Each user has a **role** — determines what they can do:
  - `admin` → invite users, toggle roles, view audit log
  - `reviewer` → view batches, relabel predictions where top-1 confidence < 0.7
  - `auditor` → read-only on batches and audit log
- Role enforcement via **Casbin** (policy engine, SQLAlchemy adapter)
- Role changes take effect on **next page load** — no logout required
- Every role change is recorded in the **audit log**

---

## Phase 4: Dataset — RVL-CDIP

- The dataset **already has the 16 classes pre-labeled** with the exact names from the spec — no renaming needed
- Labels come as **integer indices (0–15)** in text files (`train.txt`, `val.txt`, `test.txt`), each line is: `path/to/image.tif class_index`
- We maintain a `class_names` list that maps index → name
- **Splits are already provided** by the dataset — we use them as-is:
  - `train.txt` → 320k images
  - `val.txt` → 40k images
  - `test.txt` → 40k images (we carve our 50 golden images from here)
- Images are **already grayscale TIFFs** (scanner output) → 1 channel instead of 3, less data for the model to process
- Training happens **only on Colab** — never locally, never in docker

---

## Phase 5: Colab Training Pipeline — Step by Step

### TASK: Create LICENSES.md
- Flag RVL-CDIP as **academic / research use only**
- Source: adamharley.com/rvl-cdip/
- This file must exist in the repo root before submission

---

### Data Splits
- RVL-CDIP already provides the splits — use them as-is:
  - `train.txt` → 320k (used for training)
  - `val.txt` → 40k (used during training to monitor generalization)
  - `test.txt` → 40k (used once at the end for final evaluation)
- We **do not re-split** — the dataset authors defined these splits deliberately
- From `test.txt`, we hand-pick **50 golden images** (see below)

---

### The Golden Set — What It Is and Why
- 50 specific TIFF images selected deliberately from the test split
- Must span all 16 classes, include both easy cases and ambiguous ones
- Their expected labels and top-1 confidence scores are saved to `golden_expected.json`
- **Purpose:** regression test for the model — if any code change accidentally affects inference behavior, the golden-set test catches it because outputs must be byte-identical to the saved expectations (top-1 confidence within 1e-6)
- This test runs in CI on every push — a failure blocks the build
- The docker-compose stack runs this test; it never re-trains

---

### Preprocessing (Before Training)
- Images are grayscale (1 channel) but ConvNeXt was pretrained on ImageNet (RGB, 3 channels)
  → **Replicate the single channel 3 times** to produce a 3-channel input — shape goes from (1, H, W) to (3, H, W)
- Resize to **224x224** (ConvNeXt standard input size)
- Normalize using **ImageNet mean and std** — because we're loading ImageNet pretrained weights, inputs must be in the same distribution the backbone was trained on
- Data augmentation during training only (not val/test): random horizontal flip, small random rotation — helps reduce overfitting
- Check for corrupt/zero-byte files in the dataset before training starts

---

### Training Approach
- **Option A — Full 320k + 5 epochs:** best accuracy ceiling but ~10-20h on Colab T4, high session-timeout risk
- **Option B (recommended) — Stratified subset ~30-50% (96k-160k images) + 10-15 epochs:** faster per-epoch, more passes through data, easier to recover from crashes, still reaches 88-92% top-1 which is solid for this project
- **Stratified** means you sample equally from all 16 classes — random sampling without stratification skews class distribution and hurts accuracy on minority classes
- Fine-tuning a pretrained ConvNeXt converges fast regardless — the backbone already learned edges, textures, shapes from ImageNet; we are just teaching the head to map those to 16 document classes
- Monitor **train loss vs val loss** each epoch — val loss rising while train loss drops = overfitting → stop early

---

### Fine-Tuning Process (ConvNeXt Tiny or Small)
1. Load `ConvNeXt_Tiny_Weights.IMAGENET1K_V1` or Small equivalent from `torchvision.models`
2. **Replace the classifier head** — the original head outputs 1000 ImageNet classes; replace it with a new linear layer outputting 16 classes
3. **Freeze the backbone** (all layers except the new head) — called **linear probe**
   - Only the new head trains initially
   - Backbone weights are locked — they don't update
4. Train for a few epochs; once head loss stabilizes, optionally **unfreeze the last N backbone layers** (partial unfreeze) and train with a much lower learning rate
5. Optionally go to **full fine-tune** — unfreeze everything, very low LR
6. The freeze policy used must be recorded in `model_card.json`

**Why freeze first?** The pretrained backbone is already good. If you unfreeze everything from epoch 1 with a normal LR, you will destroy the pretrained weights. Freezing first protects them.

---

### Overfitting / Underfitting Controls
- **Underfitting signals:** train loss stays high after several epochs → LR too low, or too frozen
- **Overfitting signals:** val loss rises while train loss drops → add weight decay, reduce LR, stop early
- Use: weight decay (L2 regularization), learning rate scheduler (reduce on plateau), early stopping based on val accuracy

---

### Artifacts Saved After Training
All of these ship to the repo. Nothing else from training does.

| Artifact | Path | Notes |
|---|---|---|
| Model weights | `app/classifier/models/classifier.pt` | git LFS (~110MB Tiny / ~190MB Small) |
| Model card | `app/classifier/models/model_card.json` | SHA-256 of .pt, top-1/top-5 on full test + golden, per-class accuracy, backbone name, weights enum, freeze policy, environment fingerprint |
| Golden images | `app/classifier/eval/golden_images/` | 50 TIFFs |
| Golden expected | `app/classifier/eval/golden_expected.json` | Expected label + top-1 confidence for each golden image |

---

### What the Docker-Compose Stack Does With the Model
- **Never trains** — training is Colab-only
- **Never sees the full dataset**
- At startup: loads `classifier.pt`, verifies SHA-256 matches `model_card.json`, checks top-1 is above the threshold in README — refuses to boot if any check fails
- At runtime: runs inference on files arriving from SFTP
- In CI: runs `golden.py` replay test — byte-identical label match, confidence within 1e-6

---

## Phase 6: The 4 Tasks — Deep Dive

---

### FULL SYSTEM FLOW (Bird's Eye View)

```
[Scanner Vendor]
      |
      | drops TIFF via SFTP
      v
 +---------+
 |  atmoz  |  ← SFTP server (docker container)
 |  /sftp  |
 +---------+
      |
      | sftp-ingest worker polls every 5s
      v
 +-------------+       uploads file
 | sftp-ingest |  ─────────────────────────>  +-------+
 |   worker    |                              | MinIO |  (blob storage)
 +-------------+                              +-------+
      |
      | enqueues job (file path + metadata)
      v
 +---------+
 |  Redis  |  ← RQ job queue
 +---------+
      |
      | inference worker dequeues
      v
 +----------+    reads file     +-------+
 |  worker  |  <─────────────  | MinIO |
 |          |
 |          |  runs ConvNeXt
 |          |
 |          |  writes prediction ──────>  +----------+
 |          |  writes overlay PNG ──────> | Postgres |
 |          |  invalidates cache ──────>  +----------+
 +----------+                  +-------+
                                | Redis |  (cache layer)
                                +-------+
                                    ^
                                    | cached reads
                                    |
                               +---------+
                               | FastAPI |  ← authenticated users
                               |   API   |     browse results here
                               +---------+
```

---

### TASK 1 — Train a Classifier (Colab Only)

**What:** Fine-tune ConvNeXt Tiny or Small (from torchvision) on RVL-CDIP 16 classes.

**Why ConvNeXt and not ResNet/VGG?**
- ConvNeXt is a modern CNN (2022) that matches Vision Transformer accuracy but runs faster on CPU
- torchvision ships production-quality pretrained weights
- Tiny (~28M params) fits in ~110MB .pt file; Small (~50M params) ~190MB — both within git LFS limits
- CPU inference p95 < 1.0s is achievable with Tiny/Small; would fail with larger models

**Colab Training Flow:**
```
Download RVL-CDIP (37GB) to Colab session
        |
        v
Stratified sample (30-50% of train split)
        |
        v
Preprocessing pipeline:
  - grayscale (1ch) → repeat to 3ch
  - resize to 224x224
  - normalize (ImageNet mean/std)
  - augment (flip, rotate) — train only
        |
        v
Load ConvNeXt_Tiny pretrained on ImageNet
  - Replace classifier head: 1000 classes → 16 classes
  - Freeze backbone
        |
        v
Train head only (linear probe, ~3-5 epochs)
        |
        v
Optionally unfreeze last N layers (partial unfreeze)
Train with lower LR (~5-10 more epochs)
        |
        v
Evaluate on full 40k test split (never seen during training)
        |
        v
Hand-pick 50 golden images from test split
        |
        v
Save artifacts → commit to repo
```

**Why evaluate on full test split?** The model card must report real test metrics (top-1, top-5, per-class accuracy). Graders will check these numbers match the weights.

---

### TASK 2 — Build the FastAPI Service

**What:** HTTP API that handles auth, permissions, job queuing, and result browsing. **Never runs inference.**

**Why FastAPI?** Async-native, automatic OpenAPI docs, tight pydantic integration, fastapi-users and fastapi-cache2 are built for it.

**Strict Layered Architecture:**
```
HTTP Request
     |
     v
+------------------+
|   app/api/       |  ← routers only. Validates input, calls service, returns response.
|  (HTTP layer)    |    No SQLAlchemy. No Redis. No external calls.
+------------------+
     |
     v
+------------------+
|  app/services/   |  ← business logic. Owns transactions. Owns cache invalidation.
|  (logic layer)   |    Calls repositories. Calls infra adapters.
+------------------+
     |         |
     v         v
+----------+  +------------------+
| app/     |  |   app/infra/     |
| repos/   |  | (adapters layer) |
| (SQL)    |  | blob/queue/cache |
+----------+  +------------------+
     |
     v
+------------------+
|  app/db/models   |  ← SQLAlchemy ORM. Only repos import this.
+------------------+
     |
     v
  Postgres
```

**Why this strict separation?**
- Graders will add an endpoint live on Friday — if your router touches the DB directly, you fail
- Repos can be swapped (e.g. swap Postgres for another DB) without touching business logic
- Cache invalidation in one place = no stale reads

**Auth Flow:**
```
User POST /auth/login (email + password)
        |
        v
fastapi-users validates credentials against Postgres
        |
        v
Issues JWT (signed with key fetched from Vault at startup)
        |
        v
User sends JWT in Authorization: Bearer header on every request
        |
        v
Dependency checks JWT validity + loads user role
        |
        v
Casbin checks: does this role have permission for this action?
  YES → proceed
  NO  → 403
```

**Why Casbin?** Policy rules are stored in DB (SQLAlchemy adapter), not hardcoded. Role changes take effect immediately on next request — no logout needed because the policy table is re-checked live.

**Why JWT from Vault?** If the signing key is in the codebase or .env, it's a security risk. Vault is the single source of truth for all secrets. api refuses to boot if Vault is unreachable.

**Key API Endpoints:**
```
POST /auth/register          → create user
POST /auth/login             → get JWT
GET  /me                     → current user info        [cached]
POST /admin/users/{id}/role  → toggle role              [invalidates cache]
GET  /batches                → list batches             [cached]
GET  /batches/{bid}          → batch detail + predictions [cached]
GET  /predictions/recent     → recent predictions       [cached]
PATCH /predictions/{id}      → relabel (reviewer only, confidence < 0.7)
GET  /audit-log              → audit log (admin/auditor)
```

---

### TASK 3 — Ingestion + Inference Pipeline (2 Workers)

**Why 2 workers and not 1?**
- Separation of concerns: file watching is I/O-bound (polling), inference is CPU-bound
- If inference is slow, the SFTP watcher still keeps picking up files and queuing them
- Each worker can be scaled independently

**Why RQ (Redis Queue) and not Celery?**
- Celery is heavier, requires a broker + backend config, more complex
- RQ is simple: push a Python function + args onto a Redis list, worker pops and runs it
- The whole stack already has Redis — no extra service needed
- Project explicitly forbids Celery

**Worker 1 — sftp-ingest:**
```
Loop every 5 seconds:
  Connect to atmoz/sftp container
  List files in watched folder
  For each new file:
    1. Download file bytes
    2. Validate: not zero-byte, is a TIFF/image, size reasonable
       → if invalid: log error, move to quarantine folder, skip
    3. Upload to MinIO (blob storage) → get object key back
    4. Enqueue RQ job: { object_key, batch_id, filename, timestamp }
    5. Mark file as processed (move/rename on SFTP)
```

**Worker 2 — inference worker:**
```
RQ worker listening on Redis queue:
  Dequeue job: { object_key, batch_id, filename, timestamp }
  1. Download file from MinIO by object_key
  2. Load into memory, apply same preprocessing as training
     (grayscale → 3ch, resize 224x224, normalize)
  3. Run ConvNeXt forward pass → get 16-class probabilities
  4. Top-1 label + confidence, Top-5 labels + confidences
  5. Write prediction row to Postgres
     (batch_id, label, confidence, all_probs, status)
  6. Draw annotated overlay PNG (label + confidence on image)
  7. Upload overlay PNG to MinIO
  8. Call service layer → invalidate Redis cache for this batch
  9. Update batch status in Postgres → trigger audit log entry
```

**Why MinIO?**
- S3-compatible: same API as AWS S3, easy to swap to real S3 in production
- Runs locally in docker — no cloud dependency
- Keeps binary files (TIFFs, PNGs) out of Postgres (DB stores only metadata/paths)

**Error handling in the pipeline:**
```
MinIO unreachable mid-job  → job fails, RQ marks it failed, retries with backoff
Redis container recreated  → RQ jobs in "started" state are lost → need job timeout + re-enqueue on startup
Malformed file             → caught at sftp-ingest validation, quarantined, logged, never enqueued
```

---

### TASK 4 — Supporting Services

```
+----------+  schema migrations  +------------+
| migrate  | ------------------> |  Postgres  |
| container|  (runs then exits)  |     16     |
+----------+                     +------------+
                                       ^
                                       | reads/writes (repos only)
                                       |
                                  +----------+
                                  | FastAPI  |
                                  |  + worker|
                                  +----------+
                                       |
                          +------------+------------+
                          |                         |
                     +---------+             +-------+
                     |  Redis  |             | MinIO |
                     | queue + |             | blob  |
                     |  cache  |             +-------+
                     +---------+
                          |
                     +---------+
                     |  Vault  |  ← all secrets live here
                     +---------+
```

**Postgres 16 + Alembic:**
- Alembic = version-controlled DB schema migrations (like git for your DB schema)
- `migrate` container runs `alembic upgrade head` on every startup then exits
- This guarantees the DB schema is always up to date before api or worker starts
- Audit log table: every role change, relabel, batch state change → actor, action, target, timestamp

**Redis 7 — Dual Role:**
- As **queue:** RQ pushes/pops job payloads (JSON) from Redis lists
- As **cache:** fastapi-cache2 stores API response bytes keyed by endpoint + params
- Same Redis instance, different key namespaces — no conflict

**Vault (dev mode, KV v2):**
- Stores: JWT signing key, Postgres password, MinIO credentials, Redis password
- api and worker fetch secrets at startup via Vault HTTP API
- `grep -ri 'password' app/` must return zero — no secrets in code or .env
- .env holds only: Vault root token + port mappings (needed to connect to Vault itself)
- If Vault is down → api refuses to boot (can't get JWT key → can't auth anyone)

**atmoz/sftp:**
- Lightweight SFTP server docker image
- Simulates the scanner vendor dropping files
- sftp-ingest worker connects to this container and polls its upload folder

---

## Phase 7: Architecture Constraints — Layered Codebase (No Exceptions)

The graders will ask you to add a new endpoint **live on Friday**. If your layers are entangled, you cannot do it cleanly. The architecture IS the grade.

---

### The Rule: Each Layer Has One Job. It Only Talks Downward.

```
                  +-----------+
  HTTP IN ──────> |  app/api  |  routers only — HTTP in, HTTP out
                  +-----------+
                       |  calls
                       v
                  +--------------+
                  | app/services |  business logic + cache invalidation
                  +--------------+
                       |  calls
              +--------+--------+
              |                 |
              v                 v
      +---------------+   +------------+
      | app/repositories|  | app/infra  |  adapters: blob, queue, SFTP, Vault, cache
      +---------------+   +------------+
              |
              v
      +----------------+
      | app/db/models  |  SQLAlchemy ORM (only repos import this)
      +----------------+
              |
              v
          Postgres


      app/domain/  ←  Pydantic models, used across all layers for data passing
                       (NOT the ORM models)
```

---

### Layer by Layer — What Each Can and Cannot Do

#### `app/api/` — HTTP Layer
**Can:**
- Receive HTTP requests, parse path/query params and request body
- Call one service method
- Return an HTTP response (200, 201, 404, 403, etc.)
- Raise `HTTPException`

**Cannot:**
- Import `Session` from SQLAlchemy or query the DB
- Call `cache.set()` / `cache.invalidate()` directly
- Connect to MinIO, Redis, SFTP, or Vault
- Contain any if/else business logic (e.g. "if role is reviewer AND confidence < 0.7")

**Why:** The router is the thinnest possible translation layer. HTTP is a transport concern. Business rules do not belong here. If you need to add a CLI command that does the same thing as an endpoint, you call the same service — not the router.

---

#### `app/services/` — Business Logic Layer
**Can:**
- Enforce business rules (e.g. block last admin from demoting themselves)
- Call multiple repositories in one transaction
- Call infra adapters (blob upload, enqueue job, cache invalidation)
- Raise domain-level errors (NOT HTTPException — the router translates those)

**Cannot:**
- Know anything about HTTP (no `Request`, no `Response`, no status codes)
- Import SQLAlchemy models directly
- Be called by repositories

**Transaction boundary example:**
```
service.toggle_role(user_id, new_role):
  1. repo.get_user(user_id)           ─┐
  2. check: is this the last admin?    |  all in one DB transaction
  3. repo.update_role(user_id, role)   |  if step 4 fails, step 3 rolls back
  4. repo.write_audit_log(entry)      ─┘
  5. cache.invalidate(user_id)        ← happens AFTER transaction commits
```

---

#### `app/repositories/` — SQL Layer
**Can:**
- Write and execute SQLAlchemy queries
- Return domain models (Pydantic), not ORM objects
- Raise domain-level exceptions (e.g. `UserNotFound`) — NOT `HTTPException`

**Cannot:**
- Contain any business logic ("if confidence < 0.7 then...")
- Call `cache.invalidate()` — cache is a service concern
- Raise `HTTPException` (404, 403, etc.) — that's the router's job
- Import anything from `app/api/` or `app/services/`

**Why separate repos from services?** If you want to swap Postgres for another DB later, you only rewrite repos. Services and routers don't change. Also: repos are easily unit-testable in isolation.

---

#### `app/domain/` — Pydantic Models
**What they are:** Pure data classes (Pydantic BaseModel). Represent the business entities: `User`, `Batch`, `Prediction`, `AuditEntry`, etc.

**Why separate from ORM models?**
```
ORM Model (SQLAlchemy):          Domain Model (Pydantic):
  - maps to a DB table             - what the API/service sees
  - has DB-specific columns        - can flatten/reshape data
  - has relationships              - safe to serialize to JSON
  - belongs to DB layer            - no DB dependency

Example: ORM User has hashed_password column
         Domain User never exposes hashed_password
```

Repos read ORM models from DB → convert → return domain models upward. The rest of the app never sees SQLAlchemy objects.

---

#### `app/infra/` — External System Adapters
**What it holds:** One adapter per external system, each behind a clean interface.

```
app/infra/
  blob.py     ← MinIO adapter    (upload_file, get_file, delete_file)
  queue.py    ← RQ adapter       (enqueue_job, get_job_status)
  cache.py    ← Redis adapter    (get, set, invalidate)
  sftp.py     ← SFTP adapter     (list_files, download_file, move_file)
  vault.py    ← Vault adapter    (get_secret)
```

**Why adapters?** If you swap MinIO for S3, you only rewrite `blob.py`. Nothing in services or repos changes. Services call `blob.upload_file(...)` — they don't know or care what's behind it.

---

#### `app/db/models.py` — SQLAlchemy ORM Models
- One file, imported **only** by repositories
- No other layer ever imports from here
- If a router or service imports from `app/db/models`, that is an architecture violation

---

### The Friday Test — What They Will Do

> "Add a new endpoint that returns the 5 most recent predictions for a given batch."

**Clean architecture answer (takes 5 minutes):**
1. Add route in `app/api/predictions.py` — calls `prediction_service.get_recent_by_batch(batch_id, limit=5)`
2. Add method in `app/services/prediction_service.py` — calls `prediction_repo.get_recent_by_batch(...)`
3. Add query in `app/repositories/prediction_repo.py` — one SQLAlchemy query
4. Done. No other files touched.

**Tangled architecture answer (takes 30 minutes, breaks things):**
- The query is in the router. The cache logic is in the repo. Nobody knows where to add what.

---

### Forbidden Patterns (Will Fail the Review)

| Pattern | Why it's wrong |
|---|---|
| `from app.db.models import User` inside a router | Router touching ORM — layer violation |
| `raise HTTPException(404)` inside a repo | Repo raising HTTP error — layer violation |
| `cache.invalidate(...)` inside a repo | Cache is a service concern |
| Business rule (`if confidence < 0.7`) in a router | Logic belongs in service |
| Calling a service from another service directly for cache | Circular — infra adapter is the right path |

---

## Phase 8: Functional Requirements — Part by Part

---

### 1. Authentication

**Main idea:** Before anyone can touch the API, they must prove who they are. We issue them a token. They carry that token on every request.

**How it works:**
```
User registers → email + password stored in Postgres (password hashed, never plaintext)

User logs in:
  POST /auth/login  { email, password }
         |
         v
  fastapi-users checks credentials
         |
         v
  Issues a JWT (JSON Web Token)
  ┌─────────────────────────────────────┐
  │ JWT contains:                       │
  │  - user_id                          │
  │  - expiry timestamp                 │
  │  - signed with secret key from Vault│
  └─────────────────────────────────────┘
         |
         v
  User sends JWT in every request header:
  Authorization: Bearer <token>
         |
         v
  API verifies signature → knows who the user is
```

**Why fastapi-users?**
- It handles the full auth lifecycle: register, login, password reset, JWT issuance
- Has a SQLAlchemy adapter — plugs directly into our Postgres setup
- Without it we'd write all of this from scratch: hashing, token generation, session management

**Why JWT and not sessions?**
- JWT is stateless — the server doesn't need to store sessions in DB or Redis
- Token carries the user identity inside it, verified by signature
- Works well for microservice-style setups where workers also need to verify identity

**Why is the signing key in Vault and not in .env?**
- If the key leaks, anyone can forge tokens and impersonate any user
- Vault is the single trusted source for all secrets — consistent approach
- api refuses to boot if Vault is unreachable → no key → no auth → safe

---

### 2. Permissions (Casbin + 3 Roles)

**Main idea:** Authentication tells us WHO you are. Authorization tells us WHAT you can do. These are two separate concerns.

**The 3 roles:**
```
┌──────────┬────────────────────────────────────────────────────────┐
│  ROLE    │  WHAT THEY CAN DO                                      │
├──────────┼────────────────────────────────────────────────────────┤
│ admin    │ Invite users, toggle roles, view audit log             │
│ reviewer │ View batches, relabel predictions (confidence < 0.7)   │
│ auditor  │ Read-only on batches and audit log                     │
└──────────┴────────────────────────────────────────────────────────┘
```

**Why the 0.7 confidence threshold for reviewers?**
- Predictions above 0.7 the model is confident about — no human review needed
- Predictions below 0.7 the model is uncertain — a human reviewer should verify
- Reviewers cannot touch high-confidence predictions — this prevents arbitrary overrides

**Why Casbin?**
- Casbin is a policy engine — rules are stored in DB, not hardcoded in if/else
- When a role changes, the policy table updates → next request enforces new permissions
- No logout/login required — the policy is checked live on every request
- Hardcoding roles in if/else would mean every role change needs a code deploy

**Role toggle flow:**
```
Admin calls: PATCH /admin/users/{id}/role  { role: "reviewer" }
        |
        v
service.toggle_role() runs:
  1. Is requester an admin? (Casbin check)
  2. Is this the LAST admin trying to demote themselves? → BLOCK
  3. Update role in Postgres
  4. Update Casbin policy table
  5. Write audit log entry
  6. Invalidate that user's cache
        |
        v
Next request from that user → Casbin reads updated policy → new permissions applied
No logout needed.
```

**Why block the last admin from demoting themselves?**
- If the only admin removes their own admin role, nobody can ever promote another user
- The system becomes locked — no way to recover without direct DB access
- This edge case must be a hard block in the service layer

---

### 3. Caching

**Main idea:** Some API calls are read-heavy and hit the DB every time. Cache stores the result in Redis so the second call returns in <1ms instead of hitting Postgres.

**What gets cached (minimum required):**
```
GET /me                  → your own user profile
GET /batches             → list of all batches
GET /batches/{bid}       → one batch with its predictions
GET /predictions/recent  → recent predictions feed
```

**Cache lifecycle:**
```
First request:
  GET /batches/{bid}
       |
       v
  Cache MISS → service queries Postgres → result stored in Redis → returned to user

Second request (same endpoint):
  GET /batches/{bid}
       |
       v
  Cache HIT → result returned directly from Redis (no DB query)

Write happens (new prediction arrives for batch {bid}):
  service.write_prediction()
       |
       v
  Postgres updated
  Cache for /batches/{bid} INVALIDATED  ← service layer does this
       |
       v
  Next GET /batches/{bid} → Cache MISS → fresh data from Postgres
```

**Why fastapi-cache2?**
- Decorator-based caching — clean, no boilerplate
- Native Redis backend support
- Invalidation is manual and explicit — we control exactly when the cache is cleared

**Why invalidation lives ONLY in the service layer?**
- Routers don't know what data changed (they just pass the call down)
- Repos don't know what cache keys exist (they only speak SQL)
- Services know both — they orchestrate the write AND the invalidation in the same transaction boundary

**Latency targets this enables:**
```
Cached reads:   p95 < 50ms   ← Redis response time
Uncached reads: p95 < 200ms  ← Postgres query time
```

---

### 4. Secrets

**Main idea:** No secret (password, key, token) ever appears in the codebase or any committed file. Everything lives in Vault.

**What goes into Vault:**
```
┌─────────────────────────────────────────┐
│  Vault KV v2 secrets store              │
│                                         │
│  secret/jwt_signing_key   → "abc123..." │
│  secret/postgres_password → "pg_pass"  │
│  secret/minio_credentials → key+secret │
│  secret/redis_password    → "red_pass" │
└─────────────────────────────────────────┘
```

**Startup sequence:**
```
api/worker container starts
        |
        v
Reads VAULT_TOKEN from environment (.env)
        |
        v
Fetches all secrets from Vault HTTP API
        |
        v
Vault unreachable? → REFUSE TO START
        |
        v
Secrets loaded into memory only (never written to disk)
        |
        v
App boots and uses secrets from memory
```

**The grep test:**
```
grep -ri 'password' app/
```
Must return zero matches outside the Vault-reading code. This is a hard requirement checked live on Friday. Any hardcoded credential anywhere fails this test immediately.

**Why not just .env?**
- .env files get accidentally committed
- .env doesn't have access control — anyone with file access sees all secrets
- Vault has audit logging — you can see who accessed which secret and when
- .env in this project holds ONLY: Vault root token + port mappings (the minimum needed to connect to Vault itself)

---

### 5. Database

**Main idea:** The DB schema is version-controlled and applied automatically on startup. Every sensitive action leaves a permanent trail in the audit log.

**Migration flow:**
```
docker-compose up
        |
        v
migrate container starts first
        |
        v
runs: alembic upgrade head
  (applies all pending schema migrations in order)
        |
        v
migrate container EXITS
        |
        v
api and worker containers start
(guaranteed: DB schema is correct before any app code runs)
```

**Why Alembic?**
- Schema changes are versioned like code (each migration is a file in git)
- If you add a column, write a migration — never ALTER TABLE manually
- Rollback is possible: `alembic downgrade -1`
- The migrate container pattern guarantees no app starts against a stale schema

**Audit Log — what it records:**
```
┌─────────────┬──────────────────┬────────────────┬─────────────────────┐
│  actor      │  action          │  target        │  timestamp          │
├─────────────┼──────────────────┼────────────────┼─────────────────────┤
│ admin@co.com│ role_change      │ user:42        │ 2026-05-12 10:00:00 │
│ rev@co.com  │ relabel          │ prediction:99  │ 2026-05-12 10:01:00 │
│ system      │ batch_state_change│ batch:7       │ 2026-05-12 10:02:00 │
└─────────────┴──────────────────┴────────────────┴─────────────────────┘
```

**Every** role change, relabel, and batch state change writes a row. No exceptions. This is how auditors see what happened and when.

---

### 6. Pipeline

**Main idea:** Files arrive via SFTP, get stored safely, get classified automatically, results are visible in the API — all without human intervention, within 10 seconds.

**End-to-end flow with timing:**
```
t=0s   File dropped into SFTP folder by scanner vendor

t≤5s   sftp-ingest polls → detects file → validates it
        → uploads to MinIO → enqueues RQ job → marks file processed

t=5-9s  worker dequeues job
        → downloads file from MinIO
        → runs ConvNeXt inference (~<1s on CPU)
        → writes prediction row to Postgres
        → writes annotated overlay PNG to MinIO
        → invalidates cache for this batch

t<10s  GET /batches/{bid} → fresh data → prediction visible

```

**Malformed file handling:**
```
Zero-byte file      → detected at sftp-ingest → quarantine + log
Non-image file      → detected at sftp-ingest → quarantine + log
Oversized file      → detected at sftp-ingest → quarantine + log
Valid TIFF          → proceeds to MinIO + queue
```
Quarantine = move to a separate folder, write a structured log entry, never enqueue. The pipeline never crashes on bad input.

---

### 7. Refuse to Start

**Main idea:** The system does a health check on itself before accepting any traffic. If critical dependencies are broken, it refuses to run rather than running in a broken state.

**api + worker refuse to boot if:**
```
┌─────────────────────────────────────────────────────────────┐
│  CHECK 1: classifier.pt exists at expected path             │
│           → missing? ABORT                                  │
│                                                             │
│  CHECK 2: SHA-256 of classifier.pt matches model_card.json  │
│           → mismatch? ABORT (weights may be corrupted)      │
│                                                             │
│  CHECK 3: model_card top-1 accuracy >= threshold in README  │
│           → below threshold? ABORT (bad model deployed)     │
└─────────────────────────────────────────────────────────────┘
```

**api additionally refuses if:**
```
┌─────────────────────────────────────────────────────────────┐
│  CHECK 4: Vault is reachable and returns JWT signing key     │
│           → unreachable? ABORT (can't authenticate anyone)  │
│                                                             │
│  CHECK 5: Casbin policy table is NOT empty                  │
│           → empty? ABORT (no permissions defined = everyone │
│             gets everything or nothing)                     │
└─────────────────────────────────────────────────────────────┘
```

**Why this pattern matters:**
- A broken startup that silently continues leads to corrupt data, unauthorized access, or garbage predictions
- Fast fail on startup is always safer than slow fail in production
- Friday demo: kill Vault → api refuses to restart → this is the feature, not a bug

---

## Phase 9: Compose Stack — Every Service Explained

The entire system runs as a single `docker-compose up` from a fresh clone. Nine containers, each with one job.

```
┌─────────────────────────────────────────────────────────────────┐
│                     docker-compose network                      │
│                                                                 │
│  ┌─────────┐    ┌──────────┐    ┌────────────┐   ┌──────────┐  │
│  │  vault  │    │   db     │    │   redis    │   │  minio   │  │
│  │ :8200   │    │postgres16│    │  redis:7   │   │  :9000   │  │
│  └────┬────┘    └────┬─────┘    └─────┬──────┘   └────┬─────┘  │
│       │              │                │               │         │
│       └──────────────┴───────┬────────┴───────────────┘         │
│                              │ all services depend on these      │
│                              │                                   │
│  ┌─────────┐    ┌───────┐    │    ┌──────────────┐              │
│  │ migrate │    │  sftp │    │    │ sftp-ingest  │              │
│  │(exits)  │    │atmoz  │    │    │ (polls sftp) │              │
│  └─────────┘    └───────┘    │    └──────────────┘              │
│                              │                                   │
│  ┌──────────────────────┐    │    ┌──────────────┐              │
│  │        api           │◄───┘    │    worker    │              │
│  │  FastAPI :8000       │         │ (inference)  │              │
│  └──────────────────────┘         └──────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

**Startup order matters:**
```
vault + db + redis + minio + sftp  →  start first (infrastructure)
        |
migrate  →  runs alembic upgrade head, then EXITS
        |
api + worker + sftp-ingest  →  start last (application)
```

### Each Service

| Service | Image | Role | Owns |
|---|---|---|---|
| `vault` | hashicorp/vault | Secrets store, dev mode | JWT key, DB/MinIO/Redis passwords |
| `db` | postgres:16 | Application database | Users, batches, predictions, audit log, Casbin policies |
| `redis` | redis:7 | Queue + cache | RQ job lists, fastapi-cache2 response cache |
| `minio` | minio/minio | S3-compatible blob store | Raw TIFFs, annotated overlay PNGs |
| `sftp` | atmoz/sftp | SFTP server | Incoming file drop zone from scanner vendor |
| `migrate` | your build | Schema migration runner | Runs `alembic upgrade head`, exits |
| `api` | your build | FastAPI HTTP server | Auth, permissions, endpoints |
| `worker` | your build | Inference worker (RQ) | Dequeue, classify, write predictions |
| `sftp-ingest` | your build | SFTP poller | Detect files, upload to MinIO, enqueue jobs |

**Why dev mode for Vault?**
- Dev mode starts with a root token already set, no unsealing ceremony needed
- All data lives in memory — container restart wipes it (acceptable for a laptop demo)
- In production you'd use a persistent, unsealed Vault — but that's out of scope here

**.env file contains only:**
```
VAULT_ROOT_TOKEN=root
API_PORT=8000
MINIO_PORT=9000
SFTP_PORT=2222
POSTGRES_PORT=5432
REDIS_PORT=6379
```
Nothing else. No passwords. No keys. All other config comes from Vault at runtime.

---

## Phase 10: Deliverables — What Must Exist at Submission

### 1. GitHub Repo tagged `v0.1.0-week6`
- `docker-compose up` works from a fresh clone after `cp .env.example .env`
- `.env.example` has placeholder values but correct keys
- No secrets committed anywhere

### 2. Model Artifacts (git LFS for .pt)
```
app/classifier/
  models/
    classifier.pt          ← weights (~110MB Tiny / ~190MB Small)
    model_card.json        ← see below
  eval/
    golden_images/         ← 50 TIFFs
    golden_expected.json   ← { "filename": { "label": "invoice", "confidence": 0.94 } }
    golden.py              ← replay test script
```

**model_card.json must contain:**
```json
{
  "backbone": "convnext_tiny",
  "weights_enum": "ConvNeXt_Tiny_Weights.IMAGENET1K_V1",
  "freeze_policy": "partial_unfreeze",
  "sha256": "abc123...",
  "test_top1": 0.91,
  "test_top5": 0.99,
  "golden_top1": 0.94,
  "per_class_accuracy": { "invoice": 0.93, "letter": 0.95, ... },
  "environment": { "torch": "2.4.0", "python": "3.11", "cuda": "..." }
}
```

### 3. Golden-Set Replay Test (`golden.py`)
- Loads `classifier.pt`, runs all 50 golden images through the model
- Compares: label must be **byte-identical**, confidence within **1e-6**
- Any mismatch → test FAILS → CI blocks the push
- This catches: accidental weight swap, preprocessing change, normalization bug

### 4. CI Pipeline (GitHub Actions on every push)
```
Push to GitHub
      |
      v
┌─────────────────────────────────────────┐
│  CI Pipeline                            │
│                                         │
│  1. lint          (ruff / flake8)       │
│  2. type-check    (mypy)                │
│  3. build image   (docker build)        │
│  4. golden test   (golden.py)           │
│  5. smoke test:                         │
│     - docker-compose up full stack      │
│     - SCP a TIFF into SFTP              │
│     - poll GET /batches/{bid}           │
│     - assert prediction appears < 30s  │
│                                         │
│  Any step fails → build blocked        │
└─────────────────────────────────────────┘
```

### 5. Latency Budgets (must be in README and demonstrated in demo)
```
API cached reads      p95 < 50ms    ← Redis hit
API uncached reads    p95 < 200ms   ← Postgres query
Inference per doc     p95 < 1.0s    ← ConvNeXt on CPU
End-to-end            p95 < 10s     ← SFTP drop → visible in API
```

### 6. Structured JSON Logs
Every request and every worker job emits a JSON log line:
```json
{
  "timestamp": "2026-05-12T10:00:00Z",
  "request_id": "uuid-abc-123",
  "service": "api",
  "level": "INFO",
  "event": "prediction_created",
  "batch_id": 7,
  "label": "invoice",
  "confidence": 0.91
}
```
The `request_id` is generated at the API layer and passed to the queue job — the same ID appears in api logs, queue logs, and worker logs for the same document. This makes debugging possible across services.

### 7. Documentation Files (repo root)
| File | Contents |
|---|---|
| `ARCH.md` | Architecture diagram, layer descriptions, data flow |
| `DECISIONS.md` | Why RQ not Celery, why ConvNeXt, why Casbin, etc. |
| `RUNBOOK.md` | How to start, stop, reset, add a user, swap the model |
| `SECURITY.md` | Secrets policy, Vault setup, what to do if a key leaks |
| `COLLABORATION.md` | Trello link, who owned what, conflict resolution |
| `LICENSES.md` | RVL-CDIP academic/research use flag |

---

## Phase 11: Collaboration — Trello Board is Graded

**This is not optional.** A perfect codebase with an empty Trello board fails the collaboration dimension.

### What the board must show:
```
TO DO → IN PROGRESS → REVIEW → DONE

Cards must exist for every component:
  - classifier training (Colab)
  - API surface (routers)
  - services / repositories
  - ingestion worker
  - inference worker
  - Postgres + Alembic migrations
  - Redis cache setup
  - MinIO integration
  - SFTP integration
  - Vault integration
  - Casbin policies + audit log
  - golden-set test
  - CI pipeline
  - docker-compose wiring
  - latency budget measurement
  - all README/doc files
  - presentation prep
```

### Rules:
- Cards must be **distributed across all 4 members** — not all under one person
- Cards must move through columns **during the week** — not all moved to Done on Thursday night
- Each member owns at least **one substantive component end to end**

### COLLABORATION.md must cover:
1. Who owned what component
2. How merges and code review were handled
3. Where the team got stuck and how you unblocked
4. One decision the team disagreed on and how you resolved it

---

## Phase 12: Think About — Edge Cases

These are exam questions. You will be asked about them on Friday.

### 1. MinIO unreachable mid-job
```
Worker dequeues job → downloads file from MinIO → MinIO goes down mid-upload of overlay PNG
  → job throws exception
  → RQ marks job as FAILED
  → retry with exponential backoff (RQ supports this)
  → after max retries → job moves to failed queue
  → alert logged, batch status set to ERROR
  → do NOT silently swallow the error
```

### 2. Redis container recreated (queue loss)
```
RQ jobs are stored in Redis lists.
If Redis container is recreated → all in-flight jobs are LOST.

Recovery strategy:
  - RQ has a "started" registry — jobs that were dequeued but not confirmed done
  - On worker startup: scan started registry, re-enqueue jobs older than a timeout
  - Batch rows in Postgres with status = "processing" for > N seconds = stale → re-enqueue
  - This is why Postgres is the source of truth, not Redis
```

### 3. Last admin demoting themselves
```
PATCH /admin/users/{id}/role { role: "auditor" }  where id = last admin
  → service.toggle_role() runs
  → query: COUNT users WHERE role = 'admin' → returns 1
  → requested change would make it 0
  → BLOCK: raise AdminProtectionError("Cannot remove last admin")
  → router catches → returns 400 with clear message
  → audit log still records the ATTEMPT
```

### 4. Cache says one thing, DB says another
```
How it happens:
  - Cache invalidation failed (Redis blip after a write)
  - Cache TTL not set correctly (stale data served indefinitely)

How to detect:
  - Compare /batches/{bid} response with direct DB query → mismatch = stale cache
  - Structured logs show cache HIT for a key that should have been invalidated

Resolution:
  - Manual: flush the Redis key for that resource
  - Preventive: always invalidate AFTER the DB write commits, never before
  - TTL as a safety net: even if invalidation fails, cache expires eventually
```

### 5. Malformed SFTP drop
```
File arrives at sftp-ingest worker:

  Zero-byte file    → size check fails → quarantine folder + log entry
  Non-image file    → TIFF header check fails → quarantine folder + log entry
  1GB CSV           → size limit check fails → quarantine folder + log entry
  Duplicate file    → hash check against processed set → skip + log

NEVER enqueue a file that failed validation.
NEVER crash the worker — catch all exceptions, log them, continue polling.
Quarantine = move to /sftp/quarantine/ + write structured JSON log with:
  filename, size, detected_type, error_reason, timestamp
```

### 6. Swapping the model to a newer fine-tune
```
New model trained on Colab:
  1. New classifier.pt + updated model_card.json (new SHA-256)
  2. Run golden.py against new weights → must pass
  3. Commit new artifacts to repo

Deploy without dropping in-flight jobs:
  1. sftp-ingest continues queueing jobs normally
  2. Bring worker DOWN
  3. Wait: all jobs in queue drain or timeout
  4. Swap new classifier.pt (update git LFS pointer)
  5. Bring worker UP → startup check validates new SHA-256
  6. Worker now uses new model for all new jobs

Jobs that were already enqueued but not yet processed:
  - They run on the NEW model after the swap
  - This is acceptable — the queue holds file paths, not preprocessed tensors
  - If strict model versioning is needed: tag each job with model_version
    and have worker reject jobs for a different version (out of scope here)
```

---

## Phase 13: Required Libraries — Every Choice Defended

| Library | Why This One |
|---|---|
| **Python 3.11** | Best performance for async workloads; required by spec |
| **torch ≥ 2.4 + torchvision ≥ 0.19** | ConvNeXt weights only available in torchvision; torch 2.x has compile() for speed |
| **pydantic ≥ 2** | V2 is significantly faster than V1; required for fastapi-users compat |
| **FastAPI** | Async-native, automatic OpenAPI docs, integrates with fastapi-users/cache2 |
| **SQLAlchemy 2.x + Alembic** | SQLAlchemy 2.x has clean async support; Alembic is the standard migration tool |
| **fastapi-users** | Full auth lifecycle (register, login, JWT, password reset) with SQLAlchemy adapter — avoids writing auth from scratch |
| **Casbin (SQLAlchemy adapter)** | Policy stored in DB, not code; live policy updates without restart |
| **fastapi-cache2** | Decorator-based caching, Redis backend, built for FastAPI |
| **RQ (not Celery)** | Simpler, Redis-native, no broker/backend split; spec explicitly forbids Celery |
| **HashiCorp Vault KV v2** | Industry standard secret store; dev mode for local use; KV v2 supports versioned secrets |
| **MinIO** | S3-compatible API — same code works against real AWS S3 in production |
| **atmoz/sftp** | Lightweight, configurable SFTP server in one docker image |
| **Postgres 16** | Mature, reliable; Casbin and fastapi-users both have first-class SQLAlchemy adapters |
| **Redis 7** | Dual-use: RQ queue (lists) + fastapi-cache2 (strings/hashes); no extra service needed |

---

## Phase 14: Friday Presentation — What to Prepare

20 minutes. All four speak. All four answer questions.

### Agenda:
```
1. Architecture walkthrough (5 min)
   - Pick ONE endpoint (e.g. GET /batches/{bid})
   - Trace live: router → service → repo → DB query
   - Show the service that invalidates cache on write
   - Show the repo with zero business logic

2. Live demo (8 min)
   - Start stack from clean clone: docker-compose up
   - SCP a TIFF into SFTP: scp doc.tiff user@localhost:/upload/
   - Watch it land: poll GET /batches/{bid} until prediction appears
   - Demo 3 roles: log in as admin, reviewer, auditor → show different access
   - Toggle a role → show cache invalidation working (next request has new permissions)

3. Secrets discipline (2 min)
   - Run: grep -ri 'password' app/  → zero matches
   - Kill Vault container → restart api → show it refuses to start

4. CI gate (2 min)
   - Show a commit with a deliberately broken golden image expected label
   - Push it → CI fails on golden-set test
   - Show the failure in GitHub Actions

5. Collaboration (2 min)
   - Walk through Trello board: who owned what, card history
   - One specific bug you hit and fixed

6. Q&A (1 min buffer)
   - Expect: "explain your teammate's code for X"
   - Expect: "add a new endpoint live — GET /users/{id}/audit-history"
```

### The live endpoint addition — how to stay calm:
```
They say: "Add GET /users/{id}/predictions — returns all predictions made by a user's batches"

You say: "Three files to touch:"
  1. app/api/predictions.py     → add route, call service
  2. app/services/prediction_service.py → add method, call repo
  3. app/repositories/prediction_repo.py → add SQLAlchemy query

That's it. No other file changes. This is why we enforced the layers.
```

---

## Phase 15: Rules — What Gets You Graded Down

### NO VIBE CODING
Every line of code must be understood by the person who wrote it AND their teammates. On Friday, graders will point to a random function and ask the person who didn't write it to explain it. "I didn't write that part" is a failing answer.

### THE ARCHITECTURE IS THE GRADE
```
Scenario A: ConvNeXt top-1 = 93%, but router queries DB directly
  → LOWER SCORE

Scenario B: ConvNeXt top-1 = 88%, clean layered architecture
  → HIGHER SCORE

A slightly worse model in a clean codebase beats a better model in a tangled one.
```

### THE TRELLO BOARD IS GRADED TOO
```
FAILS:
  ✗ Empty board or all cards under one person
  ✗ Board filled in the day before submission
  ✗ Cards never moved through columns

PASSES:
  ✓ Cards distributed across all 4 members
  ✓ Cards moving through TO DO → IN PROGRESS → REVIEW → DONE during the week
  ✓ Every major component has a card with an owner
```

---

## Phase 16: Missing Details — Filling the Gaps

### What Is a Batch?
The spec mentions "batch listing" and "batch state change" but never defines batch explicitly. A **batch** is a logical grouping of one or more documents dropped together in a single SFTP session.

```
Batch lifecycle:
  PENDING    → files detected by sftp-ingest, uploaded to MinIO, jobs enqueued
  PROCESSING → worker has picked up at least one job from this batch
  DONE       → all jobs in the batch have completed successfully
  ERROR      → one or more jobs failed after max retries

Batch row in Postgres:
  id, status, created_at, updated_at, file_count, completed_count
```

Every prediction row links back to a batch via `batch_id`. When a user calls `GET /batches/{bid}` they see the batch status + all its predictions.

---

### The Annotated Overlay PNG — What It Actually Is
The worker draws a visual annotation on the original TIFF after classification:
```
Original TIFF (grayscale document image)
        +
Label text drawn on top: "invoice  91.4%"
        +
Colored bounding box or header bar
        =
Overlay PNG saved to MinIO at: overlays/{batch_id}/{filename}_overlay.png
```
This is stored in MinIO and accessible via the API so reviewers can visually inspect the classification.

---

### Casbin Policy Table Structure
Casbin stores rules as rows in a `casbin_rule` table:

```
ptype | v0        | v1                      | v2
------+-----------+-------------------------+------
p     | admin     | /admin/*                | *
p     | admin     | /audit-log              | GET
p     | reviewer  | /batches                | GET
p     | reviewer  | /batches/*              | GET
p     | reviewer  | /predictions/*          | PATCH
p     | auditor   | /batches                | GET
p     | auditor   | /batches/*              | GET
p     | auditor   | /audit-log              | GET
```

On every request: Casbin checks `(user_role, requested_path, HTTP_method)` against the table. If no matching rule → 403. This is why the table being empty = api refuses to boot (no rules = undefined behavior).

---

### RQ Job Payload — What Goes Into the Queue
```json
{
  "object_key": "uploads/batch_7/invoice_scan.tif",
  "batch_id": 7,
  "original_filename": "invoice_scan.tif",
  "submitted_at": "2026-05-12T10:00:00Z",
  "request_id": "uuid-abc-123"
}
```
The `request_id` is generated at the sftp-ingest layer and flows through to the worker logs — this is how you trace a single document across all services in the logs.

---

### SHA-256 Verification at Startup — How It Works
```
At api/worker startup:
  1. Open classifier.pt in binary mode
  2. Stream the bytes through hashlib.sha256()
  3. Compare the resulting hex digest against model_card.json["sha256"]
  4. Match → proceed
  5. Mismatch → log CRITICAL + sys.exit(1)

Why stream instead of load all at once? The file is ~110-190MB.
Streaming avoids loading it fully into memory just for hashing.
```

---

### Preprocessing Must Match Training EXACTLY
This is the most common silent bug in ML pipelines. If training used:
```
mean = [0.485, 0.456, 0.406]
std  = [0.229, 0.224, 0.225]
```
Then inference must use the exact same values. A mismatch produces garbage predictions that look plausible but are wrong.

**Solution:** Define the preprocessing transforms ONCE in a shared module (`app/classifier/transforms.py`) and import it in both the Colab training notebook AND the inference worker. Never define it twice.

---

### Git LFS Setup for Weights
```
Before committing classifier.pt:
  git lfs install
  git lfs track "*.pt"
  git add .gitattributes
  git commit -m "track .pt files with git LFS"
  git add app/classifier/models/classifier.pt
  git commit -m "add classifier weights"
```
Without LFS, a 110MB binary in git history bloats the repo permanently and makes cloning slow. LFS stores the binary separately and puts a pointer file in git.

---

### Golden Image Selection Strategy
50 images from the test split. How to pick deliberately:
```
- ~3 images per class (16 classes × 3 = 48, pick 2 more from hardest classes)
- "Easy" cases: images that look exactly like their class (clear invoice layout, obvious letter format)
- "Ambiguous" cases: images that could be mistaken for another class:
    letter  ↔ memo         (both are text documents with similar layout)
    form    ↔ questionnaire (both have fillable fields)
    scientific report ↔ scientific publication (both are academic)
    budget  ↔ invoice      (both have tabular financial data)
- Pick at least 2-3 ambiguous cases per visually similar pair
```

---

## Phase 17: Implementation Plan — Phase by Phase

This is the build order. Dependencies flow downward — nothing in a later phase can be built before its dependencies exist.

```
WEEK TIMELINE (assuming ~5 working days)

Day 1   →  Project setup + Colab training starts (parallel)
Day 2   →  Infrastructure + DB layer
Day 3   →  Services + Auth + Permissions
Day 4   →  Workers + API layer + Caching
Day 5   →  CI + Logging + Integration testing
Day 6   →  Polish + latency measurement + docs
Day 7   →  Presentation prep + submission
```

---

### IMPLEMENTATION PHASE 1 — Project Foundation
**Must happen before anything else.**

```
Tasks:
  ✦ Create GitHub repo, invite all 4 members
  ✦ Set up git LFS (track *.pt)
  ✦ Initialize UV project with all required dependencies
  ✦ Create .env.example with all required keys (no values)
  ✦ Create LICENSES.md (RVL-CDIP academic use flag)
  ✦ Create empty directory structure:
      app/
        api/
        services/
        repositories/
        domain/
        infra/
        db/
        classifier/
          models/
          eval/
  ✦ Set up Trello board, assign cards to all 4 members
  ✦ Write minimal docker-compose.yml with all 9 services declared
```

---

### IMPLEMENTATION PHASE 2 — Colab Training (runs in parallel with infra)
**Owned by: Member 1. Runs on Colab, not locally.**

```
Steps:
  1. Mount Google Drive or use Colab storage
  2. Download RVL-CDIP to Colab session
  3. Parse train.txt, val.txt, test.txt → build dataset objects
  4. Stratified sample from train split (~30-50%)
  5. Define preprocessing transforms (save to transforms.py — ship to repo)
  6. Load ConvNeXt Tiny from torchvision, replace head (1000→16 classes)
  7. Freeze backbone, train head only (3-5 epochs, monitor val loss)
  8. Optionally unfreeze last layers, lower LR, train more
  9. Evaluate on FULL 40k test split → record top-1, top-5, per-class accuracy
  10. Hand-pick 50 golden images (strategy: Phase 16)
  11. Save golden_expected.json
  12. Compute SHA-256 of classifier.pt
  13. Write model_card.json
  14. Commit artifacts via git LFS

Deliverable: classifier.pt, model_card.json, golden_images/, golden_expected.json
Blocks: inference worker cannot be built without classifier.pt
```

---

### IMPLEMENTATION PHASE 3 — Infrastructure (docker-compose)
**Owned by: Member 2.**

```
Steps:
  1. Write full docker-compose.yml:
     - vault (hashicorp/vault, dev mode, root token from .env)
     - db (postgres:16, volume for persistence)
     - redis (redis:7)
     - minio (minio/minio, create bucket on startup)
     - sftp (atmoz/sftp, configure upload user + folder)
     - migrate (your build, alembic entrypoint, depends_on: db)
     - api (your build, depends_on: migrate, vault, redis, minio)
     - worker (your build, depends_on: migrate, vault, redis, minio)
     - sftp-ingest (your build, depends_on: sftp, redis, minio)

  2. Write Vault initialization script:
     - Enable KV v2 secrets engine
     - Seed all required secrets (jwt_signing_key, postgres_password, etc.)
     - Run as a one-time init job in docker-compose

  3. Write MinIO initialization:
     - Create bucket: "documents" on first startup
     - Create bucket: "overlays" on first startup

  4. Verify: docker-compose up brings everything online, all services healthy

Deliverable: working docker-compose.yml, all infra containers running
Blocks: nothing else can be tested without this
```

---

### IMPLEMENTATION PHASE 4 — Database Layer
**Owned by: Member 2 (continues) or Member 3.**

```
Steps:
  1. Write SQLAlchemy ORM models (app/db/models.py):
     - User (id, email, hashed_password, role, created_at)
     - Batch (id, status, created_at, updated_at, file_count, completed_count)
     - Prediction (id, batch_id, filename, object_key, label, confidence,
                   all_probabilities, overlay_key, created_at)
     - AuditLog (id, actor_id, action, target, timestamp)
     - CasbinRule (ptype, v0, v1, v2, v3, v4, v5)  ← managed by Casbin

  2. Write Pydantic domain models (app/domain/):
     - UserDomain, BatchDomain, PredictionDomain, AuditEntryDomain

  3. Write Alembic migrations:
     - Initial migration: create all tables
     - Seed migration: insert default Casbin policy rules
     - Seed migration: create initial admin user

  4. Write repositories (app/repositories/):
     - user_repo.py     → get_by_id, get_by_email, create, update_role
     - batch_repo.py    → create, get_by_id, list_all, update_status
     - prediction_repo.py → create, get_by_batch, get_recent
     - audit_repo.py    → create, list_all, list_by_actor

Deliverable: migrate container runs clean, all tables created
Blocks: services cannot be written without repos
```

---

### IMPLEMENTATION PHASE 5 — Vault + Auth + Permissions
**Owned by: Member 3.**

```
Steps:
  1. Write Vault adapter (app/infra/vault.py):
     - get_secret(path) → fetches from Vault KV v2 at startup
     - Called once on startup, secrets cached in memory

  2. Write startup checks (app/startup.py):
     - Check classifier.pt exists
     - Verify SHA-256 against model_card.json
     - Check model_card top-1 >= README threshold
     - Fetch all secrets from Vault (fail if unreachable)
     - Check Casbin policy table not empty

  3. Configure fastapi-users:
     - SQLAlchemy user model adapter
     - JWT strategy with key from Vault
     - Register/login/me routes

  4. Configure Casbin:
     - SQLAlchemy adapter pointing to casbin_rule table
     - Load policy from DB on startup
     - Enforce on every protected route via FastAPI dependency

  5. Write auth dependency (app/api/deps.py):
     - get_current_user → validates JWT, returns UserDomain
     - require_role(role) → checks Casbin policy, raises 403 if denied

Deliverable: POST /auth/register, POST /auth/login, GET /me working with roles enforced
Blocks: all protected API routes depend on this
```

---

### IMPLEMENTATION PHASE 6 — Service Layer
**Owned by: Members 3 + 4 (split by domain).**

```
Services to write (app/services/):

  user_service.py:
    - register_user(email, password) → hashes password, creates user
    - toggle_role(actor_id, target_id, new_role):
        1. Check actor is admin
        2. Check not demoting last admin → raise if so
        3. repo.update_role()
        4. Update Casbin policy
        5. audit_repo.create(role_change entry)
        6. cache.invalidate(target_id)

  batch_service.py:
    - create_batch() → new batch row, status=PENDING
    - get_batch(bid) → repo.get_by_id(), check cache first
    - list_batches() → repo.list_all(), check cache first
    - update_status(bid, status) → repo, audit log, cache invalidate

  prediction_service.py:
    - create_prediction(batch_id, ...) → repo.create()
    - relabel(pred_id, new_label, actor_id):
        1. Check confidence < 0.7 (reviewer constraint)
        2. repo.update label
        3. audit_repo.create(relabel entry)
        4. cache.invalidate(batch_id)
    - get_recent() → check cache → repo.get_recent()

Deliverable: all business logic centralized, cache invalidation in one place
Blocks: API routers depend on services
```

---

### IMPLEMENTATION PHASE 7 — API Routers + Caching
**Owned by: Member 3.**

```
Routers to write (app/api/):

  auth.py      → register, login (fastapi-users handles this)
  users.py     → GET /me, PATCH /admin/users/{id}/role
  batches.py   → GET /batches, GET /batches/{bid}
  predictions.py → GET /predictions/recent, PATCH /predictions/{id}
  audit.py     → GET /audit-log

Cache decorators:
  @cache(expire=60)  on GET /me
  @cache(expire=30)  on GET /batches
  @cache(expire=30)  on GET /batches/{bid}
  @cache(expire=15)  on GET /predictions/recent

Each router method: parse params → call service → return response
No SQLAlchemy. No cache calls. No business logic.

Deliverable: all endpoints working, caching active, permissions enforced
```

---

### IMPLEMENTATION PHASE 8 — Workers
**Owned by: Member 4.**

```
sftp-ingest worker (app/workers/sftp_ingest.py):
  Loop every 5 seconds:
    1. SFTP adapter: list new files in upload folder
    2. For each file:
       a. Validate (size, TIFF header check)
       b. If invalid → quarantine + structured log → skip
       c. Upload to MinIO via blob adapter
       d. Create batch row via batch_service
       e. Enqueue RQ job with payload (object_key, batch_id, request_id)
       f. Move file to processed folder on SFTP

inference worker (app/workers/inference.py):
  RQ worker function:
    1. Download file from MinIO
    2. Apply preprocessing transforms (from shared transforms.py)
    3. Load model (loaded ONCE at worker startup, not per job)
    4. Run forward pass → probabilities
    5. Extract top-1, top-5
    6. Call prediction_service.create_prediction()
    7. Draw overlay PNG (PIL: write label + confidence on image)
    8. Upload overlay to MinIO
    9. Call batch_service.update_status()
    10. Log structured JSON with request_id

IMPORTANT: Model loads ONCE when the worker process starts.
Loading per job = 2-3 seconds overhead per document = fails latency budget.

Deliverable: end-to-end SFTP drop → prediction in API working
```

---

### IMPLEMENTATION PHASE 9 — Logging + request_id Propagation
**Owned by: Member 4.**

```
Logging setup:
  - Use Python structlog or standard logging with JSON formatter
  - Every log line is a JSON object (not plain text)
  - Fields: timestamp, level, service, event, request_id, + context fields

request_id flow:
  API request arrives → middleware generates UUID → stored in contextvars
  → included in all log lines during that request
  → passed into RQ job payload as "request_id"
  → worker reads request_id from job, stores in contextvars
  → all worker log lines include same request_id

Result: you can grep a single request_id and see the full trace:
  api: "job enqueued"       request_id=abc-123
  worker: "job started"     request_id=abc-123
  worker: "inference done"  request_id=abc-123
  worker: "prediction saved" request_id=abc-123
```

---

### IMPLEMENTATION PHASE 10 — CI Pipeline
**Owned by: Member 1 (who also did training).**

```
.github/workflows/ci.yml:

  on: [push, pull_request]

  jobs:
    lint:
      - ruff check app/
      - mypy app/

    build:
      - docker build -t doc-classifier .

    golden-test:
      - pip install torch torchvision
      - python app/classifier/eval/golden.py
      - must exit 0

    smoke-test:
      - docker-compose up -d
      - wait for api health check
      - scp test TIFF into sftp container
      - poll GET /batches until prediction appears (timeout 30s)
      - assert label is one of the 16 valid classes
      - docker-compose down

  Any job fails → build blocked → no merge
```

---

### IMPLEMENTATION PHASE 11 — Documentation + Latency Measurement

```
ARCH.md:
  - System diagram (copy from BRAINSTORM.md)
  - Layer descriptions
  - Data flow narrative

DECISIONS.md:
  - Why RQ not Celery
  - Why ConvNeXt Tiny/Small
  - Why Casbin over hardcoded roles
  - Why Vault over .env
  - Why 2 workers not 1
  - Training subset size decision

RUNBOOK.md:
  - How to start: cp .env.example .env && docker-compose up
  - How to reset DB: docker-compose down -v && docker-compose up
  - How to add a user via CLI
  - How to swap the model weights
  - How to check logs: docker-compose logs -f worker

SECURITY.md:
  - Secrets policy (Vault only, grep test)
  - What to do if JWT key leaks
  - SFTP user permissions

Latency measurement:
  - Use locust or k6 to hit API endpoints under load
  - Record p95 for cached + uncached reads
  - Time 10 inference runs, report p95
  - Time 10 e2e drops, report p95
  - All numbers go in README
```

---

### DEPENDENCY MAP — What Blocks What

```
Phase 1 (foundation)
  └─► Phase 3 (docker infra)
        └─► Phase 4 (DB layer)
              └─► Phase 5 (auth/vault)
                    └─► Phase 6 (services)
                          ├─► Phase 7 (API routers)
                          └─► Phase 8 (workers)
                                └─► Phase 9 (logging)

Phase 2 (Colab training)  ← runs in parallel with phases 3-6
  └─► Phase 8 (workers need classifier.pt)

Phases 7+8+9 complete
  └─► Phase 10 (CI smoke test needs full stack working)
        └─► Phase 11 (docs + latency measurement)
```

---

### Suggested Member Ownership

```
Member 1:  Colab training, golden set, model card, golden.py, CI pipeline
Member 2:  docker-compose, Vault init, MinIO, SFTP, Alembic migrations, ORM models
Member 3:  fastapi-users, Casbin, auth deps, all API routers, caching
Member 4:  sftp-ingest worker, inference worker, RQ setup, overlay PNG, logging
```

Every member must understand every other member's code — you will be asked about it on Friday.

---

## Phase 16: Submission Format

```
Project 6, [Name 1], [Name 2], [Name 3], [Name 4]
Repo:      https://github.com/.../doc-classifier-service
Trello:    https://trello.com/b/...
Tag:       v0.1.0-week6
Backbone:  convnext_tiny | ConvNeXt_Tiny_Weights.IMAGENET1K_V1
Freeze:    partial_unfreeze
Test top-1: 0.91 | Top-5: 0.99 | Worst-class: 0.81 (handwritten)
Latency p95: api-uncached=142ms  inference=820ms  e2e=7.2s
README contains: ARCH.md, DECISIONS.md, RUNBOOK.md, SECURITY.md, COLLABORATION.md
```
