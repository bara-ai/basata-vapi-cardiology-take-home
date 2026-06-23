from typing import Any

SENSITIVE_FIELDS = {
    "phone",
    "verification_phone",
    "date_of_birth",
    "email",
    "insurance_member_id",
    "transcript",
}


def redact_event(event: dict[str, Any]) -> dict[str, Any]:
    return {key: "[REDACTED]" if key in SENSITIVE_FIELDS else value for key, value in event.items()}
