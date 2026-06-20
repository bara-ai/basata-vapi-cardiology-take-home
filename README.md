# Basata Voice AI Take-Home

FastAPI webhook backend for a Vapi cardiology scheduling agent. The CardioChart Pro sandbox remains the source of truth.

## Implemented Workflows

- New-patient registration with duplicate-phone protection.
- Existing-patient verification using registered phone plus DOB.
- Provider listing and slot search.
- Protected appointment lookup, booking, cancellation, and book-first rescheduling.
- Vapi tool-call payload compatibility, Bearer authentication, idempotent mutation retries, and safe EMR-unavailable results.
- A 15-minute in-memory idempotency TTL for the demo; production should use Redis or Postgres.

## Run Locally

```powershell
Copy-Item .env.example .env
$env:VAPI_WEBHOOK_SECRET = "replace-with-a-random-secret"
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
python -m pytest -q
```

Expose the local server for Vapi with:

```powershell
ngrok config add-authtoken YOUR_NGROK_AUTHTOKEN
ngrok http 8000
```

ngrok was installed locally through Winget. Open a new terminal before using the `ngrok` command so its updated PATH entry is loaded.

Set each Vapi tool server URL to `https://YOUR-NGROK-DOMAIN/vapi/webhook`.

Run a collision-safe live sandbox verification with:

```powershell
$env:VAPI_WEBHOOK_URL = "https://YOUR-NGROK-DOMAIN/vapi/webhook"
python -m scripts.live_emr_verification
```

Each invocation generates a synthetic `Basata Sandbox...` patient and a reserved `+1555...` number. It leaves its patient and scheduled appointment in the shared sandbox and records only non-PII IDs in `LIVE_TEST_NOTES.md`.

## Vapi Setup

The Vapi assistant is configured in the Interview Sandbox: [Heartland Cardiology](https://dashboard.vapi.ai/assistants/9ca91034-3de4-44be-bba6-5aa756128d64?tab=assistant).

Vapi Custom Credential `Basata Vapi Webhook Bearer` is configured with Bearer Token authentication, header `Authorization`, and Bearer prefix enabled. It uses the same value as `VAPI_WEBHOOK_SECRET`. The credential is attached to all eight custom tool server configurations. The old static `Authorization` headers were removed. The `ngrok-skip-browser-warning: 1` header stays because it is needed for the ngrok free tunnel.

The Vapi phone number `+1 601 419 9125` is assigned to this assistant. Request-start filler messages are configured on the eight tools.

Use [`vapi/system-prompt.md`](vapi/system-prompt.md) as the assistant system prompt.

Native `transferCall` is intentionally deferred: no real front-desk number or operating hours are available. The assistant must use the `human_handoff_required` fallback instead.

## Safety Notes

- Do not commit `.env` or any API key.
- Do not call the EMR administrative reset endpoint for live verification.
- Use `python -m scripts.live_emr_verification` for shared-sandbox testing so every run has its own synthetic name and reserved test phone number.
- Do not claim a booking, cancellation, or transfer unless the EMR or Vapi confirms it.

## Verification Status

The local test suite, Python compilation, Docker image build, and containerized `/health` check pass. The secured webhook is live through ngrok and was verified with both rejected and accepted bearer-authenticated requests.

Vapi assistant `9ca91034-3de4-44be-bba6-5aa756128d64` (`Heartland Cardiology`) has the eight function tools, scheduling instructions, request-start filler messages, and Vapi Bearer custom credential configured. The phone number `+1 601 419 9125` is assigned to it.

The live webhook has verified registration, patient verification, provider and slot lookup, booking, rescheduling without a replacement type, and cancellation against the sandbox. Each mutation was checked directly in the EMR. The original appointment type was retained during rescheduling.

Future live checks use the no-reset runner. Each run creates a unique synthetic patient and scheduled appointment, then leaves those records in the shared sandbox.

A Vapi dashboard web call was attempted for provider lookup. The dashboard browser denied microphone permission before a conversation started, so no Vapi tool call was emitted or logged from that call. A real inbound phone call was not placed during this setup.
