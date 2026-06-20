from app.models.vapi import normalize_tool_calls


def test_normalizes_current_object_arguments_tool_call() -> None:
    payload = {
        "message": {
            "type": "tool-calls",
            "call": {"id": "call_123", "customer": {"number": "+15551234001"}},
            "toolCallList": [
                {
                    "id": "toolu_123",
                    "name": "find_patient",
                    "arguments": {"phone": "+15551234001", "date_of_birth": "1985-03-15"},
                }
            ],
        }
    }

    calls = normalize_tool_calls(payload)

    assert len(calls) == 1
    assert calls[0].tool_call_id == "toolu_123"
    assert calls[0].name == "find_patient"
    assert calls[0].arguments == {"phone": "+15551234001", "date_of_birth": "1985-03-15"}
    assert calls[0].call_id == "call_123"
    assert calls[0].customer_number == "+15551234001"


def test_normalizes_legacy_function_arguments_json_string() -> None:
    payload = {
        "message": {
            "type": "tool-calls",
            "toolCallList": [
                {
                    "id": "tc_xyz789",
                    "type": "function",
                    "function": {
                        "name": "list_providers",
                        "arguments": '{"specialty":"interventional_cardiology"}',
                    },
                }
            ],
        }
    }

    calls = normalize_tool_calls(payload)

    assert len(calls) == 1
    assert calls[0].tool_call_id == "tc_xyz789"
    assert calls[0].name == "list_providers"
    assert calls[0].arguments == {"specialty": "interventional_cardiology"}


def test_normalizes_tool_with_tool_call_parameters() -> None:
    payload = {
        "message": {
            "type": "tool-calls",
            "toolWithToolCallList": [
                {
                    "toolCall": {
                        "id": "tc_slots",
                        "function": {
                            "name": "search_slots",
                            "parameters": {"appointment_type": "follow_up"},
                        },
                    }
                }
            ],
        }
    }

    calls = normalize_tool_calls(payload)

    assert len(calls) == 1
    assert calls[0].tool_call_id == "tc_slots"
    assert calls[0].name == "search_slots"
    assert calls[0].arguments == {"appointment_type": "follow_up"}
