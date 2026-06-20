from app.telemetry.logging import redact_event


def test_redact_event_removes_sensitive_fields() -> None:
    event = {
        "call_id": "call_123",
        "tool_call_id": "tool_123",
        "phone": "+15551234001",
        "date_of_birth": "1985-03-15",
        "email": "maria@example.test",
        "insurance_member_id": "member-123",
        "transcript": "My SSN is not relevant.",
    }

    redacted = redact_event(event)

    assert redacted["call_id"] == "call_123"
    assert redacted["phone"] == "[REDACTED]"
    assert redacted["date_of_birth"] == "[REDACTED]"
    assert redacted["transcript"] == "[REDACTED]"
