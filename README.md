# Basata Voice AI Take-Home

FastAPI backend and Vapi configuration for a Heartland Cardiology scheduling agent backed by the CardioChart Pro sandbox.

## Supported Workflows

- Register a new patient.
- Verify an existing patient with phone number and date of birth.
- Find providers and appointment availability.
- Book, cancel, and reschedule appointments.

The EMR is the source of truth for patients, providers, slots, and appointment status.

## Run Locally

```powershell
Copy-Item .env.example .env
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

Run the tests with:

```powershell
python -m pytest -q
```

## Quality Checks

Run these checks before pushing changes:

```powershell
ruff check app tests
ruff format --check app tests
mypy app
python -m pytest -q
```

Expose the service for Vapi:

```powershell
ngrok http 8000
```

Set each Vapi tool server URL to `https://YOUR-NGROK-DOMAIN/vapi/webhook`.

## Vapi Assistant

[Heartland Cardiology](https://dashboard.vapi.ai/assistants/9ca91034-3de4-44be-bba6-5aa756128d64?tab=assistant) has eight function tools for the supported workflows. The assigned phone number is `+1 601 419 9125`.

The assistant prompt is in [`vapi/system-prompt.md`](vapi/system-prompt.md), and the tool definitions are in [`vapi/assistant.tools.json`](vapi/assistant.tools.json).

## Verification

- `48` automated tests pass.
- Live webhook verification completed against the EMR sandbox for registration, provider and slot lookup, booking, rescheduling, and cancellation.
- Rescheduling keeps the original appointment type unless a replacement type is provided.

## Remaining Dependency

Native call transfer is not configured because a front-desk E.164 number and operating hours were not provided. The assistant requests staff assistance without claiming a transfer occurred.
