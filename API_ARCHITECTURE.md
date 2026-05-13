"""
API Architecture Documentation.

This document describes the FastAPI skeleton structure for the document classifier service.
"""

# API Skeleton Architecture

## Structure Overview

```
app/
├── main.py                          # FastAPI app factory
├── core/
│   ├── config.py                    # Application settings
│   └── security.py                  # Security/JWT/Casbin config (placeholder)
├── api/
│   ├── main.py                      # Router registration
│   ├── middleware/
│   │   ├── __init__.py
│   │   └── request_id.py            # Request ID middleware
│   ├── deps/
│   │   ├── __init__.py
│   │   └── auth.py                  # Dependency injection (JWT, DB, etc.)
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── common.py                # Common response models
│   │   ├── auth.py                  # Auth schemas (TODO)
│   │   ├── user.py                  # User schemas (TODO)
│   │   ├── batch.py                 # Batch schemas (TODO)
│   │   └── prediction.py            # Prediction schemas (TODO)
│   └── routers/
│       ├── __init__.py
│       ├── health.py                # Health check
│       ├── auth.py                  # Auth endpoints (TODO)
│       ├── users.py                 # User management (TODO)
│       ├── batches.py               # Batch processing (TODO)
│       ├── predictions.py           # Predictions (TODO)
│       └── audit.py                 # Audit logs (TODO)
├── auth/
│   ├── __init__.py
│   ├── jwt.py                       # JWT token handling (TODO)
│   ├── casbin.py                    # RBAC with Casbin (TODO)
│   └── users.py                     # User authentication (TODO)
├── services/
│   ├── __init__.py
│   ├── auth_service.py              # Auth business logic (TODO)
│   ├── user_service.py              # User operations (TODO)
│   ├── prediction_service.py        # Predictions (TODO)
│   └── batch_service.py             # Batch processing (TODO)
├── repositories/
│   └── ...                          # Data access layer (TODO)
└── infra/
    └── ...                          # External integrations (TODO)

tests/
├── api/
│   ├── conftest.py                  # Test fixtures
│   ├── test_health.py               # Health tests
│   ├── test_auth.py                 # Auth tests (TODO)
│   └── test_users.py                # User tests (TODO)
```

## Design Principles

### 1. **Thin Routers**
Routers only:
- Validate input via Pydantic
- Extract dependencies
- Call service layer
- Format responses

**Example:**
```python
@router.post("/predictions", response_model=PredictionResponse)
async def create_prediction(
    request: PredictionRequest,
    request_id: RequestIDDep,
    prediction_service: Annotated[PredictionService, Depends(get_prediction_service)],
) -> PredictionResponse:
    result = await prediction_service.predict(request)
    return result
```

### 2. **Service Layer**
Contains all business logic:
- No HTTP concerns
- Async by default
- Repository/infra injection
- Testable in isolation

### 3. **Repository Layer**
Data access only:
- DB queries
- Caching
- ORM calls

### 4. **Dependency Injection**
Uses FastAPI's Depends:
```python
# Clean, typed dependencies
RequestIDDep = Annotated[str, Depends(get_request_id)]
UserDep = Annotated[User, Depends(get_current_user)]
DBDep = Annotated[Session, Depends(get_db)]
```

### 5. **Schema Organization**
One schema file per domain:
```
schemas/
├── common.py          # Reusable (HealthResponse, ErrorResponse)
├── auth.py            # Auth (LoginRequest, TokenResponse)
├── user.py            # User (UserCreate, UserResponse)
├── prediction.py      # Predictions (PredictionRequest, Result)
└── batch.py           # Batches (BatchCreate, BatchStatus)
```

## Request Flow

```
HTTP Request
    ↓
RequestIDMiddleware (attach request_id to state)
    ↓
CORS Middleware
    ↓
Router (validate, inject deps)
    ↓
Service (business logic)
    ↓
Repository (data access)
    ↓
Response (formatted)
    ↓
HTTP Response (with X-Request-ID header)
```

## Middleware Stack

**Order matters** (outer → inner):
1. `RequestIDMiddleware` - Earliest for tracing
2. `CORSMiddleware` - Second, handles cross-origin
3. Built-in FastAPI middleware

## Router Registration Pattern

All routers included in `app/api/main.py`:
```python
api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)      # When ready
api_router.include_router(predictions.router)
```

Then included in `app/main.py`:
```python
app.include_router(api_router)
```

## Testing Strategy

### Unit Tests
Test services in isolation:
```python
@pytest.fixture
def prediction_service():
    repo = MockPredictionRepository()
    cache = MockCache()
    return PredictionService(repo, cache)

async def test_predict_valid_image(prediction_service):
    result = await prediction_service.predict(...)
    assert result.class_id in range(16)
```

### Integration Tests
Test routers with test client:
```python
def test_create_prediction_endpoint(client: TestClient):
    response = client.post(
        "/api/v1/predictions",
        json={"image": "..."},
        headers={"X-Request-ID": "test-123"}
    )
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
```

## Key Features Currently Implemented

✅ FastAPI app factory  
✅ Router registration pattern  
✅ Request ID middleware  
✅ CORS middleware  
✅ Health check endpoint  
✅ Pydantic v2 schemas  
✅ Dependency injection scaffold  
✅ Test fixtures and first test  
✅ Security settings placeholder

## TODO: Next Implementations

- [ ] JWT authentication (app/auth/jwt.py)
- [ ] Casbin RBAC (app/auth/casbin.py)
- [ ] User model and service
- [ ] Database integration
- [ ] Prediction service and router
- [ ] Batch processing router
- [ ] Audit logging
- [ ] Exception handlers (custom errors)
- [ ] Logging configuration
- [ ] Rate limiting
- [ ] Request/response compression

## Running the App

```bash
# Development
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Tests
pytest tests/api/ -v

# Docs
# OpenAPI: http://localhost:8000/api/docs
# ReDoc: http://localhost:8000/api/redoc
```

## Configuration

Load from `.env`:
```
DEBUG=true
LOG_LEVEL=DEBUG
DATABASE_URL=postgresql://user:pass@localhost/db
REDIS_URL=redis://localhost:6379
```

All settings via Pydantic BaseSettings.

## Clean Import Pattern

### Router (minimal)
```python
from fastapi import APIRouter
from app.api.schemas import PredictionResponse
from app.services import PredictionService
```

### Service (logic only)
```python
from app.repositories import PredictionRepository
from app.infra.cache import CacheService
```

### Core (config)
```python
from app.core.config import settings
from app.core.security import security_settings
```

No circular imports by keeping layers separate.
