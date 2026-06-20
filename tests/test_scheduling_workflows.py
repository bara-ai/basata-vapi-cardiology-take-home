from datetime import date, timedelta
import httpx
import json

import pytest

from app.models.vapi import NormalizedToolCall
from app.services.scheduling import list_providers, search_slots
from app.services.tool_dispatch import dispatch_tool_call


class ProviderEMRClient:
    async def list_providers(self):
        return [
            {
                "id": "prov_martinez",
                "name": "Dr. Sofia Martinez, MD",
                "specialties": ["general_cardiology", "interventional_cardiology"],
                "appointment_types": ["new_patient", "follow_up", "procedure_consult"],
            },
            {
                "id": "prov_patel",
                "name": "Dr. Raj Patel, MD",
                "specialties": ["general_cardiology"],
                "appointment_types": ["new_patient", "follow_up"],
            },
        ]


@pytest.mark.asyncio
async def test_list_providers_filters_by_specialty() -> None:
    result = await list_providers(ProviderEMRClient(), specialty="interventional_cardiology")

    assert result == {
        "status": "ok",
        "providers": [
            {
                "id": "prov_martinez",
                "name": "Dr. Sofia Martinez, MD",
                "specialties": ["general_cardiology", "interventional_cardiology"],
                "appointment_types": ["new_patient", "follow_up", "procedure_consult"],
            }
        ],
    }


@pytest.mark.asyncio
async def test_list_providers_supports_emr_provider_schema() -> None:
    class ActualProviderEMRClient:
        async def list_providers(self):
            return [
                {
                    "id": "prov_martinez",
                    "first_name": "Sofia",
                    "last_name": "Martinez",
                    "title": "MD",
                    "specialties": ["interventional_cardiology"],
                    "supported_appointment_types": ["procedure_consult"],
                    "restrictions": "Tuesday and Thursday only",
                }
            ]

    result = await list_providers(ActualProviderEMRClient())

    assert result["providers"] == [
        {
            "id": "prov_martinez",
            "name": "Sofia Martinez, MD",
            "specialties": ["interventional_cardiology"],
            "appointment_types": ["procedure_consult"],
            "restrictions": "Tuesday and Thursday only",
        }
    ]


@pytest.mark.asyncio
async def test_list_providers_filters_by_appointment_type() -> None:
    result = await list_providers(ProviderEMRClient(), appointment_type="procedure_consult")

    assert [provider["id"] for provider in result["providers"]] == ["prov_martinez"]


@pytest.mark.asyncio
async def test_dispatch_list_providers_returns_filtered_result() -> None:
    tool_call = NormalizedToolCall(
        tool_call_id="tool_providers",
        name="list_providers",
        arguments={"specialty": "interventional_cardiology"},
        call_id="call_123",
        customer_number=None,
    )

    response = await dispatch_tool_call(tool_call, emr_client=ProviderEMRClient())

    assert json.loads(response["result"])["providers"][0]["id"] == "prov_martinez"


class SlotEMRClient:
    def __init__(self) -> None:
        self.filters = None

    async def list_providers(self):
        return [
            {"id": "prov_martinez", "name": "Dr. Sofia Martinez, MD"},
            {"id": "prov_patel", "name": "Dr. Raj Patel, MD"},
        ]

    async def search_slots(self, **filters):
        self.filters = filters
        return [
            {
                "id": "slot_1",
                "provider_id": "prov_martinez",
                "start_time": "2026-06-22T09:00:00Z",
                "appointment_type": "follow_up",
            },
            {
                "id": "slot_2",
                "provider_id": "prov_patel",
                "start_time": "2026-06-22T10:00:00Z",
                "appointment_type": "new_patient",
            },
        ]


@pytest.mark.asyncio
async def test_search_slots_filters_and_limits_results() -> None:
    emr_client = SlotEMRClient()
    result = await search_slots(
        emr_client,
        patient_id="pat_123",
        appointment_type="follow_up",
        provider_id="prov_martinez",
        number_of_slots_to_present=1,
    )

    assert result == {
        "status": "ok",
        "slots": [
            {
                "id": "slot_1",
                "provider_id": "prov_martinez",
                "provider_name": "Dr. Sofia Martinez, MD",
                "start_time": "2026-06-22T09:00:00Z",
                "appointment_type": "follow_up",
            }
        ],
    }
    assert emr_client.filters["start_date"] == date.today().isoformat()
    assert emr_client.filters["end_date"] == (date.today() + timedelta(days=14)).isoformat()


@pytest.mark.asyncio
async def test_search_slots_supports_emr_slot_schema() -> None:
    class ActualSlotEMRClient:
        async def list_providers(self):
            return [{"id": "prov_martinez", "name": "Dr. Sofia Martinez, MD"}]

        async def search_slots(self, **filters):
            return [
                {
                    "provider_id": "prov_martinez",
                    "start_time": "2026-06-22T09:00:00Z",
                    "end_time": "2026-06-22T09:30:00Z",
                    "supported_appointment_types": ["new_patient", "follow_up"],
                    "is_telehealth": False,
                }
            ]

    result = await search_slots(ActualSlotEMRClient(), patient_id="pat_123", appointment_type="follow_up")

    assert result["status"] == "ok"
    assert result["slots"][0]["supported_appointment_types"] == ["new_patient", "follow_up"]
    assert result["slots"][0]["provider_name"] == "Dr. Sofia Martinez, MD"


@pytest.mark.asyncio
async def test_dispatch_search_slots_returns_matching_slots() -> None:
    tool_call = NormalizedToolCall(
        tool_call_id="tool_slots",
        name="search_slots",
        arguments={"patient_id": "pat_123", "appointment_type": "follow_up", "provider_id": "prov_martinez"},
        call_id="call_123",
        customer_number=None,
    )

    response = await dispatch_tool_call(tool_call, emr_client=SlotEMRClient())

    assert json.loads(response["result"])["slots"][0]["id"] == "slot_1"


class BookingEMRClient:
    def __init__(self) -> None:
        self.created_appointment = None

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

    async def create_appointment(self, appointment):
        self.created_appointment = appointment
        return {"id": "apt_1", "status": "scheduled", **appointment}


@pytest.mark.asyncio
async def test_dispatch_book_appointment_requires_verified_identity() -> None:
    tool_call = NormalizedToolCall(
        tool_call_id="tool_book",
        name="book_appointment",
        arguments={
            "patient_id": "pat_123",
            "verification_phone": "+15551234001",
            "date_of_birth": "1985-03-15",
            "provider_id": "prov_martinez",
            "start_time": "2026-06-22T09:00:00Z",
            "appointment_type": "follow_up",
            "reason": "Routine follow-up",
        },
        call_id="call_123",
        customer_number=None,
    )
    emr_client = BookingEMRClient()

    response = await dispatch_tool_call(tool_call, emr_client=emr_client)

    assert json.loads(response["result"])["status"] == "booked"
    assert emr_client.created_appointment["patient_id"] == "pat_123"


class ConflictingBookingEMRClient(BookingEMRClient):
    async def create_appointment(self, appointment):
        request = httpx.Request("POST", "https://emr.test/appointments")
        response = httpx.Response(409, request=request)
        raise httpx.HTTPStatusError("slot conflict", request=request, response=response)


@pytest.mark.asyncio
async def test_dispatch_book_appointment_maps_slot_conflict() -> None:
    tool_call = NormalizedToolCall(
        tool_call_id="tool_book_conflict",
        name="book_appointment",
        arguments={
            "patient_id": "pat_123",
            "verification_phone": "+15551234001",
            "date_of_birth": "1985-03-15",
            "provider_id": "prov_martinez",
            "start_time": "2026-06-22T09:00:00Z",
            "appointment_type": "follow_up",
        },
        call_id="call_123",
        customer_number=None,
    )

    response = await dispatch_tool_call(tool_call, emr_client=ConflictingBookingEMRClient())

    assert json.loads(response["result"]) == {"status": "conflict"}
