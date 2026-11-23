"""Create a local .env without overwriting an existing configuration."""
from pathlib import Path
import secrets

root = Path(__file__).resolve().parents[1]
target = root / ".env"
if target.exists():
    raise SystemExit(".env already exists; existing settings were preserved")
password = secrets.token_hex(16)
content = (root / ".env.example").read_text(encoding="utf-8")
content = content.replace("your_strong_password_here", password)
content = content.replace("your_secret_key_here", secrets.token_hex(32))
content = content.replace('ALLOWED_ORIGINS=["https://your-domain.com"]',
                          'ALLOWED_ORIGINS=["http://localhost:8080","http://localhost:5173"]')
content = content.replace("DOCS_ENABLED=False", "DOCS_ENABLED=True")
with target.open("x", encoding="utf-8") as handle:
    handle.write(content)
print("Created .env with generated local credentials. Telegram and dev login are disabled.")
