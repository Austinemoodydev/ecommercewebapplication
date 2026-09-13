from pathlib import Path

path = Path(".gitignore")

existing = (
    path.read_text(encoding="utf-8-sig")
    if path.exists()
    else ""
)

entries = [
    ".env",
    "db.sqlite3",
    "config/dbfile/*.sql",
    "*.sql",
    "__pycache__/",
    "*.pyc",
    "venv/",
]

lines = existing.splitlines()

for entry in entries:
    if entry not in lines:
        lines.append(entry)

path.write_text(
    "\n".join(lines).strip() + "\n",
    encoding="utf-8",
)

print("Updated .gitignore")
