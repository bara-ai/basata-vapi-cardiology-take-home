import json
from typing import Any

import httpx

from app.models.vapi import NormalizedToolCall
from app.services.appointments import cancel_appointment, reschedule_appointment
from app.services.patients import find_verified_patient, list_verified_appointments, register_patient
from app.services.scheduling import book_appointment, list_providers, search_slots


async def dispatch_tool_call(
    tool_call: NormalizedToolCall,
    *,
    emr_client: Any | None = None,
) -> dict[str, str]:
    try:
        return await _dispatch_tool_call(tool_call, emr_client=emr_client)
    except httpx.HTTPError:
        return {
            "name": tool_call.name,
            "toolCallId": tool_call.tool_call_id,
            "result": json.dumps({"status": "emr_unavailable"}),
        }


async def _dispatch_tool_call(
    tool_call: NormalizedToolCall,
    *,
    emr_client: Any | None = None,
) -> dict[str, str]:
    if tool_call.name == "find_patient":
        phone = tool_call.arguments.get("phone")
        date_of_birth = tool_call.arguments.get("date_of_birth")
        if not isinstance(phone, str) or not isinstance(date_of_birth, str):
            result: dict[str, Any] = {"status": "invalid_arguments"}
        elif emr_client is None:
            result = {"status": "emr_unavailable"}
        else:
            result = await find_verified_patient(
                emr_client,
                phone=phone,
                date_of_birth=date_of_birth,
            )
    elif tool_call.name == "register_patient":
        required_fields = ("first_name", "last_name", "date_of_birth", "phone")
        if emr_client is None:
            result = {"status": "emr_unavailable"}
        elif not all(isinstance(tool_call.arguments.get(field), str) for field in required_fields):
            result = {"status": "invalid_arguments"}
        else:
            patient = {
                **tool_call.arguments,
                "email": tool_call.arguments.get("email"),
                "insurance_provider": tool_call.arguments.get("insurance_provider"),
                "insurance_member_id": tool_call.arguments.get("insurance_member_id"),
            }
            result = await register_patient(emr_client, patient)
    elif tool_call.name == "list_providers":
        if emr_client is None:
            result = {"status": "emr_unavailable"}
        else:
            specialty = tool_call.arguments.get("specialty")
            appointment_type = tool_call.arguments.get("appointment_type")
            result = await list_providers(
                emr_client,
                specialty=specialty if isinstance(specialty, str) else None,
                appointment_type=appointment_type if isinstance(appointment_type, str) else None,
            )
    elif tool_call.name == "search_slots":
        patient_id = tool_call.arguments.get("patient_id")
        appointment_type = tool_call.arguments.get("appointment_type")
        if emr_client is None:
            result = {"status": "emr_unavailable"}
        elif not isinstance(patient_id, str) or not isinstance(appointment_type, str):
            result = {"status": "invalid_arguments"}
        else:
            provider_id = tool_call.arguments.get("provider_id")
            count = tool_call.arguments.get("number_of_slots_to_present", 3)
            result = await search_slots(
                emr_client,
                patient_id=patient_id,
                appointment_type=appointment_type,
                provider_id=provider_id if isinstance(provider_id, str) else None,
                start_date=tool_call.arguments.get("start_date"),
                end_date=tool_call.arguments.get("end_date"),
                start_time_of_day=tool_call.arguments.get("start_time_of_day"),
                end_time_of_day=tool_call.arguments.get("end_time_of_day"),
                days_of_week=tool_call.arguments.get("days_of_week"),
                earliest_available=tool_call.arguments.get("earliest_available"),
                number_of_slots_to_present=count if isinstance(count, int) else 3,
            )
    elif tool_call.name == "list_patient_appointments":
        patient_id = tool_call.arguments.get("patient_id")
        phone = tool_call.arguments.get("verification_phone")
        date_of_birth = tool_call.arguments.get("date_of_birth")
        if emr_client is None:
            result = {"status": "emr_unavailable"}
        elif not all(isinstance(value, str) for value in (patient_id, phone, date_of_birth)):
            result = {"status": "invalid_arguments"}
        else:
            result = await list_verified_appointments(
                emr_client,
                patient_id=patient_id,
                verification_phone=phone,
                date_of_birth=date_of_birth,
                include_cancelled=tool_call.arguments.get("include_cancelled") is True,
            )
    elif tool_call.name == "book_appointment":
        required_fields = (
            "patient_id",
            "verification_phone",
            "date_of_birth",
            "provider_id",
            "start_time",
            "appointment_type",
        )
        if emr_client is None:
            result = {"status": "emr_unavailable"}
        elif not all(isinstance(tool_call.arguments.get(field), str) for field in required_fields):
            result = {"status": "invalid_arguments"}
        else:
            result = await book_appointment(
                emr_client,
                patient_id=tool_call.arguments["patient_id"],
                verification_phone=tool_call.arguments["verification_phone"],
                date_of_birth=tool_call.arguments["date_of_birth"],
                provider_id=tool_call.arguments["provider_id"],
                start_time=tool_call.arguments["start_time"],
                appointment_type=tool_call.arguments["appointment_type"],
                reason=tool_call.arguments.get("reason"),
            )
    elif tool_call.name == "cancel_appointment":
        required_fields = ("patient_id", "verification_phone", "date_of_birth", "appointment_id")
        if emr_client is None:
            result = {"status": "emr_unavailable"}
        elif not all(isinstance(tool_call.arguments.get(field), str) for field in required_fields):
            result = {"status": "invalid_arguments"}
        elif tool_call.arguments.get("confirmed") is not True:
            result = {"status": "invalid_arguments"}
        else:
            result = await cancel_appointment(
                emr_client,
                patient_id=tool_call.arguments["patient_id"],
                verification_phone=tool_call.arguments["verification_phone"],
                date_of_birth=tool_call.arguments["date_of_birth"],
                appointment_id=tool_call.arguments["appointment_id"],
                confirmed=True,
            )
    elif tool_call.name == "reschedule_appointment":
        required_fields = (
            "patient_id",
            "verification_phone",
            "date_of_birth",
            "appointment_id",
            "new_provider_id",
            "new_start_time",
        )
        if emr_client is None:
            result = {"status": "emr_unavailable"}
        elif not all(isinstance(tool_call.arguments.get(field), str) for field in required_fields):
            result = {"status": "invalid_arguments"}
        elif tool_call.arguments.get("confirmed") is not True:
            result = {"status": "invalid_arguments"}
        else:
            new_type = tool_call.arguments.get("new_appointment_type")
            result = await reschedule_appointment(
                emr_client,
                patient_id=tool_call.arguments["patient_id"],
                verification_phone=tool_call.arguments["verification_phone"],
                date_of_birth=tool_call.arguments["date_of_birth"],
                appointment_id=tool_call.arguments["appointment_id"],
                new_provider_id=tool_call.arguments["new_provider_id"],
                new_start_time=tool_call.arguments["new_start_time"],
                new_appointment_type=new_type if isinstance(new_type, str) else None,
                reason=tool_call.arguments.get("reason"),
                confirmed=True,
            )
    else:
        result = {"status": "unsupported_tool", "tool": tool_call.name}

    return {
        "name": tool_call.name,
        "toolCallId": tool_call.tool_call_id,
        "result": json.dumps(result),
    }
