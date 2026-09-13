from pathlib import Path

files = [
    Path("static/css/styles.css"),
    Path("static/css/auth.css"),
]

replacements = {
    # Deep royal blue -> lighter professional blue
    "#0B4DBB": "#3B82F6",
    "#073B8F": "#2563EB",

    # Existing bright blue
    "#2563EB": "#3B82F6",

    # Dark blue shadows
    "rgba(7, 59, 143, .18)": "rgba(37, 99, 235, .16)",
    "rgba(11, 77, 187, .14)": "rgba(59, 130, 246, .14)",
}

for path in files:

    if not path.exists():
        print(f"SKIPPED: {path} not found")
        continue

    text = path.read_text(encoding="utf-8-sig")

    # Do replacements in a controlled order so #2563EB
    # does not accidentally overwrite a newly-created value.
    text = text.replace("#0B4DBB", "#3B82F6")
    text = text.replace("#073B8F", "#2563EB")

    text = text.replace(
        "rgba(7, 59, 143, .18)",
        "rgba(37, 99, 235, .16)",
    )

    text = text.replace(
        "rgba(11, 77, 187, .14)",
        "rgba(59, 130, 246, .14)",
    )

    path.write_text(text, encoding="utf-8")

    print(f"UPDATED: {path}")

print()
print("NEW THEME")
print("Primary Blue : #3B82F6")
print("Navbar Blue  : #2563EB")
print("Hover Blue   : #1D4ED8")
print("Orange       : #F97316")
print("White        : #FFFFFF")
print("Soft Blue    : #EFF6FF")
print()
print("No layout, fonts or spacing changed.")
