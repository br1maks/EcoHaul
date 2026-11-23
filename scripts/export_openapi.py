"""Export the API contract without starting Telegram, Redis, or a database."""
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "backend"))
from app.main import app

target = root / "docs" / "api" / "openapi.json"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Exported {len(app.openapi()['paths'])} API paths")
