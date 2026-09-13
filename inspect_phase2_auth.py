from pathlib import Path

files = [
    "accounts/models.py",
    "accounts/forms.py",
    "accounts/views.py",
    "accounts/urls.py",
]

output = Path("phase2_auth_inspection.txt")

with output.open("w", encoding="utf-8") as out:
    for filename in files:
        path = Path(filename)

        out.write("\n" + "=" * 80 + "\n")
        out.write(filename + "\n")
        out.write("=" * 80 + "\n\n")

        if path.exists():
            out.write(path.read_text(encoding="utf-8-sig"))
        else:
            out.write("FILE NOT FOUND")

        out.write("\n")

print(f"Created: {output.resolve()}")
