"""Run one collision-safe live EMR verification through the public Vapi webhook."""

import argparse
import asyncio
from datetime import UTC, datetime
import hashlib
import json
import os
from typing import Any
from uuid import uuid4

import httpx
from dotenv import load_dotenv


TEST_DOB = "1990-01-01"
TEST_APPOINTMENT_TYPE = "follow_up"


def make_run_id() -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}-{uuid4().hex[:8]}"


def build_test_identity(run_id: str) -> dict[str, str]:
    compact_run_id = "".join(character for character in run_id if character.isalnum()).upper()
    phone_suffix = int(hashlib.sha256(run_id.encode()).hexdigest(), 16) % 10_000_000
    return {
        "first_name": "Basata",
        "last_name": f"Sandbox{compact_run_id}",
        "date_of_birth": TEST_DOB,
        "phone": f"+1555{phone_suffix:07d}",
    }


def _tool_payload(*, run_id: str, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "message": {
            "type": "tool-calls",
            "call": {"id": f"live-{run_id}"},
            "toolCallList": [
                {
                    "id": f"{run_id}-{name}",
                    "function": {"name": name, "arguments": json.dumps(arguments)},
                }
            ],
        }
    }


async def _call_tool(
    client: httpx.AsyncClient,
    *,
    webhook_url: str,
    bearer_secret: str,
    run_id: str,
    name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    response = await client.post(
        webhook_url,
        headers={"Authorization": f"Bearer {bearer_secret}", "ngrok-skip-browser-warning": "1"},
        json=_tool_payload(run_id=run_id, name=name, arguments=arguments),
    )
    response.raise_for_status()
    result = response.json()["results"][0]
    if result["name"] != name:
        raise RuntimeError(f"Unexpected tool response for {name}")
    return json.loads(result["result"])


def _require_status(result: dict[str, Any], expected: str, tool_name: str) -> None:
    if result.get("status") != expected:
        raise RuntimeError(f"{tool_name} returned {result.get('status')!r}, expected {expected!r}")


async def run_live_verification(
    *,
    webhook_url: str,
    emr_base_url: str,
    bearer_secret: str,
    run_id: str | None = None,
) -> dict[str, str]:
    if not bearer_secret:
        raise ValueError("VAPI_WEBHOOK_SECRET is required")

    run_id = run_id or make_run_id()
    identity = build_test_identity(run_id)
    async with httpx.AsyncClient(timeout=20.0) as client:
        registration = await _call_tool(
            client,
            webhook_url=webhook_url,
            bearer_secret=bearer_secret,
            run_id=run_id,
            name="register_patient",
            arguments=identity,
        )
        _require_status(registration, "created", "register_patient")
        patient_id = registration["patient"]["id"]

        verification = await _call_tool(
            client,
            webhook_url=webhook_url,
            bearer_secret=bearer_secret,
            run_id=run_id,
            name="find_patient",
            arguments={"phone": identity["phone"], "date_of_birth": identity["date_of_birth"]},
        )
        _require_status(verification, "verified", "find_patient")
        if verification["patient"]["id"] != patient_id:
            raise RuntimeError("find_patient returned a different patient")

        providers = await _call_tool(
            client,
            webhook_url=webhook_url,
            bearer_secret=bearer_secret,
            run_id=run_id,
            name="list_providers",
            arguments={"appointment_type": TEST_APPOINTMENT_TYPE},
        )
        _require_status(providers, "ok", "list_providers")

        slots = await _call_tool(
            client,
            webhook_url=webhook_url,
            bearer_secret=bearer_secret,
            run_id=run_id,
            name="search_slots",
            arguments={
                "patient_id": patient_id,
                "appointment_type": TEST_APPOINTMENT_TYPE,
                "number_of_slots_to_present": 1,
            },
        )
        _require_status(slots, "ok", "search_slots")
        slot = slots["slots"][0]

        booking = await _call_tool(
            client,
            webhook_url=webhook_url,
            bearer_secret=bearer_secret,
            run_id=run_id,
            name="book_appointment",
            arguments={
                "patient_id": patient_id,
                "verification_phone": identity["phone"],
                "date_of_birth": identity["date_of_birth"],
                "provider_id": slot["provider_id"],
                "start_time": slot["start_time"],
                "appointment_type": TEST_APPOINTMENT_TYPE,
                "reason": f"Basata sandbox verification {run_id}",
            },
        )
        _require_status(booking, "booked", "book_appointment")
        appointment_id = booking["appointment"]["id"]

        appointment_response = await client.get(
            f"{emr_base_url.rstrip('/')}/appointments/{appointment_id}",
            headers={"ngrok-skip-browser-warning": "1"},
        )
        appointment_response.raise_for_status()
        appointment = appointment_response.json()
        if appointment.get("patient_id") != patient_id or appointment.get("status") != "scheduled":
            raise RuntimeError("Direct EMR appointment verification failed")

    return {
        "run_id": run_id,
        "patient_id": patient_id,
        "appointment_id": appointment_id,
        "appointment_status": appointment["status"],
    }


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--webhook-url", default=os.environ.get("VAPI_WEBHOOK_URL"))
    parser.add_argument("--emr-base-url", default=os.environ.get("EMR_BASE_URL"))
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()

    if not args.webhook_url or not args.emr_base_url:
        parser.error("VAPI_WEBHOOK_URL and EMR_BASE_URL are required")

    result = asyncio.run(
        run_live_verification(
            webhook_url=args.webhook_url,
            emr_base_url=args.emr_base_url,
            bearer_secret=os.environ.get("VAPI_WEBHOOK_SECRET", ""),
            run_id=args.run_id,
        )
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
