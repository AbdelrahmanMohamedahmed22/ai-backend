# FastAPI Starter

A minimal FastAPI application with root and health-check endpoints.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

```powershell
uvicorn main:app --reload
```

The app will be available at <http://127.0.0.1:8000>.

## Endpoints

- `GET /` — welcome message
- `GET /health` — health status
- `GET /api/v1/info` — service information
- `GET /api/v1/items` — list all items
- `POST /api/v1/items` — create an item
- `GET /api/v1/items/{item_id}` — get one item by ID
- `GET /docs` — Swagger UI
- `GET /redoc` — ReDoc API documentation

### Create an item

```json
{
  "name": "Example item",
  "description": "Optional description"
}
```
