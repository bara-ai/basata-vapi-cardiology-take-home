# Basata Exercise Write-Up

## What I Built

I made Baseet, a voice assistant for Heartland Cardiology. It is connected to a FastAPI backend and the CardioChart Pro sandbox EMR. The assistant is in the Interview Sandbox as [Heartland Cardiology](https://dashboard.vapi.ai/assistants/9ca91034-3de4-44be-bba6-5aa756128d64?tab=assistant). The phone number is `+1 601 419 9125`.

The assistant can register a new patient and find an existing patient and find providers and available slots and book appointments and look up appointments and cancel appointments and reschedule appointments.

## How It Works

The caller talks with the Vapi assistant. The assistant follows the system prompt and asks the needed questions one by one. When it needs real information it calls one of the Vapi tools.

The tool request goes to the FastAPI webhook. The backend checks the request and then calls the EMR. The EMR returns the real patient data and provider data and appointment data. The backend sends the result back to Vapi and then Vapi can continue the call.

The EMR is the source of truth. The assistant does not create provider names or available times or appointment confirmations by itself. It only confirms an action after the EMR returns a successful result.

There are eight tools. They are for patient verification and registration and provider lookup and slot search and appointment lookup and booking and cancellation and rescheduling.

## Important Choices

For an existing patient the assistant asks for the phone number on the record and the date of birth. The backend checks both values before it shows appointments or changes an appointment. This helps prevent another person from seeing or changing patient information.

For a new patient the assistant asks for first name and last name and date of birth and phone number. Email and insurance information are optional because the EMR allows them to be optional. Before creating the record the assistant reads the details back and asks the caller to confirm. The backend also checks for an existing phone number before it creates a new patient.

Before booking or cancelling or rescheduling the assistant repeats the important details and asks for a clear confirmation. This is important because a phone call can have speech errors or misunderstanding. The backend does not say that an appointment is booked or cancelled or changed until the EMR confirms it.

## Failure Cases

If there are no slots then the assistant does not make up another time. If a selected slot is no longer available then the EMR returns a conflict and the assistant can search again. If the EMR is not available then the assistant asks for staff help and does not guess the result.

Rescheduling has more than one step. The system first tries to book the replacement appointment and then cancels the old appointment. If the new appointment cannot be booked then the old appointment stays unchanged. If the old appointment cannot be cancelled after the new one is booked then the backend tries to cancel the new appointment again. If the system cannot fix this safely then it asks for staff help. When the caller does not ask to change the appointment type then the old type stays the same.

The backend has retry protection for booking and other changes. This helps prevent a repeated Vapi request from creating the same action twice during the demo. The scheduling tools stay synchronous because the assistant needs the current EMR result before it can continue the same call. The retry protection uses the Vapi `toolCallId` and keeps the result in memory for the demo. For production this should be stored in Redis or Postgres.

## Voice Design

This is made for phone calls and not chat. The assistant uses short sentences and asks one question at a time. It gives no more than three appointment choices. It also uses short filler messages while it waits for the tool result so the caller does not stay in silence.

The assistant does not give medical advice or insurance advice or pricing advice. If the caller describes an emergency then it tells the caller to use emergency services and it stops normal scheduling.

## Backend Implementation Details

The Vapi payload normalizer changes the different Vapi tool call formats into one internal request shape. This includes the tool call ID and tool name and arguments and call ID and caller phone number. Some requests have arguments as a JSON string and some already have a dictionary. The normalizer handles this once so the service code does not need to care about Vapi payload differences.

The patient service uses `find_verified_patient` to check the phone number and date of birth before it returns a verified patient. It normalizes phone digits first so different phone formats can match the same record. `register_patient` also checks for an existing phone number before creating a new patient. `list_verified_appointments` verifies the patient again before reading appointment data and cancelled appointments stay hidden unless the caller asks for cancelled history.

The scheduling service uses `list_providers` and `search_slots` to get provider and slot data from the EMR. `list_providers` can filter providers by specialty or appointment type and it returns a simple provider structure for the assistant. `search_slots` uses a default range from today until two weeks later when the caller does not give dates and it limits the returned slots. `book_appointment` verifies the patient again because booking changes EMR data and it maps an EMR slot conflict to a clear conflict result.

The appointment service uses `cancel_appointment` to check confirmation and patient ownership before cancellation. It will not cancel an appointment that is already cancelled or not scheduled. `reschedule_appointment` is kept in the backend as one controlled workflow so the assistant does not have to make two separate mutation decisions. It books the replacement first and then cancels the old appointment and it tries compensation when the second step fails.

The tool dispatcher is the routing layer between Vapi and the services. It validates the tool name and required arguments and calls the correct patient or scheduling or appointment function. EMR HTTP errors become an `emr_unavailable` result instead of an unhandled backend failure.

The FastAPI application has a health endpoint and the authenticated Vapi webhook endpoint. It creates a shared EMR client during the application lifecycle and closes it on shutdown. The webhook checks the Vapi Bearer secret with a constant time comparison and it logs outcomes with sensitive fields removed. Phone number and date of birth and email and insurance member ID and transcript fields are redacted from logs.

The automated tests are grouped by the main boundaries of the project. They check the application health and webhook authentication and Vapi payload formats and log redaction and EMR client requests. They also check patient registration and verification and provider and slot search and booking and cancellation and rescheduling and live verification script behavior. This gives evidence for both normal workflows and the important failure cases.
