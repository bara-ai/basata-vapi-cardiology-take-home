from typing import Any

import httpx

from app.services.patients import find_verified_patient


async def cancel_appointment(
    emr_client: Any,
    *,
    patient_id: str,
    verification_phone: str,
    date_of_birth: str,
    appointment_id: str,
    confirmed: bool,
) -> dict[str, Any]:
    if not confirmed:
        return {"status": "invalid_arguments"}

    # Re-verify at the mutation boundary and confirm the appointment belongs to this patient.
    verification = await find_verified_patient(
        emr_client,
        phone=verification_phone,
        date_of_birth=date_of_birth,
    )
    if verification.get("status") != "verified" or verification["patient"]["id"] != patient_id:
        return {"status": "identity_verification_failed"}

    appointment = await emr_client.get_appointment(appointment_id)
    if appointment.get("patient_id") != patient_id:
        return {"status": "ownership_mismatch"}
    if appointment.get("status") == "cancelled":
        return {"status": "already_cancelled"}
    if appointment.get("status") != "scheduled":
        return {"status": "invalid_arguments"}

    cancelled_appointment = await emr_client.cancel_appointment(appointment_id)
    return {"status": "cancelled", "appointment": cancelled_appointment}


async def reschedule_appointment(
    emr_client: Any,
    *,
    patient_id: str,
    verification_phone: str,
    date_of_birth: str,
    appointment_id: str,
    new_provider_id: str,
    new_start_time: str,
    new_appointment_type: str | None,
    reason: str | None,
    confirmed: bool,
) -> dict[str, Any]:
    if not confirmed:
        return {"status": "invalid_arguments"}

    # Re-verify at the mutation boundary and confirm the appointment belongs to this patient.
    verification = await find_verified_patient(
        emr_client,
        phone=verification_phone,
        date_of_birth=date_of_birth,
    )
    if verification.get("status") != "verified" or verification["patient"]["id"] != patient_id:
        return {"status": "identity_verification_failed"}

    old_appointment = await emr_client.get_appointment(appointment_id)
    if old_appointment.get("patient_id") != patient_id:
        return {"status": "ownership_mismatch"}
    if old_appointment.get("status") != "scheduled":
        return {"status": "invalid_arguments"}

    # Book first so a failed replacement does not remove the caller's existing appointment.
    try:
        replacement = await emr_client.create_appointment(
            {
                "patient_id": patient_id,
                "provider_id": new_provider_id,
                "start_time": new_start_time,
                "appointment_type": new_appointment_type or old_appointment.get("appointment_type", "follow_up"),
                "reason": reason,
            }
        )
    except httpx.HTTPStatusError as error:
        if error.response.status_code == 409:
            return {"status": "conflict"}
        return {"status": "emr_unavailable"}

    try:
        await emr_client.cancel_appointment(appointment_id)
    except Exception:
        # Compensate by removing the replacement when the old appointment could not be cancelled.
        try:
            await emr_client.cancel_appointment(replacement["id"])
        except Exception:
            return {"status": "partial_failure_requires_human", "appointment": replacement}
        return {"status": "reschedule_failed_original_preserved"}

    return {"status": "rescheduled", "old_appointment_id": appointment_id, "appointment": replacement}
