# Basata Voice AI Take-Home Write-Up

## What I Built

I made a Vapi voice assistant for Heartland Cardiology. It is connected to a FastAPI backend and the CardioChart Pro sandbox EMR. The assistant is in the Interview Sandbox as [Heartland Cardiology](https://dashboard.vapi.ai/assistants/9ca91034-3de4-44be-bba6-5aa756128d64?tab=assistant). The phone number is `+1 601 419 9125`.

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

The backend also has retry protection for booking and other changes. This helps prevent a repeated Vapi request from creating the same action twice during the demo.

Vapi can send a tool request in different payload shapes. The backend changes these shapes into one internal tool request before it starts the workflow. The scheduling tools stay synchronous because the assistant needs the current EMR result before it can continue the same call. The retry protection uses the Vapi `toolCallId` and keeps the result in memory for the demo. For production this should be stored in Redis or Postgres.

## Voice Design

This is made for phone calls and not chat. The assistant uses short sentences and asks one question at a time. It gives no more than three appointment choices. It also uses short filler messages while it waits for the tool result so the caller does not stay in silence.

The assistant does not give medical advice or insurance advice or pricing advice. If the caller describes an emergency then it tells the caller to use emergency services and it stops normal scheduling.

## Testing And Deferred Work

The project has `48` automated tests. They cover Vapi request formats and authentication and patient workflows and booking and cancellation and rescheduling and error cases. The public webhook was also tested with the sandbox EMR for registration and provider lookup and slot search and booking and rescheduling and cancellation.

Native Vapi call transfer is not added yet. A real front desk phone number and business hours were not provided. The assistant says that clinic staff need to help but it does not say that the caller was transferred.

With more time I would use Redis or Postgres for retry protection and use managed deployment instead of a development tunnel. I would also add more monitoring for EMR failures and tool latency and slot conflicts and staff help requests.
