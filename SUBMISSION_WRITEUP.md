# Basata Voice AI Take-Home Write-Up

## What Was Built

The project implements a FastAPI webhook backend for a Vapi cardiology scheduling assistant. It supports new-patient registration, existing-patient phone-and-DOB verification, provider discovery, availability search, appointment lookup, booking, cancellation, and book-first rescheduling against the CardioChart Pro sandbox.

The configured assistant is [Heartland Cardiology](https://dashboard.vapi.ai/assistants/9ca91034-3de4-44be-bba6-5aa756128d64?tab=assistant). The Vapi phone number `+1 601 419 9125` is assigned to it. I added eight function tools and the short filler messages.

The webhook accepts current Vapi `tool-calls` payloads, the exercise's nested JSON-string function arguments, and `toolWithToolCallList` parameter variants. Responses use Vapi `results` with tool call IDs and JSON-string results.

## Safety And Reliability

The EMR is the only source of truth. Existing-patient appointment data and mutations re-verify the registered phone and DOB server-side. Mutations require explicit confirmation fields. Vapi retry protection caches mutation results by `toolCallId` for the demo process.

Rescheduling books the replacement first. A booking conflict leaves the original appointment unchanged. If old-appointment cancellation fails after booking, the service compensates by cancelling the replacement; if that compensation fails, it returns `partial_failure_requires_human`.

The webhook uses a Vapi Custom Credential Bearer token and uses constant-time comparison. The same credential is selected in all eight tools. Logs keep only redacted call/tool metadata, not transcript or patient identifying fields.

## Deferred Items

Native Vapi transfer is still deferred. I do not have front-desk E.164 number or business hours. The assistant uses `human_handoff_required` and does not say a transfer happened.

Vapi assistant, tools, credential, ngrok URL, and phone number assignment are done. Live test with the public webhook and real EMR sandbox included registration, providers, slots, booking, reschedule, and cancellation. I checked the appointments directly from EMR. Reschedule kept the old appointment type when no new type was sent.

For future shared sandbox tests, the project uses unique synthetic patient names and reserved test phone numbers. There is no automatic or manual sandbox reset. The generated patient and appointment records stay in the sandbox.

I also tried Vapi dashboard web call for provider lookup. The browser blocked microphone permission, so the call did not start and no dashboard tool call was logged. A real phone call was not made.

## Production Follow-Up

For production, I would use Redis or Postgres for idempotency, add credential rotation, and add better logs for EMR latency and errors. I would use managed HTTPS instead of ngrok. Before production, the clinic should give the real transfer policy and front-desk number.
