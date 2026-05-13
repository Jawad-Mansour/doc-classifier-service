"""
Quick Start: API Skeleton

Step-by-step guide to extend the skeleton with a real router.
"""

# QUICK START: Adding a New Router

## Example: Create a Predictions Router

### Step 1: Define Schemas (app/api/schemas/prediction.py)
```python
from pydantic import BaseModel, Field

class PredictionRequest(BaseModel):
    image_path: str = Field(..., description="Path to TIFF image")

class PredictionResponse(BaseModel):
    prediction_id: str
    class_id: int
    class_name: str
    confidence: float
```

### Step 2: Create Service Layer (app/services/prediction_service.py)
```python
from app.repositories import PredictionRepository
from app.infra.cache import CacheService

class PredictionService:
    def __init__(self, repo: PredictionRepository, cache: CacheService):
        self.repo = repo
        self.cache = cache
    
    async def predict(self, image_path: str) -> dict:
        # Business logic here, NO HTTP
        # Call repo and infra only
        result = await self.repo.save_prediction(...)
        return result
```

### Step 3: Add Service Dependency (app/api/deps/auth.py)
```python
from app.services import PredictionService

async def get_prediction_service() -> PredictionService:
    repo = PredictionRepository()
    cache = CacheService()
    return PredictionService(repo, cache)

PredictionServiceDep = Annotated[
    PredictionService,
    Depends(get_prediction_service)
]
```

### Step 4: Create Router (app/api/routers/predictions.py)
```python
from fastapi import APIRouter
from app.api.deps.auth import PredictionServiceDep, RequestIDDep
from app.api.schemas.prediction import PredictionRequest, PredictionResponse

router = APIRouter(prefix="/predictions", tags=["predictions"])

@router.post("", response_model=PredictionResponse)
async def create_prediction(
    request: PredictionRequest,
    request_id: RequestIDDep,
    service: PredictionServiceDep,
) -> PredictionResponse:
    result = await service.predict(request.image_path)
    return PredictionResponse(**result)
```

### Step 5: Register Router (app/api/main.py)
```python
from app.api.routers import predictions

api_router.include_router(predictions.router)
```

### Step 6: Add Tests (tests/api/test_predictions.py)
```python
import pytest
from fastapi.testclient import TestClient

def test_create_prediction(client: TestClient):
    response = client.post(
        "/api/v1/predictions",
        json={"image_path": "test.tiff"},
        headers={"X-Request-ID": "test-123"}
    )
    assert response.status_code == 200
    assert response.json()["class_name"] in [...]
```

## Key Rules to Follow

1. **Routers stay thin**: Only validation + service calls
2. **Services have logic**: Only business rules, no HTTP
3. **Repositories do queries**: Only data access
4. **Dependencies are injected**: No hardcoding
5. **Tests are isolated**: Mock services in unit tests
6. **Schemas live in one place**: app/api/schemas/domain.py
7. **Request ID on all responses**: Via middleware
8. **Async everywhere**: Use async/await

## Architecture Checklist

When adding a new feature:
- [ ] Create schema in app/api/schemas/
- [ ] Create service in app/services/
- [ ] Create repository in app/repositories/ (if DB)
- [ ] Add dependency in app/api/deps/
- [ ] Create router in app/api/routers/
- [ ] Register router in app/api/main.py
- [ ] Add tests in tests/api/
- [ ] Document in README

## Running Tests
```bash
pytest tests/api/ -v
pytest tests/api/test_health.py -v
pytest tests/api/ --cov=app
```

## Starting the Server
```bash
uvicorn app.main:app --reload
```

Then visit http://localhost:8000/api/docs for interactive docs.

## Folder Size Expectations
- Routers: ~50 lines each
- Services: 100-200 lines each
- Repos: 50-150 lines each
- Tests: 50-100 lines per test file

If a file gets too big, split it by domain.
