import httpx
import pytest

from app.models.vapi import NormalizedToolCall
from app.services.appointments import cancel_appointment, reschedule_appointment
from app.services.tool_dispatch import dispatch_tool_call


class CancellationEMRClient:
    def __init__(self) -> None:
        self.cancelled_id = None

    async def list_patients(self, **_filters):
        return [
            {
                "id": "pat_123",
                "first_name": "Maria",
                "last_name": "Santos",
                "date_of_birth": "1985-03-15",
                "phone": "+15551234001",
            }
        ]

    async def get_appointment(self, appointment_id):
        return {"id": appointment_id, "patient_id": "pat_123", "status": "scheduled"}

    async def cancel_appointment(self, appointment_id):
        self.cancelled_id = appointment_id
        return {"id": appointment_id, "patient_id": "pat_123", "status": "cancelled"}


@pytest.mark.asyncio
async def test_cancel_appointment_after_identity_and_confirmation() -> None:
    emr_client = CancellationEMRClient()

    result = await cancel_appointment(
        emr_client,
        patient_id="pat_123",
        verification_phone="+15551234001",
        date_of_birth="1985-03-15",
        appointment_id="apt_1",
        confirmed=True,
    )

    assert result["status"] == "cancelled"
    assert emr_client.cancelled_id == "apt_1"


@pytest.mark.asyncio
async def test_dispatch_cancel_appointment_returns_cancelled() -> None:
    tool_call = NormalizedToolCall(
        tool_call_id="tool_cancel",
        name="cancel_appointment",
        arguments={
            "patient_id": "pat_123",
            "verification_phone": "+15551234001",
            "date_of_birth": "1985-03-15",
            "appointment_id": "apt_1",
            "confirmed": True,
        },
        call_id="call_123",
        customer_number=None,
    )

    response = await dispatch_tool_call(tool_call, emr_client=CancellationEMRClient())

    assert '"status": "cancelled"' in response["result"]


class RescheduleEMRClient(CancellationEMRClient):
    def __init__(self) -> None:
        super().__init__()
        self.created_appointment = None

    async def create_appointment(self, appointment):
        self.created_appointment = appointment
        return {"id": "apt_new", "status": "scheduled", **appointment}


@pytest.mark.asyncio
async def test_reschedule_books_replacement_before_cancelling_original() -> None:
    emr_client = RescheduleEMRClient()

    result = await reschedule_appointment(
        emr_client,
        patient_id="pat_123",
        verification_phone="+15551234001",
        date_of_birth="1985-03-15",
        appointment_id="apt_1",
        new_provider_id="prov_martinez",
        new_start_time="2026-06-23T09:00:00Z",
        new_appointment_type=None,
        reason=None,
        confirmed=True,
    )

    assert result["status"] == "rescheduled"
    assert emr_client.created_appointment["appointment_type"] == "follow_up"
    assert emr_client.cancelled_id == "apt_1"


@pytest.mark.asyncio
async def test_dispatch_reschedule_returns_rescheduled() -> None:
    tool_call = NormalizedToolCall(
        tool_call_id="tool_reschedule",
        name="reschedule_appointment",
        arguments={
            "patient_id": "pat_123",
            "verification_phone": "+15551234001",
            "date_of_birth": "1985-03-15",
            "appointment_id": "apt_1",
            "new_provider_id": "prov_martinez",
            "new_start_time": "2026-06-23T09:00:00Z",
            "confirmed": True,
        },
        call_id="call_123",
        customer_number=None,
    )

    response = await dispatch_tool_call(tool_call, emr_client=RescheduleEMRClient())

    assert '"status": "rescheduled"' in response["result"]


class ConflictingRescheduleEMRClient(RescheduleEMRClient):
    async def create_appointment(self, appointment):
        request = httpx.Request("POST", "https://emr.test/appointments")
        response = httpx.Response(409, request=request)
        raise httpx.HTTPStatusError("slot conflict", request=request, response=response)


@pytest.mark.asyncio
async def test_reschedule_conflict_preserves_original_appointment() -> None:
    emr_client = ConflictingRescheduleEMRClient()

    result = await reschedule_appointment(
        emr_client,
        patient_id="pat_123",
        verification_phone="+15551234001",
        date_of_birth="1985-03-15",
        appointment_id="apt_1",
        new_provider_id="prov_martinez",
        new_start_time="2026-06-23T09:00:00Z",
        new_appointment_type=None,
        reason=None,
        confirmed=True,
    )

    assert result == {"status": "conflict"}
    assert emr_client.cancelled_id is None


class CompensationRescheduleEMRClient(RescheduleEMRClient):
    async def cancel_appointment(self, appointment_id):
        if appointment_id == "apt_1":
            raise RuntimeError("old cancellation failed")
        self.cancelled_id = appointment_id
        return {"id": appointment_id, "status": "cancelled"}


@pytest.mark.asyncio
async def test_reschedule_compensates_when_old_cancellation_fails() -> None:
    emr_client = CompensationRescheduleEMRClient()

    result = await reschedule_appointment(
        emr_client,
        patient_id="pat_123",
        verification_phone="+15551234001",
        date_of_birth="1985-03-15",
        appointment_id="apt_1",
        new_provider_id="prov_martinez",
        new_start_time="2026-06-23T09:00:00Z",
        new_appointment_type=None,
        reason=None,
        confirmed=True,
    )

    assert result == {"status": "reschedule_failed_original_preserved"}
    assert emr_client.cancelled_id == "apt_new"
