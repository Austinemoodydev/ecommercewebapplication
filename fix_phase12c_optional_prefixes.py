from pathlib import Path
import shutil


MODELS = Path("core/models.py")

if not MODELS.exists():

    raise RuntimeError(
        "core/models.py not found."
    )


backup = Path(
    "core/models.py.phase12c-optional-prefix-backup"
)

if not backup.exists():

    shutil.copy2(
        MODELS,
        backup,
    )


text = MODELS.read_text(
    encoding="utf-8-sig"
)


replacements = {

'''    invoice_prefix = models.CharField(
        max_length=20,
        default="INV",
    )
''':
'''    invoice_prefix = models.CharField(
        max_length=20,
        default="INV",
        blank=True,
    )
''',

'''    receipt_prefix = models.CharField(
        max_length=20,
        default="RCP",
    )
''':
'''    receipt_prefix = models.CharField(
        max_length=20,
        default="RCP",
        blank=True,
    )
''',

'''    credit_note_prefix = models.CharField(
        max_length=20,
        default="CN",
    )
''':
'''    credit_note_prefix = models.CharField(
        max_length=20,
        default="CN",
        blank=True,
    )
''',

}


for old, new in replacements.items():

    if old in text:

        text = text.replace(
            old,
            new,
            1,
        )

    elif new in text:

        print(
            "Already repaired."
        )

    else:

        raise RuntimeError(
            "Could not locate one of the "
            "document prefix fields."
        )


MODELS.write_text(
    text,
    encoding="utf-8",
)


print()
print("=" * 72)
print("PHASE 12C OPTIONAL PREFIX REPAIR APPLIED")
print("=" * 72)
print()
print("invoice_prefix     -> optional")
print("receipt_prefix     -> optional")
print("credit_note_prefix -> optional")
print()
print("Form clean methods will still fall back to:")
print("  INV")
print("  RCP")
print("  CN")
