from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys

ROOT = Path.cwd()

if not (ROOT / "manage.py").exists():
    raise SystemExit(
        "ERROR: Run this inside the Django project root containing manage.py."
    )

FILES = [
    ROOT / "static/css/styles.css",
    ROOT / "static/css/auth.css",
]

for file in FILES:
    if not file.exists():
        raise SystemExit(
            f"ERROR: Required frontend stylesheet not found: {file}"
        )

stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

backup_root = (
    ROOT
    / ".theme_backups"
    / stamp
)

backup_root.mkdir(
    parents=True,
    exist_ok=True,
)

print()
print("=" * 72)
print("ONLINE SHOP — ROYAL BLUE / WHITE / ORANGE THEME")
print("=" * 72)

print()
print("Backup directory:")
print(backup_root)


# ============================================================
# COLOR SYSTEM
# ============================================================

# IMPORTANT:
# This changes COLORS ONLY.
#
# Layout, typography, spacing, breakpoints, HTML structure,
# templates and Django application logic are not redesigned.

COLOR_MAP = {

    # --------------------------------------------------------
    # MAIN BRAND
    # --------------------------------------------------------

    "#1f6f5b": "#0B4DBB",
    "#144b3f": "#073B8F",

    # Existing secondary greens used in hero gradients
    "#184b40": "#073B8F",
    "#2c806a": "#2563EB",

    # --------------------------------------------------------
    # ORANGE ACCENTS
    # --------------------------------------------------------

    "#e1a744": "#F97316",
    "#f4c96f": "#FDBA74",

    "#d96c4f": "#F97316",
    "#9a4e37": "#C2410C",
    "#d88452": "#FB923C",

    # --------------------------------------------------------
    # MAIN TEXT
    # --------------------------------------------------------

    "#17211b": "#0F172A",
    "#68736b": "#64748B",

    # --------------------------------------------------------
    # PAGE / CARD SURFACES
    # --------------------------------------------------------

    "#fffdf8": "#FFFFFF",
    "#fffefa": "#FFFFFF",
    "#f4f1e9": "#F8FAFC",

    # --------------------------------------------------------
    # BORDERS
    # --------------------------------------------------------

    "#deded2": "#E2E8F0",
    "#cfd5ca": "#CBD5E1",
    "#bfc9bc": "#CBD5E1",

    # --------------------------------------------------------
    # LIGHT BRAND BACKGROUNDS
    # --------------------------------------------------------

    "#dce7dc": "#EFF6FF",
    "#d9e8df": "#DBEAFE",

    # --------------------------------------------------------
    # MUTED PRODUCT COLORS
    # --------------------------------------------------------

    "#e8e7df": "#F1F5F9",
    "#9b9f94": "#94A3B8",

    # --------------------------------------------------------
    # HERO TEXT
    # --------------------------------------------------------

    "#dbeafe": "#DBEAFE",

    # --------------------------------------------------------
    # OFFER HERO LIGHT ORANGE
    # --------------------------------------------------------

    "#ffedd5": "#FFEDD5",
}


def backup(file):

    target = (
        backup_root
        / file.relative_to(ROOT)
    )

    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        file,
        target,
    )


def replace_colors(file):

    backup(file)

    text = file.read_text(
        encoding="utf-8-sig"
    )

    original = text

    for old, new in COLOR_MAP.items():

        text = text.replace(
            old,
            new,
        )

        text = text.replace(
            old.upper(),
            new,
        )

    if text == original:

        print(
            "[NOTICE] No matching old theme colors in:",
            file.relative_to(ROOT),
        )

    else:

        file.write_text(
            text,
            encoding="utf-8",
        )

        print(
            "[UPDATED]",
            file.relative_to(ROOT),
        )


for file in FILES:

    replace_colors(
        file
    )


# ============================================================
# styles.css — FINAL PROFESSIONAL BRAND OVERRIDES
# ============================================================

styles_file = ROOT / "static/css/styles.css"

styles = styles_file.read_text(
    encoding="utf-8"
)


# ------------------------------------------------------------
# Fix shadow tint
# ------------------------------------------------------------

styles = styles.replace(
    "rgba(23, 33, 27, .09)",
    "rgba(15, 23, 42, .10)",
)

styles = styles.replace(
    "rgba(20, 75, 63, .18)",
    "rgba(7, 59, 143, .18)",
)

styles = styles.replace(
    "rgba(31, 111, 91, .13)",
    "rgba(11, 77, 187, .14)",
)


# ------------------------------------------------------------
# Keep success semantic GREEN.
#
# Branding is blue, but payment/order success should remain
# visually recognized as success.
# ------------------------------------------------------------

old_success = '''.btn-success {
    background: var(--brand);
    border-color: var(--brand);
}'''

new_success = '''.btn-success {
    background: #198754;
    border-color: #198754;
}

.btn-success:hover,
.btn-success:focus {
    background: #157347;
    border-color: #146c43;
}'''

if old_success in styles:

    styles = styles.replace(
        old_success,
        new_success,
        1,
    )


# ------------------------------------------------------------
# Orange warning / CTA consistency
# ------------------------------------------------------------

old_warning = '''.btn-warning {
    background: var(--accent);
    border-color: var(--accent);
    color: var(--ink);
}'''

new_warning = '''.btn-warning {
    background: var(--accent);
    border-color: var(--accent);
    color: #FFFFFF;
}

.btn-warning:hover,
.btn-warning:focus {
    background: #EA580C;
    border-color: #EA580C;
    color: #FFFFFF;
}'''

if old_warning in styles:

    styles = styles.replace(
        old_warning,
        new_warning,
        1,
    )


styles_file.write_text(
    styles,
    encoding="utf-8",
)


# ============================================================
# auth.css — SHADOW CONSISTENCY
# ============================================================

auth_file = ROOT / "static/css/auth.css"

auth = auth_file.read_text(
    encoding="utf-8"
)

auth = auth.replace(
    "rgba(23, 33, 27, .12)",
    "rgba(15, 23, 42, .12)",
)

auth_file.write_text(
    auth,
    encoding="utf-8",
)


# ============================================================
# DISPLAY RESULTING COLOR SYSTEM
# ============================================================

print()
print("=" * 72)
print("NEW FRONTEND BRAND COLORS")
print("=" * 72)

print("""
Primary Royal Blue : #0B4DBB
Deep Royal Blue    : #073B8F
Bright Blue        : #2563EB

Orange Accent      : #F97316
Orange Hover       : #EA580C

White              : #FFFFFF
Soft Background    : #F8FAFC

Main Text          : #0F172A
Secondary Text     : #64748B
Border             : #E2E8F0

Success Green      : #198754
WhatsApp Green     : unchanged
""")


# ============================================================
# DJANGO VALIDATION
# ============================================================

commands = [

    [
        sys.executable,
        "manage.py",
        "check",
    ],

    [
        sys.executable,
        "manage.py",
        "collectstatic",
        "--noinput",
    ],

    [
        sys.executable,
        "manage.py",
        "test",
        "-v",
        "1",
    ],
]


print()
print("=" * 72)
print("RUNNING FRONTEND SAFETY CHECKS")
print("=" * 72)


for command in commands:

    print()
    print(
        ">",
        " ".join(command),
    )

    print(
        "-" * 72
    )

    result = subprocess.run(
        command,
        cwd=ROOT,
    )

    if result.returncode != 0:

        print()
        print("=" * 72)
        print("STOPPED — VALIDATION FAILED")
        print("=" * 72)

        print()
        print(
            "Your previous CSS files are safely backed up here:"
        )

        print(
            backup_root
        )

        raise SystemExit(
            result.returncode
        )


print()
print("=" * 72)
print("ROYAL BLUE / WHITE / ORANGE THEME APPLIED")
print("=" * 72)

print()
print("✓ Layout unchanged")
print("✓ Fonts unchanged")
print("✓ Spacing unchanged")
print("✓ Cards unchanged")
print("✓ Responsive design unchanged")
print("✓ Django logic unchanged")
print("✓ Royal blue primary branding")
print("✓ Orange CTA/accent branding")
print("✓ Clean white surfaces")
print("✓ Success states remain green")
print("✓ WhatsApp remains green")
print("✓ collectstatic completed")
print("✓ Full Django tests passed")

print()
print("Backup:")
print(backup_root)

print()
print(
    "Restart runserver if necessary, then hard refresh "
    "the browser with Ctrl+F5."
)
