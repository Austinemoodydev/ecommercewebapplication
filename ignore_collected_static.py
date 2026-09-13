from pathlib import Path

path = Path(".gitignore")
text = path.read_text(encoding="utf-8-sig") if path.exists() else ""

entries = [
    "staticfiles/",
]

lines = text.splitlines()

for entry in entries:
    if entry not in lines:
        lines.append(entry)

path.write_text(
    "\n".join(lines).strip() + "\n",
    encoding="utf-8",
)

print("staticfiles/ is ignored by Git.")
