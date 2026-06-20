from datetime import date, timedelta
from typing import Any

import httpx

from app.services.patients import find_verified_patient


def _provider_result(provider: dict[str, Any]) -> dict[str, Any]:
    result = {
        "id": provider["id"],
        "name": provider.get("name")
        or f"{provider.get('first_name', '')} {provider.get('last_name', '')}, {provider.get('title', '')}".strip(
            ", "
        ),
        "specialties": provider.get("specialties", []),
        "appointment_types": provider.get("supported_appointment_types", provider.get("appointment_types", [])),
    }
    if provider.get("restrictions") is not None:
        result["restrictions"] = provider["restrictions"]
    return result


def _provider_name(provider: dict[str, Any]) -> str:
    return provider.get("name") or f"{provider.get('first_name', '')} {provider.get('last_name', '')}, {provider.get('title', '')}".strip(
        ", "
    )


async def list_providers(
    emr_client: Any,
    *,
    specialty: str | None = None,
    appointment_type: str | None = None,
) -> dict[str, Any]:
    providers = await emr_client.list_providers()
    if specialty:
        providers = [provider for provider in providers if specialty in provider.get("specialties", [])]
    if appointment_type:
        providers = [
            provider
            for provider in providers
            if appointment_type
            in provider.get("supported_appointment_types", provider.get("appointment_types", []))
        ]

    return {
        "status": "ok",
        "providers": [_provider_result(provider) for provider in providers],
    }


async def search_slots(
    emr_client: Any,
    *,
    patient_id: str,
    appointment_type: str,
    provider_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    start_time_of_day: str | None = None,
    end_time_of_day: str | None = None,
    days_of_week: str | None = None,
    earliest_available: bool | None = None,
    number_of_slots_to_present: int = 3,
) -> dict[str, Any]:
    limit = max(1, min(number_of_slots_to_present, 5))
    start_date = start_date or date.today().isoformat()
    end_date = end_date or (date.today() + timedelta(days=14)).isoformat()
    slots = await emr_client.search_slots(
        patient_id=patient_id,
        appointment_type=appointment_type,
        provider_id=provider_id,
        start_date=start_date,
        end_date=end_date,
        start_time_of_day=start_time_of_day,
        end_time_of_day=end_time_of_day,
        days_of_week=days_of_week,
        earliest_available=earliest_available,
        number_of_slots_to_present=limit,
    )
    bounded_slots = slots[:limit]
    if not bounded_slots:
        return {"status": "no_slots", "slots": []}

    provider_names = {
        provider["id"]: _provider_name(provider)
        for provider in await emr_client.list_providers()
    }
    return {
        "status": "ok",
        "slots": [
            {**slot, "provider_name": provider_names.get(slot.get("provider_id"))}
            for slot in bounded_slots
        ],
    }


async def book_appointment(
    emr_client: Any,
    *,
    patient_id: str,
    verification_phone: str,
    date_of_birth: str,
    provider_id: str,
    start_time: str,
    appointment_type: str,
    reason: str | None = None,
) -> dict[str, Any]:
    verification = await find_verified_patient(
        emr_client,
        phone=verification_phone,
        date_of_birth=date_of_birth,
    )
    if verification.get("status") != "verified" or verification["patient"]["id"] != patient_id:
        return {"status": "identity_verification_failed"}

    try:
        appointment = await emr_client.create_appointment(
            {
                "patient_id": patient_id,
                "provider_id": provider_id,
                "start_time": start_time,
                "appointment_type": appointment_type,
                "reason": reason,
            }
        )
    except httpx.HTTPStatusError as error:
        if error.response.status_code == 409:
            return {"status": "conflict"}
        raise

    return {"status": "booked", "appointment": appointment}
