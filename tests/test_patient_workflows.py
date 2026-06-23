import json

import httpx
import pytest

from app.models.vapi import NormalizedToolCall
from app.services.patients import find_verified_patient, list_verified_appointments
from app.services.tool_dispatch import dispatch_tool_call


class FakeEMRClient:
    async def list_patients(self, **_filters):
        return [
            {
                "id": "pat_123",
                "first_name": "Maria",
                "last_name": "Santos",
                "date_of_birth": "1985-03-15",
                "phone": "+1 (555) 123-4001",
            }
        ]


@pytest.mark.asyncio
async def test_find_verified_patient_matches_normalized_phone_and_dob() -> None:
    result = await find_verified_patient(
        FakeEMRClient(),
        phone="+15551234001",
        date_of_birth="1985-03-15",
    )

    assert result == {
        "status": "verified",
        "patient": {"id": "pat_123", "first_name": "Maria", "last_name": "Santos"},
    }


@pytest.mark.asyncio
async def test_dispatch_find_patient_returns_verified_result() -> None:
    tool_call = NormalizedToolCall(
        tool_call_id="tool_find",
        name="find_patient",
        arguments={"phone": "+15551234001", "date_of_birth": "1985-03-15"},
        call_id="call_123",
        customer_number="+15551234001",
    )

    response = await dispatch_tool_call(tool_call, emr_client=FakeEMRClient())

    assert response["toolCallId"] == "tool_find"
    assert json.loads(response["result"])["status"] == "verified"


class RegisteringEMRClient(FakeEMRClient):
    def __init__(self) -> None:
        self.created_patient = None

    async def create_patient(self, patient):
        self.created_patient = patient
        return {"id": "pat_new", **patient}


@pytest.mark.asyncio
async def test_register_patient_creates_new_record_after_duplicate_check() -> None:
    from app.services.patients import register_patient

    emr_client = RegisteringEMRClient()
    result = await register_patient(
        emr_client,
        {
            "first_name": "Ava",
            "last_name": "Jones",
            "date_of_birth": "1990-01-02",
            "phone": "+15551234567",
            "email": None,
            "insurance_provider": None,
            "insurance_member_id": None,
        },
    )

    assert result["status"] == "created"
    assert result["patient"]["id"] == "pat_new"
    assert emr_client.created_patient["phone"] == "+15551234567"


@pytest.mark.asyncio
async def test_dispatch_register_patient_returns_created_result() -> None:
    tool_call = NormalizedToolCall(
        tool_call_id="tool_register",
        name="register_patient",
        arguments={
            "first_name": "Ava",
            "last_name": "Jones",
            "date_of_birth": "1990-01-02",
            "phone": "+15551234567",
        },
        call_id="call_123",
        customer_number="+15551234567",
    )

    response = await dispatch_tool_call(tool_call, emr_client=RegisteringEMRClient())

    assert json.loads(response["result"])["status"] == "created"


class AppointmentEMRClient(FakeEMRClient):
    appointments_queried = False

    async def list_appointments(self, *, patient_id):
        self.appointments_queried = True
        return [{"id": "apt_1", "patient_id": patient_id, "status": "scheduled"}]

    async def list_providers(self):
        return [{"id": "prov_martinez", "name": "Dr. Sofia Martinez, MD"}]


@pytest.mark.asyncio
async def test_list_verified_appointments_rejects_wrong_dob_before_lookup() -> None:
    emr_client = AppointmentEMRClient()

    result = await list_verified_appointments(
        emr_client,
        patient_id="pat_123",
        verification_phone="+15551234001",
        date_of_birth="1999-01-01",
    )

    assert result == {"status": "identity_verification_failed"}
    assert emr_client.appointments_queried is False


@pytest.mark.asyncio
async def test_dispatch_list_patient_appointments_requires_verified_identity() -> None:
    tool_call = NormalizedToolCall(
        tool_call_id="tool_appointments",
        name="list_patient_appointments",
        arguments={
            "patient_id": "pat_123",
            "verification_phone": "+15551234001",
            "date_of_birth": "1985-03-15",
        },
        call_id="call_123",
        customer_number=None,
    )

    response = await dispatch_tool_call(tool_call, emr_client=AppointmentEMRClient())

    appointment = json.loads(response["result"])["appointments"][0]
    assert appointment["id"] == "apt_1"
    assert appointment["provider_name"] is None


@pytest.mark.asyncio
async def test_list_verified_appointments_includes_cancelled_only_when_requested() -> None:
    class HistoryEMRClient(AppointmentEMRClient):
        async def list_appointments(self, *, patient_id):
            return [
                {"id": "apt_scheduled", "patient_id": patient_id, "status": "scheduled"},
                {"id": "apt_cancelled", "patient_id": patient_id, "status": "cancelled"},
            ]

    result = await list_verified_appointments(
        HistoryEMRClient(),
        patient_id="pat_123",
        verification_phone="+15551234001",
        date_of_birth="1985-03-15",
        include_cancelled=True,
    )

    assert [appointment["id"] for appointment in result["appointments"]] == [
        "apt_scheduled",
        "apt_cancelled",
    ]


class UnavailableEMRClient:
    async def list_patients(self, **_filters):
        raise httpx.ConnectError("sandbox unavailable")


@pytest.mark.asyncio
async def test_dispatch_maps_emr_connection_failure_to_safe_status() -> None:
    tool_call = NormalizedToolCall(
        tool_call_id="tool_unavailable",
        name="find_patient",
        arguments={"phone": "+15551234001", "date_of_birth": "1985-03-15"},
        call_id="call_123",
        customer_number=None,
    )

    response = await dispatch_tool_call(tool_call, emr_client=UnavailableEMRClient())

    assert json.loads(response["result"]) == {"status": "emr_unavailable"}
