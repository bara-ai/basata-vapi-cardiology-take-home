import httpx
import pytest
import respx

from app.clients.emr import EMRClient


@pytest.mark.asyncio
async def test_list_patients_passes_phone_search_filter() -> None:
    async with httpx.AsyncClient(base_url="https://emr.test") as http_client:
        client = EMRClient(http_client)
        with respx.mock(base_url="https://emr.test") as router:
            route = router.get("/patients", params={"phone": "+15551234001"}).mock(
                return_value=httpx.Response(
                    200,
                    json=[
                        {
                            "id": "pat_123",
                            "first_name": "Maria",
                            "last_name": "Santos",
                            "date_of_birth": "1985-03-15",
                            "phone": "+15551234001",
                        }
                    ],
                )
            )

            patients = await client.list_patients(phone="+15551234001")

    assert route.called
    assert patients[0]["id"] == "pat_123"


@pytest.mark.asyncio
async def test_list_providers_reads_emr_collection() -> None:
    async with httpx.AsyncClient(base_url="https://emr.test") as http_client:
        client = EMRClient(http_client)
        with respx.mock(base_url="https://emr.test") as router:
            route = router.get("/providers").mock(
                return_value=httpx.Response(200, json=[{"id": "prov_martinez"}])
            )

            providers = await client.list_providers()

    assert route.called
    assert providers == [{"id": "prov_martinez"}]


@pytest.mark.asyncio
async def test_list_slots_reads_emr_collection() -> None:
    async with httpx.AsyncClient(base_url="https://emr.test") as http_client:
        client = EMRClient(http_client)
        with respx.mock(base_url="https://emr.test") as router:
            route = router.get("/slots").mock(return_value=httpx.Response(200, json=[{"id": "slot_1"}]))

            slots = await client.list_slots()

    assert route.called
    assert slots == [{"id": "slot_1"}]


@pytest.mark.asyncio
async def test_search_slots_passes_required_and_optional_filters() -> None:
    params = {
        "patient_id": "pat_123",
        "appointment_type": "follow_up",
        "provider_id": "prov_martinez",
        "start_date": "2026-06-22",
        "number_of_slots_to_present": "3",
    }
    async with httpx.AsyncClient(base_url="https://emr.test") as http_client:
        client = EMRClient(http_client)
        with respx.mock(base_url="https://emr.test") as router:
            route = router.get("/slots", params=params).mock(
                return_value=httpx.Response(200, json=[{"provider_id": "prov_martinez"}])
            )

            slots = await client.search_slots(
                patient_id="pat_123",
                appointment_type="follow_up",
                provider_id="prov_martinez",
                start_date="2026-06-22",
                number_of_slots_to_present=3,
            )

    assert route.called
    assert slots == [{"provider_id": "prov_martinez"}]


@pytest.mark.asyncio
async def test_list_appointments_passes_patient_filter() -> None:
    async with httpx.AsyncClient(base_url="https://emr.test") as http_client:
        client = EMRClient(http_client)
        with respx.mock(base_url="https://emr.test") as router:
            route = router.get("/appointments", params={"patient_id": "pat_123"}).mock(
                return_value=httpx.Response(200, json=[{"id": "apt_1"}])
            )

            appointments = await client.list_appointments(patient_id="pat_123")

    assert route.called
    assert appointments == [{"id": "apt_1"}]


@pytest.mark.asyncio
async def test_get_patient_and_provider_use_item_endpoints() -> None:
    async with httpx.AsyncClient(base_url="https://emr.test") as http_client:
        client = EMRClient(http_client)
        with respx.mock(base_url="https://emr.test") as router:
            patient_route = router.get("/patients/pat_123").mock(
                return_value=httpx.Response(200, json={"id": "pat_123"})
            )
            provider_route = router.get("/providers/prov_martinez").mock(
                return_value=httpx.Response(200, json={"id": "prov_martinez"})
            )

            patient = await client.get_patient("pat_123")
            provider = await client.get_provider("prov_martinez")

    assert patient_route.called and provider_route.called
    assert patient == {"id": "pat_123"}
    assert provider == {"id": "prov_martinez"}


@pytest.mark.asyncio
async def test_create_appointment_posts_emr_payload() -> None:
    appointment = {"patient_id": "pat_123", "provider_id": "prov_martinez", "start_time": "2026-06-22T09:00:00Z"}
    async with httpx.AsyncClient(base_url="https://emr.test") as http_client:
        client = EMRClient(http_client)
        with respx.mock(base_url="https://emr.test") as router:
            route = router.post("/appointments", json=appointment).mock(
                return_value=httpx.Response(201, json={"id": "apt_1", **appointment})
            )

            created = await client.create_appointment(appointment)

    assert route.called
    assert created["id"] == "apt_1"


@pytest.mark.asyncio
async def test_get_and_cancel_appointment_use_item_endpoint() -> None:
    async with httpx.AsyncClient(base_url="https://emr.test") as http_client:
        client = EMRClient(http_client)
        with respx.mock(base_url="https://emr.test") as router:
            get_route = router.get("/appointments/apt_1").mock(
                return_value=httpx.Response(200, json={"id": "apt_1", "status": "scheduled"})
            )
            delete_route = router.delete("/appointments/apt_1").mock(
                return_value=httpx.Response(200, json={"id": "apt_1", "status": "cancelled"})
            )

            appointment = await client.get_appointment("apt_1")
            cancelled = await client.cancel_appointment("apt_1")

    assert get_route.called and delete_route.called
    assert appointment["status"] == "scheduled"
    assert cancelled["status"] == "cancelled"
