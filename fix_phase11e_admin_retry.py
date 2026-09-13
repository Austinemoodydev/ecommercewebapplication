from pathlib import Path
import shutil


path = Path("notifications/views.py")

backup = Path(
    "notifications/views.py.phase11e-legacy-backup"
)

if not backup.exists():
    shutil.copy2(
        path,
        backup,
    )


text = path.read_text(
    encoding="utf-8-sig"
)


# Add helper import.
text = text.replace(
    '''    retry_notification,
    retry_notification_channel,
)
''',
    '''    retry_notification,
    retry_notification_channel,
    retryable_failed_channels,
)
''',
    1,
)


# Replace both direct channel checks used by
# normal retry and bulk retry.
old = '''    retryable = (
        channel_retry_available(
            notification,
            "email",
        )
        or
        channel_retry_available(
            notification,
            "sms",
        )
    )
'''

new = '''    retryable = bool(
        retryable_failed_channels(
            notification
        )
    )
'''


count = text.count(old)

if count == 0:
    raise RuntimeError(
        "Could not locate retryability checks."
    )


text = text.replace(
    old,
    new,
)


path.write_text(
    text,
    encoding="utf-8",
)


print(
    f"Updated {count} admin retry compatibility check(s)."
)

print(
    "No migration required."
)
