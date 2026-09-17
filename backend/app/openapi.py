"""Write the OpenAPI schema to frontend/openapi.json (no running server needed).

Used by the frontend's `npm run gen:api`. Run directly with:

    uv run python -m app.openapi
"""

import json

from app.config import BACKEND_DIR
from app.main import app

OUTPUT = BACKEND_DIR.parent / "frontend" / "openapi.json"


if __name__ == "__main__":
    OUTPUT.write_text(json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT}")
