from pathlib import Path
import shutil


path = Path("notifications/tasks.py")

if not path.exists():
    raise RuntimeError(
        "notifications/tasks.py not found."
    )


backup = Path(
    "notifications/tasks.py.phase11e-legacy-backup"
)

if not backup.exists():
    shutil.copy2(
        path,
        backup,
    )


text = path.read_text(
    encoding="utf-8-sig"
)


start = text.find(
    "def retryable_failed_channels("
)

end = text.find(
    "\n\n\n@shared_task\n"
    "def retry_notification_channel(",
    start,
)


if start == -1 or end == -1:
    raise RuntimeError(
        "Could not locate retryable_failed_channels()."
    )


replacement = r'''def retryable_failed_channels(
    notification,
):

    channels = set()


    # --------------------------------------------------------
    # MODERN PHASE 11D / 11E RECORDS
    # --------------------------------------------------------

    if channel_retry_available(
        notification,
        "email",
    ):
        channels.add(
            "email"
        )


    if channel_retry_available(
        notification,
        "sms",
    ):
        channels.add(
            "sms"
        )


    if channels:
        return channels


    # --------------------------------------------------------
    # LEGACY COMPATIBILITY
    # --------------------------------------------------------
    #
    # Notifications created before Phase 11D only had the
    # overall `status` field.
    #
    # Example:
    #
    #   status="failed"
    #   email_status="not_requested"
    #   sms_status="not_requested"
    #
    # These rows must remain retryable after upgrading to
    # per-channel delivery tracking.
    #
    # We intentionally enable this fallback only when both
    # per-channel states are still "not_requested". This avoids
    # accidentally retrying modern skipped/successful channels.

    legacy_record = (
        notification.status
        in {
            "failed",
            "partial",
        }
        and
        notification.email_status
        == "not_requested"
        and
        notification.sms_status
        == "not_requested"
    )


    if not legacy_record:
        return channels


    requested = (
        _requested_channels(
            notification
        )
    )


    if (
        "email" in requested
        and
        notification.email_attempts
        < MAX_CHANNEL_DELIVERY_ATTEMPTS
    ):
        channels.add(
            "email"
        )


    if (
        "sms" in requested
        and
        notification.sms_attempts
        < MAX_CHANNEL_DELIVERY_ATTEMPTS
    ):
        channels.add(
            "sms"
        )


    return channels
'''


text = (
    text[:start]
    + replacement
    + text[end:]
)


path.write_text(
    text,
    encoding="utf-8",
)


print("=" * 72)
print("PHASE 11E LEGACY RETRY COMPATIBILITY REPAIRED")
print("=" * 72)
print()
print("Legacy overall failed notifications are retryable.")
print("Modern per-channel retry rules remain unchanged.")
print("No migration required.")
