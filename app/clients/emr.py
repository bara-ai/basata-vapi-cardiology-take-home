from typing import Any, Protocol

import httpx


class EMRClientProtocol(Protocol):
    async def list_patients(
        self,
        *,
        phone: str | None = None,
        last_name: str | None = None,
        date_of_birth: str | None = None,
    ) -> list[dict[str, Any]]: ...

    async def create_patient(self, patient: dict[str, Any]) -> dict[str, Any]: ...

    async def list_providers(self) -> list[dict[str, Any]]: ...

    async def search_slots(self, **filters: Any) -> list[dict[str, Any]]: ...

    async def list_appointments(self, *, patient_id: str) -> list[dict[str, Any]]: ...

    async def create_appointment(self, appointment: dict[str, Any]) -> dict[str, Any]: ...

    async def get_appointment(self, appointment_id: str) -> dict[str, Any]: ...

    async def cancel_appointment(self, appointment_id: str) -> dict[str, Any]: ...


class EMRClient:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def list_patients(
        self,
        *,
        phone: str | None = None,
        last_name: str | None = None,
        date_of_birth: str | None = None,
    ) -> list[dict[str, Any]]:
        params = {
            key: value
            for key, value in {
                "phone": phone,
                "last_name": last_name,
                "date_of_birth": date_of_birth,
            }.items()
            if value is not None
        }
        if not params:
            raise ValueError("Patient search requires a phone or name-and-date-of-birth filter")

        response = await self._client.get("/patients", params=params)
        response.raise_for_status()
        return response.json()

    async def create_patient(self, patient: dict[str, Any]) -> dict[str, Any]:
        response = await self._client.post("/patients", json=patient)
        response.raise_for_status()
        return response.json()

    async def get_patient(self, patient_id: str) -> dict[str, Any]:
        response = await self._client.get(f"/patients/{patient_id}")
        response.raise_for_status()
        return response.json()

    async def list_providers(self) -> list[dict[str, Any]]:
        response = await self._client.get("/providers")
        response.raise_for_status()
        return response.json()

    async def get_provider(self, provider_id: str) -> dict[str, Any]:
        response = await self._client.get(f"/providers/{provider_id}")
        response.raise_for_status()
        return response.json()

    async def list_slots(self) -> list[dict[str, Any]]:
        response = await self._client.get("/slots")
        response.raise_for_status()
        return response.json()

    async def search_slots(self, **filters: Any) -> list[dict[str, Any]]:
        params = {key: value for key, value in filters.items() if value is not None}
        response = await self._client.get("/slots", params=params)
        response.raise_for_status()
        return response.json()

    async def list_appointments(self, *, patient_id: str) -> list[dict[str, Any]]:
        response = await self._client.get("/appointments", params={"patient_id": patient_id})
        response.raise_for_status()
        return response.json()

    async def create_appointment(self, appointment: dict[str, Any]) -> dict[str, Any]:
        response = await self._client.post("/appointments", json=appointment)
        response.raise_for_status()
        return response.json()

    async def get_appointment(self, appointment_id: str) -> dict[str, Any]:
        response = await self._client.get(f"/appointments/{appointment_id}")
        response.raise_for_status()
        return response.json()

    async def cancel_appointment(self, appointment_id: str) -> dict[str, Any]:
        response = await self._client.delete(f"/appointments/{appointment_id}")
        response.raise_for_status()
        return response.json()
