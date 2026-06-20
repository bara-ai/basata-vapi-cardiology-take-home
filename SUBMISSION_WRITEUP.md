# Basata Voice AI Take-Home Write-Up

## What I Built

I built a Vapi scheduling assistant for Heartland Cardiology with a FastAPI webhook backend connected to the CardioChart Pro sandbox EMR. The assistant is configured in the Interview Sandbox as [Heartland Cardiology](https://dashboard.vapi.ai/assistants/9ca91034-3de4-44be-bba6-5aa756128d64?tab=assistant) and is assigned to `+1 601 419 9125`.

The assistant supports new-patient registration, existing-patient verification, provider lookup, slot search, appointment booking, appointment lookup, cancellation, and rescheduling. Eight Vapi function tools map these tasks to the backend. The backend then reads or changes only the EMR data needed for that step. Providers, available times, appointment details, and confirmations always come from the EMR rather than from the model.

## Important Workflow Decisions

For an existing patient, the system requires both the phone number on the record and the date of birth before it returns appointments or allows a booking, cancellation, or reschedule. Matching only a name or only a phone number would be too weak because it could disclose another patient's information or allow a caller to change their appointment. The backend repeats this verification for protected actions instead of relying only on what the model remembers from the conversation.

For a new patient, the assistant collects first name, last name, date of birth, and phone number. Email and insurance fields are collected when available because they are optional in the EMR. Before creating the patient, the assistant reads the details back and waits for a clear confirmation. It also checks for an existing phone number before creation, which avoids duplicate records during retries or repeated requests.

Booking and rescheduling require an explicit spoken confirmation after the assistant repeats the provider, date, time, appointment type, and any reason supplied. The backend does not report success until the EMR returns a successful result. This prevents the assistant from making a confident statement based only on a planned tool call.

## Failure Handling And Voice Design

The workflow treats the EMR as the source of truth. If availability search returns no slots, the assistant does not invent alternatives. If a booking receives a conflict, it explains that the selected time is no longer available and searches again. If the EMR is unavailable or a request cannot be safely completed, the assistant asks for staff assistance instead of guessing or claiming a completed action.

Rescheduling is handled in backend code as a composite operation because the EMR does not provide a single reschedule endpoint. The backend books the replacement appointment first, then cancels the original. If the replacement cannot be booked, the original appointment stays unchanged. If cancelling the original fails after a successful replacement booking, the backend attempts to cancel the replacement as compensation. If it cannot safely reconcile the two appointments, it returns a human-assistance outcome rather than an inaccurate confirmation. When a caller does not request a new appointment type, the original type is preserved.

The voice prompt is designed for a phone call rather than a chat interface. It asks one question at a time, uses short sentences, and presents no more than three appointment options. Request-start filler messages such as "Let me check that for you" avoid silence while tools wait on the EMR. The prompt also avoids medical, insurance, pricing, and payment advice. Emergency symptoms stop routine scheduling and direct the caller to emergency services.

## Verification And Deferred Work

The automated test suite covers Vapi payload handling, authentication, patient workflows, scheduling, cancellation, rescheduling, logging, and the live-test data generator. `48` tests pass. The public webhook was also exercised against the sandbox for registration, provider lookup, slot search, booking, rescheduling, and cancellation, with appointment changes checked directly in the EMR.

Native Vapi call transfer is intentionally deferred. A transfer needs a real front-desk E.164 destination and operating hours, neither of which was supplied. The assistant therefore gives a clear staff-assistance response without saying that a transfer occurred. With more time, I would add a configured transfer destination and business-hours policy, move in-memory idempotency records to Redis or Postgres, use managed HTTPS rather than a development tunnel, and add operational metrics for EMR latency, tool failures, slot conflicts, and escalation rates.
