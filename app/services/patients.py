from typing import Any

from app.clients.emr import EMRClientProtocol


def _phone_digits(phone: str) -> str:
    return "".join(character for character in phone if character.isdigit())


async def find_verified_patient(
    emr_client: EMRClientProtocol,
    *,
    phone: str,
    date_of_birth: str,
) -> dict[str, Any]:
    for patient in await emr_client.list_patients(phone=phone):
        if (
            _phone_digits(patient["phone"]) == _phone_digits(phone)
            and patient["date_of_birth"] == date_of_birth
        ):
            return {
                "status": "verified",
                "patient": {
                    "id": patient["id"],
                    "first_name": patient["first_name"],
                    "last_name": patient["last_name"],
                },
            }

    return {"status": "not_found"}


async def register_patient(
    emr_client: EMRClientProtocol, patient: dict[str, Any]
) -> dict[str, Any]:
    phone = patient["phone"]
    for existing_patient in await emr_client.list_patients(phone=phone):
        if _phone_digits(existing_patient["phone"]) == _phone_digits(phone):
            return {"status": "duplicate_phone"}

    created_patient = await emr_client.create_patient(patient)
    return {"status": "created", "patient": created_patient}


async def list_verified_appointments(
    emr_client: EMRClientProtocol,
    *,
    patient_id: str,
    verification_phone: str,
    date_of_birth: str,
    include_cancelled: bool = False,
) -> dict[str, Any]:
    # Re-verify before disclosure because a patient ID alone is not caller authentication.
    verification = await find_verified_patient(
        emr_client,
        phone=verification_phone,
        date_of_birth=date_of_birth,
    )
    if verification.get("status") != "verified" or verification["patient"]["id"] != patient_id:
        return {"status": "identity_verification_failed"}

    appointments = await emr_client.list_appointments(patient_id=patient_id)
    provider_names = {
        provider["id"]: provider.get("name")
        or f"{provider.get('first_name', '')} {provider.get('last_name', '')}, {provider.get('title', '')}".strip(
            ", "
        )
        for provider in await emr_client.list_providers()
    }
    return {
        "status": "ok",
        "appointments": [
            {**appointment, "provider_name": provider_names.get(appointment.get("provider_id"))}
            for appointment in appointments
            if include_cancelled or appointment.get("status") != "cancelled"
        ],
    }
