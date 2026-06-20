# Basata Voice AI Take-Home - Implementation Tasks

This task list is for Codex to implement the Basata take-home exercise end to end. It is based on:

- `outputs/Basata_Voice_AI_Take_Home_Detailed_Guide.pdf` English content only. Arabic translation and duplicate translated lines are intentionally ignored.
- Drive folder: `https://drive.google.com/drive/folders/1hFggNGII9quTX6q9mun4Eq0p7h6zB2MC?usp=drive_link`
- Drive docs: `candidate-brief-section-1.md`, `architecture-diagram.md`, `vapi-reference.md`
- Current Vapi docs checked through Context7 MCP.
- Current FastAPI docs checked through Context7 MCP.
- CardioChart Pro OpenAPI from `https://basata-interview-sandbox-emr.ngrok.app/openapi.json`

## Current Known Inputs

- Vapi phone number: `+1 601 419 9125`
- Vapi phone resource ID: `3d091f26-d420-4fd3-a773-0122e2f80f4b`
- Vapi MCP server for Codex: configured in local Codex config through `mcp-remote` against `https://mcp.vapi.ai/mcp`
- Vapi MCP caveat: Codex may need restart before Vapi MCP tools appear in the active session.
- EMR base URL: `https://basata-interview-sandbox-emr.ngrok.app`
- EMR docs: `https://basata-interview-sandbox-emr.ngrok.app/docs`
- EMR OpenAPI: `https://basata-interview-sandbox-emr.ngrok.app/openapi.json`
- Preferred backend stack: FastAPI, Pydantic, httpx, pytest, uvicorn, Docker, ngrok.

## MCP Support And Usage Policy

Use MCPs only when they directly support a concrete implementation, configuration, or verification task. Do not install a broad set of MCPs up front.

### Confirmed MCPs

- **Vapi MCP**: use for Vapi assistant, function tool, phone-number, and dashboard configuration in the Interview Sandbox organization. It is configured through `mcp-remote` against `https://mcp.vapi.ai/mcp`. Restart Codex and confirm the Vapi tools are available before relying on it. If the tools are still unavailable, configure and verify through the Vapi dashboard instead.
- **Context7 MCP**: use before making decisions that depend on current Vapi, FastAPI, Python package, Docker, ngrok, or deployment documentation. Resolve the relevant library first, then query its current official documentation.
- **Chrome DevTools MCP**: use for non-destructive Vapi dashboard inspection, authenticated configuration verification, dashboard web-call testing, and browser/network diagnostics. Do not use it to make real outbound calls without approval.

### On-Demand MCP Setup

- Codex may install or configure another MCP only when it directly unblocks a concrete implementation or verification task.
- Before adding an MCP, record its purpose, configuration location, required credential, and verification step in the README or implementation notes.
- Do not add unrelated configured MCPs to this project merely because they are available.
- Never commit API keys, access tokens, webhook secrets, or MCP credentials. Do not put them in `.env.example`, logs, screenshots, or submission documentation.
- Ask for approval before an MCP action that can create external resources with cost or user impact, modify an existing Vapi assistant or phone assignment that may disrupt another setup, or place a real call.

## Exercise Requirements

- Build a telephony-enabled Vapi voice AI agent for inbound cardiology scheduling calls.
- Register a new patient.
- Schedule a new appointment.
- Cancel an existing appointment.
- Reschedule an existing appointment.
- Look up an existing appointment.
- Provide well-designed Vapi function tool schemas.
- Build a backend webhook server that services Vapi tool calls and calls the mock EMR.
- Use the CardioChart Pro EMR as the source of truth.
- Configure the Vapi assistant in the Interview Sandbox organization.
- Assign the Vapi phone number to the assistant.
- Submit a git repo with code and README.
- Submit a link to the Vapi assistant.
- Submit a short 1-2 page write-up covering what was built, deferred, and future work.

## Non-Negotiable Behavior

- Do not fabricate providers, slots, patient details, or appointment confirmations.
- Always confirm exact mutation details before registration, booking, cancellation, or rescheduling.
- Verify an existing caller by matching their registered phone and DOB before revealing or changing appointment information.
- Keep the webhook server stateless for conversation state; Vapi owns call transcript and turn history.
- Use the EMR as the only source of truth for patients, providers, slots, and appointments.
- Handle slow/down EMR behavior explicitly.
- Use short voice-friendly responses.
- Configure tool filler messages so callers do not sit in silence during backend calls.
- Preserve the original appointment if replacement booking fails during rescheduling.
- Report partial reschedule failure honestly and escalate to human support.
- Do not configure native Vapi `transferCall` until a real front-desk E.164 number and operating hours are supplied.
- Use an explicit `human_handoff_required` outcome when staff assistance is needed but no transfer destination is configured; never claim that a transfer occurred.
- Log only redacted call metadata. Do not persist transcripts or raw tool arguments containing PII.
- Do not use the EMR administrative reset endpoint. Shared-sandbox tests must use a unique synthetic patient identity for every run.

## EMR API Contract

Implement an EMR client for these endpoints:

- `GET /providers`
- `GET /providers/{provider_id}`
- `GET /providers/{provider_id}/slots`
- `GET /slots`
- `GET /patients`
- `POST /patients`
- `GET /patients/{patient_id}`
- `GET /appointments`
- `POST /appointments`
- `GET /appointments/{appointment_id}`
- `DELETE /appointments/{appointment_id}`

Do not implement normal workflow dependencies on administrative EMR endpoints.

## EMR Enums

Appointment types:

- `new_patient`
- `follow_up`
- `procedure_consult`
- `stress_test`
- `telehealth`

Appointment statuses:

- `scheduled`
- `cancelled`
- `completed`
- `no_show`

Specialties:

- `general_cardiology`
- `interventional_cardiology`
- `electrophysiology`

## Provider Rules To Respect

- `prov_martinez`, Dr. Sofia Martinez, MD
- Specialties: general cardiology, interventional cardiology
- Appointment types: new patient, follow-up, procedure consult
- Restrictions: procedure consults Tuesday/Thursday only; general cardiology Monday-Friday.

- `prov_patel`, Dr. Raj Patel, MD
- Specialties: general cardiology
- Appointment types: new patient, follow-up
- Restrictions: does not see patients under 16.

- `prov_kim`, Dr. Emily Kim, MD
- Specialties: general cardiology, electrophysiology
- Appointment types: new patient, follow-up, stress test, telehealth
- Restrictions: Monday/Wednesday/Friday only; telehealth Friday only.

- `prov_williams`, Jamie Williams, PA-C
- Specialties: general cardiology
- Appointment types: new patient, follow-up
- Restrictions: cannot perform procedure consults or stress tests.

Implementation rule:

- Use provider restrictions to guide the conversation, but always query real EMR slots before offering availability.

## Architecture Target

Expected flow:

```text
Caller
  -> Vapi phone number +1 601 419 9125
  -> Vapi assistant
  -> Vapi STT
  -> Vapi model with system prompt and tool definitions
  -> Vapi sends tool-calls to backend POST /vapi/webhook
  -> FastAPI validates and dispatches tool calls
  -> EMR client calls CardioChart Pro
  -> FastAPI returns Vapi tool results
  -> Vapi model speaks final answer through TTS
```

## Backend Project Structure

Create this structure:

```text
app/
  __init__.py
  main.py
  config.py
  errors.py
  models/
    __init__.py
    emr.py
    tools.py
    vapi.py
  clients/
    __init__.py
    emr.py
  services/
    __init__.py
    patients.py
    scheduling.py
    appointments.py
    reschedule.py
    tool_dispatch.py
  telemetry/
    __init__.py
    logging.py
tests/
  fixtures/
  test_emr_client.py
  test_vapi_payloads.py
  test_patient_workflows.py
  test_scheduling_workflows.py
  test_cancel_reschedule.py
  test_webhook.py
Dockerfile
README.md
requirements.txt
.env.example
```

## Backend Dependencies

Use these dependencies unless the repo already defines a different standard:

```text
fastapi
uvicorn[standard]
pydantic
pydantic-settings
httpx
pytest
pytest-asyncio
respx
python-dotenv
```

## Environment Variables

Create `.env.example` with:

```text
EMR_BASE_URL=https://basata-interview-sandbox-emr.ngrok.app
HTTP_TIMEOUT_SECONDS=10
LOG_LEVEL=INFO
VAPI_WEBHOOK_SECRET=
ENABLE_IDEMPOTENCY_MEMORY=true
```

Configure a Vapi Custom Credential with Bearer Token authentication, header name `Authorization`, and the Bearer prefix enabled. Attach its `credentialId` to every custom tool `server` configuration and any configured assistant server.

Backend authentication tasks:

- [ ] Require `Authorization: Bearer <VAPI_WEBHOOK_SECRET>` on `POST /vapi/webhook`.
- [ ] Compare the supplied token with `VAPI_WEBHOOK_SECRET` using a constant-time comparison.
- [ ] Return `401` without request details for a missing or invalid credential.
- [ ] Never log the authorization header, secret, or unredacted request body.

## FastAPI App Tasks

- [ ] Create `app/main.py`.
- [ ] Instantiate `FastAPI(title="Basata Voice AI Webhook")`.
- [ ] Add `GET /health`.
- [ ] Add `POST /vapi/webhook`.
- [ ] Use async endpoints.
- [ ] Add structured exception handling for known workflow errors.
- [ ] Return JSON responses only.
- [ ] Do not expose stack traces to Vapi.
- [ ] Log `call_id`, `tool_call_id`, tool name, duration, and outcome.
- [ ] Redact phone, DOB, email, insurance member ID, and transcript text from normal logs.

Acceptance checks:

- `GET /health` returns `{"status": "ok"}`.
- `POST /vapi/webhook` accepts a valid `tool-calls` message.
- Unknown message types return a safe `ignored` or `unsupported_message_type` result, not a server crash.

## Vapi Payload Compatibility Tasks

Current Vapi docs and the exercise reference show different payload variants. Support both.

Current Vapi-style tool call:

```json
{
  "message": {
    "type": "tool-calls",
    "toolCallList": [
      {
        "id": "toolu_123",
        "name": "find_patient",
        "arguments": {
          "phone": "+15551234001"
        }
      }
    ]
  }
}
```

Exercise reference payload:

```json
{
  "message": {
    "type": "tool-calls",
    "toolCallList": [
      {
        "id": "tc_xyz789",
        "type": "function",
        "function": {
          "name": "search_providers",
          "arguments": "{\"specialty\":\"interventional_cardiology\"}"
        }
      }
    ]
  }
}
```

Also support `toolWithToolCallList` where parameters may appear under:

- `toolCall.parameters`
- `toolCall.function.parameters`
- `toolCall.function.arguments`

Tasks:

- [ ] Create `models/vapi.py`.
- [ ] Create a normalization function that converts every Vapi variant into internal `NormalizedToolCall`.
- [ ] Internal model fields: `tool_call_id`, `name`, `arguments`, `call_id`, `customer_number`.
- [ ] Parse `arguments` if it is a JSON string.
- [ ] Use object-valued `arguments` directly if already an object.
- [ ] Ignore unrelated Vapi metadata except for logging/correlation.
- [ ] Return one result per tool call.
- [ ] Include `toolCallId` in every result.
- [ ] Include `name` in results for current Vapi compatibility.
- [ ] Return `result` as a JSON string.

Vapi response shape:

```json
{
  "results": [
    {
      "name": "find_patient",
      "toolCallId": "toolu_123",
      "result": "{\"status\":\"found\",\"patient\":{\"id\":\"pat_123\"}}"
    }
  ]
}
```

## Tool Surface

Implement these backend-dispatched tools:

- `find_patient`
- `register_patient`
- `list_providers`
- `search_slots`
- `list_patient_appointments`
- `book_appointment`
- `cancel_appointment`
- `reschedule_appointment`

Do not expose raw EMR endpoints directly to the model. Tool responses should be compact, speech-friendly, and include machine IDs for follow-up calls.

### Existing-Patient Verification Contract

The webhook is stateless, so protected existing-patient tools cannot rely on an earlier conversational verification step. Every tool that reveals or mutates an existing patient's appointment data must receive `verification_phone` and `date_of_birth`, then re-validate both against the EMR patient record before proceeding.

- Protected tools: `list_patient_appointments`, `book_appointment`, `cancel_appointment`, and `reschedule_appointment`.
- `verification_phone` must match the patient's registered phone after normalization.
- `date_of_birth` must match the EMR record exactly in `YYYY-MM-DD` format.
- When Vapi supplies an inbound caller number, log only a redacted comparison outcome; do not rely on it as a substitute for the verified phone and DOB pair.
- On verification failure, return `identity_verification_failed` without appointment details or mutation attempts.

## Tool: `find_patient`

Purpose:

- Resolve and verify an existing caller by matching registered phone and DOB.

Arguments:

```json
{
  "phone": "string",
  "date_of_birth": "YYYY-MM-DD"
}
```

Tasks:

- [ ] Query `GET /patients`.
- [ ] Normalize and match the registered phone and DOB together.
- [ ] Return `verified`, `not_found`, or `invalid_search`.
- [ ] Do not reveal appointment information from this tool.
- [ ] Include only minimum needed patient fields in response.

Response example:

```json
{
  "status": "verified",
  "patient": {
    "id": "pat_santos",
    "first_name": "Maria",
    "last_name": "Santos",
    "date_of_birth": "1985-03-15",
    "phone": "+15551234001"
  }
}
```

## Tool: `register_patient`

Purpose:

- Register a first-time patient after the assistant has confirmed the details.

Arguments:

```json
{
  "first_name": "string",
  "last_name": "string",
  "date_of_birth": "YYYY-MM-DD",
  "phone": "string",
  "email": "string | null",
  "insurance_provider": "string | null",
  "insurance_member_id": "string | null"
}
```

Tasks:

- [ ] Validate required fields.
- [ ] Normalize phone where possible.
- [ ] Search by phone before creating to avoid duplicates.
- [ ] Call `POST /patients`.
- [ ] If EMR rejects duplicate phone, return `duplicate_phone` and include safe lookup guidance.
- [ ] Return created patient ID.

## Tool: `list_providers`

Purpose:

- Return available providers and restrictions by specialty or appointment type.

Arguments:

```json
{
  "specialty": "general_cardiology | interventional_cardiology | electrophysiology | null",
  "appointment_type": "new_patient | follow_up | procedure_consult | stress_test | telehealth | null"
}
```

Tasks:

- [ ] Query `GET /providers`.
- [ ] Filter by specialty if provided.
- [ ] Filter locally by supported appointment type if provided.
- [ ] Return provider IDs, names, specialties, supported appointment types, and restrictions.
- [ ] Keep response short enough for the model to speak naturally.

## Tool: `search_slots`

Purpose:

- Search real EMR availability after patient identity and appointment type are known.

Arguments:

```json
{
  "patient_id": "string",
  "appointment_type": "new_patient | follow_up | procedure_consult | stress_test | telehealth",
  "start_date": "YYYY-MM-DD | null",
  "end_date": "YYYY-MM-DD | null",
  "start_time_of_day": "HH:MM | null",
  "end_time_of_day": "HH:MM | null",
  "days_of_week": "MON,TUE,WED | null",
  "provider_id": "string | null",
  "earliest_available": "boolean | null",
  "number_of_slots_to_present": "integer"
}
```

Tasks:

- [ ] Validate `patient_id`.
- [ ] Validate appointment type enum.
- [ ] Default slot window to a practical range if missing, such as today through 14 days.
- [ ] Limit returned slots to 1-5.
- [ ] Call `GET /slots`.
- [ ] Include provider display name in response by joining provider data.
- [ ] Return `no_slots` if empty.
- [ ] Do not invent alternatives not returned by EMR.

## Tool: `list_patient_appointments`

Purpose:

- Return active appointments for a verified patient.

Arguments:

```json
{
  "patient_id": "string",
  "verification_phone": "string",
  "date_of_birth": "YYYY-MM-DD",
  "include_cancelled": false
}
```

Tasks:

- [ ] Call `GET /appointments?patient_id=...`.
- [ ] Re-verify `verification_phone` and `date_of_birth` against the patient record before returning appointments.
- [ ] Default `include_cancelled=false`.
- [ ] Join provider names.
- [ ] Return appointment IDs, provider, start, end, type, status, reason, and telehealth flag.
- [ ] Do not list another patient appointments.

## Tool: `book_appointment`

Purpose:

- Book a confirmed appointment.

Arguments:

```json
{
  "patient_id": "string",
  "verification_phone": "string",
  "date_of_birth": "YYYY-MM-DD",
  "provider_id": "string",
  "start_time": "ISO date-time",
  "appointment_type": "new_patient | follow_up | procedure_consult | stress_test | telehealth",
  "reason": "string | null"
}
```

Tasks:

- [ ] Validate patient exists.
- [ ] Re-verify the existing patient's phone and DOB before booking.
- [ ] Validate provider exists.
- [ ] Optionally re-check the selected slot immediately before booking.
- [ ] Call `POST /appointments`.
- [ ] Handle `409` slot conflict.
- [ ] Return the actual EMR appointment object.
- [ ] Never say booked unless EMR returns success.

## Tool: `cancel_appointment`

Purpose:

- Cancel a verified patient's explicitly confirmed appointment.

Arguments:

```json
{
  "patient_id": "string",
  "verification_phone": "string",
  "date_of_birth": "YYYY-MM-DD",
  "appointment_id": "string",
  "confirmed": true
}
```

Tasks:

- [ ] Require `confirmed=true`.
- [ ] Re-verify the existing patient's phone and DOB before reading or cancelling the appointment.
- [ ] Call `GET /appointments/{appointment_id}` first.
- [ ] Verify appointment belongs to `patient_id`.
- [ ] Verify appointment status is `scheduled`.
- [ ] Call `DELETE /appointments/{appointment_id}`.
- [ ] Return updated appointment status.
- [ ] Return safe errors for ownership mismatch, already cancelled, completed, or not found.

## Tool: `reschedule_appointment`

Purpose:

- Replace an existing appointment with a confirmed new slot.

Arguments:

```json
{
  "patient_id": "string",
  "verification_phone": "string",
  "date_of_birth": "YYYY-MM-DD",
  "appointment_id": "string",
  "new_provider_id": "string",
  "new_start_time": "ISO date-time",
  "new_appointment_type": "new_patient | follow_up | procedure_consult | stress_test | telehealth | null",
  "reason": "string | null",
  "confirmed": true
}
```

Server algorithm:

- [ ] Require `confirmed=true`.
- [ ] Fetch old appointment.
- [ ] Re-verify the existing patient's phone and DOB before reading or changing the appointment.
- [ ] Verify old appointment belongs to patient.
- [ ] Verify old appointment is `scheduled`.
- [ ] Default `new_appointment_type` to the old appointment type when it is `null`.
- [ ] Book new appointment first.
- [ ] If new booking fails or returns `409`, preserve old appointment and return `conflict`.
- [ ] After new booking succeeds, cancel old appointment.
- [ ] If old cancellation succeeds, return `rescheduled`.
- [ ] If old cancellation fails, attempt to cancel the newly created appointment as compensation.
- [ ] If compensation succeeds, return `reschedule_failed_original_preserved`.
- [ ] If compensation fails, return `partial_failure_requires_human`.

Do not implement reschedule as cancel-first. That risks losing the original appointment.

## Error Model

Use consistent tool result statuses:

- `ok`
- `found`
- `not_found`
- `multiple_matches`
- `created`
- `duplicate_phone`
- `no_slots`
- `booked`
- `conflict`
- `cancelled`
- `rescheduled`
- `invalid_arguments`
- `ownership_mismatch`
- `already_cancelled`
- `emr_unavailable`
- `partial_failure_requires_human`
- `human_handoff_required`
- `identity_verification_failed`
- `unsupported_tool`

Tasks:

- [ ] Create `errors.py` with workflow exceptions.
- [ ] Map EMR `400`, `404`, `409`, `422`, `5xx`, and timeout cases.
- [ ] Return user-safe errors to Vapi.
- [ ] Return `human_handoff_required` when staff assistance is needed but native transfer is unavailable; the result must not imply a completed transfer.
- [ ] Return `identity_verification_failed` before any protected appointment disclosure or mutation when phone and DOB do not match.
- [ ] Log enough technical detail locally for debugging.

## Idempotency Tasks

Vapi may retry or duplicate tool calls. Mutations must be protected.

- [ ] Use `toolCallId` as idempotency key for mutating tools.
- [ ] Store mutation result in in-memory TTL cache for the take-home demo.
- [ ] Include note in README that production should use Redis/Postgres.
- [ ] Return cached result if the same `toolCallId` repeats.
- [ ] Do not blindly retry `POST /patients` or `POST /appointments` after timeout.
- [ ] For uncertain booking timeout, query patient appointments by patient/provider/start/type before deciding outcome.

## Vapi Assistant Configuration Tasks

Use Vapi dashboard or Vapi MCP after Codex restart.

- [ ] Verify the active MCP inventory: Context7 is callable; Vapi MCP tools are available after restart or the dashboard fallback is selected; Chrome DevTools is used only after dashboard authentication.
- [ ] Confirm the Vapi MCP tools are available after Codex restart.
- [ ] List phone numbers and confirm `+1 601 419 9125` / resource ID `3d091f26-d420-4fd3-a773-0122e2f80f4b`.
- [ ] Create or update a Vapi assistant in the `Interview Sandbox` organization.
- [ ] Use OpenAI `gpt-5-mini` or closest available.
- [ ] Configure a clear professional voice.
- [ ] Configure first message.
- [ ] Configure system prompt.
- [ ] Add all custom function tools.
- [ ] Set each tool `server.url` to the deployed backend `/vapi/webhook`.
- [ ] Create the Vapi Bearer Token Custom Credential and attach its `credentialId` to every tool `server` configuration.
- [ ] Keep scheduling and mutation tools synchronous.
- [ ] Add `request-start` filler messages for each tool.
- [ ] Configure `assistant.server.url` for non-tool events if needed.
- [ ] Configure `serverMessages` to include `end-of-call-report` and `status-update` if the backend should receive them.
- [ ] Do not configure native `transferCall`: no real front-desk E.164 destination or business hours are available.
- [ ] Configure the system prompt to use the `human_handoff_required` voice fallback for unsupported requests, verification failure, EMR failure, and uncertain mutation outcomes.
- [ ] Assign phone number `+1 601 419 9125` to the assistant.
- [ ] Test in-dashboard web call.
- [ ] Test real inbound phone call.

## Vapi Tool Configuration Pattern

Each custom function tool should follow this pattern:

```json
{
  "type": "function",
  "function": {
    "name": "find_patient",
    "description": "Find a patient by phone or by last name and DOB.",
    "parameters": {
      "type": "object",
      "properties": {}
    }
  },
  "server": {
    "url": "https://YOUR_PUBLIC_HOST/vapi/webhook",
    "credentialId": "cred_your_vapi_bearer_credential"
  },
  "async": false,
  "messages": [
    {
      "type": "request-start",
      "content": "Let me look up your record."
    }
  ]
}
```

Server URL fallback priority from current Vapi docs:

1. `tool.server.url`
2. `assistant.server.url`
3. `phoneNumber.server.url`
4. `org.server.url`

Prefer explicit `tool.server.url` for every custom EMR tool.

## System Prompt Requirements

Create a system prompt with these rules:

- You are the phone scheduling assistant for Heartland Cardiology.
- You can identify patients, register new patients, schedule appointments, look up appointments, cancel appointments, and reschedule appointments.
- The EMR is the source of truth.
- Never invent providers, slots, patients, or confirmations.
- Before revealing or changing existing appointment information, require a successful match of the registered phone and DOB.
- Ask for explicit confirmation before creating, cancelling, or rescheduling.
- Present at most three slot options at a time.
- Keep spoken responses short.
- Do not diagnose or provide medical advice.
- For emergency symptoms, advise emergency services and do not proceed as routine scheduling.
- When identity cannot be verified, a request is unsupported, the EMR is unavailable, or a mutation outcome is uncertain, invoke the handoff fallback. State that staff assistance is required and do not say a transfer has occurred.
- Do not invoke native `transferCall` until a real front-desk number and business hours are configured.

## Suggested Filler Messages

- `find_patient`: "Let me look up your record."
- `register_patient`: "I am creating your patient record now."
- `list_providers`: "Let me check the available providers."
- `search_slots`: "One moment while I check availability."
- `list_patient_appointments`: "Let me pull up your appointments."
- `book_appointment`: "I am booking that appointment."
- `cancel_appointment`: "I am cancelling that appointment now."
- `reschedule_appointment`: "I am changing that appointment now."
- `human_handoff_required`: "I need to have our staff help with this. Please contact the clinic's front desk for assistance."

## Conversation Workflow Tasks

Opening:

- [ ] Greet as Heartland Cardiology.
- [ ] State supported tasks in one sentence.
- [ ] Ask what the caller wants to do.

Existing patient identity:

- [ ] Use inbound phone number first.
- [ ] Ask for the registered phone and DOB before revealing appointment details or taking an appointment action.
- [ ] Call `find_patient` only with the registered phone and DOB; do not use name-only lookup for protected actions.
- [ ] If the phone and DOB do not match one record, do not reveal records or attempt a mutation.
- [ ] Use the handoff fallback and state that clinic staff must assist; do not claim a phone transfer occurred.

New patient registration:

- [ ] Collect first name.
- [ ] Collect last name.
- [ ] Collect DOB.
- [ ] Collect phone.
- [ ] Collect optional email.
- [ ] Collect optional insurance provider and member ID when available.
- [ ] Read back details.
- [ ] Ask explicit confirmation.
- [ ] Register patient.
- [ ] Continue to scheduling.

Scheduling:

- [ ] Determine appointment type.
- [ ] Ask one clarifying question if type is unclear.
- [ ] Ask date/time preference.
- [ ] Ask provider preference only when useful.
- [ ] Search slots.
- [ ] Present no more than three options.
- [ ] Confirm selected provider/date/time/type/reason.
- [ ] Book appointment.
- [ ] Read final confirmation from EMR response.

Cancellation:

- [ ] Verify patient.
- [ ] List active appointments.
- [ ] Identify exact appointment.
- [ ] Read back exact appointment details.
- [ ] Ask explicit cancellation confirmation.
- [ ] Cancel appointment.
- [ ] Confirm cancelled status from EMR response.

Rescheduling:

- [ ] Verify patient.
- [ ] Identify old appointment.
- [ ] Search replacement slots.
- [ ] Present no more than three options.
- [ ] Confirm old appointment and new slot.
- [ ] Call composite reschedule tool.
- [ ] Report success or partial failure accurately.
- [ ] Preserve the original appointment type unless the caller explicitly requests another type.
- [ ] Use the handoff fallback on partial failure; do not claim a transfer occurred.

## Backend Test Plan

Write tests before or alongside implementation.

Payload parsing:

- [ ] Current Vapi object-valued `toolCallList.arguments`.
- [ ] Exercise reference nested `function.arguments` JSON string.
- [ ] `toolWithToolCallList` parameter variant.
- [ ] Unknown tool.
- [ ] Malformed arguments.
- [ ] Multiple tool calls in one webhook request.

Patient workflows:

- [ ] Find and verify by matching phone and DOB.
- [ ] Reject matching phone with wrong DOB without returning appointment information.
- [ ] Reject matching DOB with wrong phone without returning appointment information.
- [ ] Register success.
- [ ] Duplicate phone handling.

Scheduling:

- [ ] Provider list filters by specialty.
- [ ] Provider list filters by appointment type.
- [ ] Slot search success.
- [ ] Slot search no slots.
- [ ] Booking success.
- [ ] Booking conflict `409`.
- [ ] Booking timeout does not claim success.

Cancellation:

- [ ] Cancel success.
- [ ] Requires `confirmed=true`.
- [ ] Ownership mismatch.
- [ ] Already cancelled.
- [ ] Not found.

Reschedule:

- [ ] New booking conflict preserves original.
- [ ] New booking success then old cancellation success.
- [ ] Omitted `new_appointment_type` preserves the old appointment type.
- [ ] Explicit `new_appointment_type` is applied when supported by the replacement slot.
- [ ] Old cancellation failure triggers compensation.
- [ ] Compensation failure returns `partial_failure_requires_human`.
- [ ] Duplicate tool call returns cached result.

Webhook:

- [ ] `/health` works.
- [ ] Missing bearer credential returns `401` without request details.
- [ ] Invalid bearer credential returns `401` without request details.
- [ ] `/vapi/webhook` returns valid Vapi response.
- [ ] Unknown message type handled safely.
- [ ] End-of-call-report logs redacted metadata only and does not persist transcript text.
- [ ] `human_handoff_required` produces a clear voice-safe result without a native transfer request.

Shared sandbox control:

- [ ] Every live run uses a unique synthetic patient name and reserved test phone number.
- [ ] Created synthetic patient and appointment records remain in the shared sandbox.

## Manual Voice Test Plan

Run these after deployment and Vapi configuration:

- [ ] Existing patient provides registered phone and DOB before appointment lookup.
- [ ] Unknown caller registers as new patient and books an appointment.
- [ ] Caller requests general cardiology earliest available.
- [ ] Caller requests procedure consult on a non-allowed day.
- [ ] Caller requests telehealth before Friday.
- [ ] Caller asks for Dr. Patel for a patient under 16.
- [ ] Caller cancels a specific appointment.
- [ ] Caller reschedules an appointment successfully.
- [ ] Caller reschedules without changing appointment type and the original type is preserved.
- [ ] Caller reschedule hits slot conflict and original appointment remains.
- [ ] Identity verification failure reveals no appointment data and uses the handoff fallback.
- [ ] EMR unavailable or simulated failure uses the handoff fallback without claiming a transfer.
- [ ] Caller asks for medical advice and assistant refuses clinical guidance.

## Deployment Tasks

- [ ] Create `requirements.txt`.
- [ ] Create `Dockerfile`.
- [ ] Verify local run with `uvicorn app.main:app --reload`.
- [ ] Run tests locally.
- [ ] Start ngrok with a public HTTPS endpoint for the interview demo.
- [ ] Set Vapi tool server URLs to public `/vapi/webhook`.
- [ ] Verify Vapi can reach backend.
- [ ] Make at least one dashboard web call.
- [ ] Make at least one real call to `+1 601 419 9125`.
- [ ] Confirm EMR mutation happened as expected.

## README Tasks

README must include:

- [ ] What the project does.
- [ ] Architecture summary.
- [ ] Requirements and environment variables.
- [ ] How to install dependencies.
- [ ] How to run locally.
- [ ] How to run tests.
- [ ] How to expose with ngrok.
- [ ] How to configure Vapi assistant/tools.
- [ ] How to create and attach the Vapi Bearer Token Custom Credential without exposing the token.
- [ ] Tool schema summary.
- [ ] EMR integration notes.
- [ ] Known limitations.
- [ ] Safety and privacy notes.
- [ ] Redacted logging and no-transcript-retention policy.
- [ ] How reschedule works and why it books first.
- [ ] Existing-patient verification requirements and protected-tool inputs.
- [ ] Human-handoff fallback and the deferred native transfer dependency.
- [ ] Troubleshooting for Vapi payload variants.

## Final Write-Up Tasks

Create a short 1-2 page write-up covering:

- [ ] What was built.
- [ ] What was deferred.
- [ ] Why the server is stateless.
- [ ] How hallucination is prevented.
- [ ] How provider restrictions are handled.
- [ ] How rescheduling handles partial failure.
- [ ] How voice latency is handled.
- [ ] What would change for production.

## Submission Checklist

- [ ] Git repo contains backend code.
- [ ] Git repo contains README.
- [ ] Git repo contains tests.
- [ ] No API keys or secrets committed.
- [ ] Vapi assistant exists in Interview Sandbox.
- [ ] Vapi assistant linked in submission.
- [ ] Phone number `+1 601 419 9125` assigned to assistant.
- [ ] Public backend URL is reachable by Vapi.
- [ ] New patient registration tested.
- [ ] Scheduling tested.
- [ ] Cancellation tested.
- [ ] Rescheduling tested.
- [ ] Human transfer path configured or documented as blocked by missing destination.
- [ ] Short write-up included.
- [ ] Optional Loom recording completed.

## Resolved Demo Defaults And External Dependency

Use these decisions for the take-home implementation:

- **Identity:** registered phone plus DOB are required for every existing-patient appointment disclosure or mutation. Do not use name-only lookup for protected actions.
- **Registration data:** email, insurance provider, and insurance member ID remain optional because the EMR schema marks them optional.
- **Language:** support English only for submission scope.
- **Appointment history:** hide cancelled appointments by default; include them only when the caller explicitly asks.
- **Rescheduling:** preserve the old appointment type unless the caller explicitly selects another supported type.
- **Security and audit:** use a Vapi Bearer Token Custom Credential through `server.credentialId`; validate the bearer token in FastAPI; retain only redacted end-of-call metadata and no transcript store.
- **Deployment:** use an ngrok public HTTPS endpoint for the interview demo.
- **Shared sandbox isolation:** never use the administrative reset endpoint. Generate a unique synthetic patient name and reserved test phone number for every live run, then leave all generated records in the sandbox.
- **Native human transfer:** defer Vapi `transferCall` until a real front-desk E.164 number and business hours are provided. Until then, use the app-level `human_handoff_required` voice fallback.

Only this external detail remains before native transfer can be enabled:

- Front-desk E.164 transfer number and its operating hours.

## Implementation Order

Follow this order:

1. Build backend skeleton and health endpoint.
2. Implement Vapi payload normalization.
3. Implement EMR client.
4. Implement read-only tools: `find_patient`, `list_providers`, `search_slots`, `list_patient_appointments`.
5. Implement mutating tools: `register_patient`, `book_appointment`, `cancel_appointment`.
6. Implement composite `reschedule_appointment`.
7. Add idempotency for mutating tool calls.
8. Add tests for payload variants and workflows.
9. Add README and `.env.example`.
10. Configure and test webhook bearer authentication.
11. Run local test suite.
12. Expose backend through ngrok.
13. Configure Vapi assistant and tools.
14. Assign phone number.
15. Run dashboard web call.
16. Run real phone call.
17. Write final submission summary.

## Stop Conditions For Codex

Stop and ask the user before:

- Calling the EMR administrative reset endpoint.
- Creating outbound Vapi calls to real phone numbers.
- Using or exposing any API key in committed files.
- Assigning a Vapi phone number if an existing assistant is already attached and the change could disrupt another setup.
- Configuring transferCall without a confirmed transfer destination.
