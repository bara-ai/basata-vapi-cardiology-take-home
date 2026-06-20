# Basata Voice AI Take-Home Write-Up

This project delivers a Vapi scheduling assistant for Heartland Cardiology with a FastAPI webhook backend connected to the CardioChart Pro sandbox.

The assistant registers new patients, verifies existing patients using phone number and date of birth, finds providers and slots, and manages booking, cancellation, and rescheduling. The backend treats the EMR as the source of truth and requires explicit confirmation before appointment changes.

The configured Vapi assistant has eight function tools and is assigned to `+1 601 419 9125`. The public webhook was tested with the sandbox for registration, provider lookup, slot search, booking, rescheduling, and cancellation. Rescheduling books the replacement before cancelling the original and preserves the appointment type when no new type is requested.

The remaining external dependency is a front-desk E.164 number and operating hours for native transfer. Until they are available, unsupported or failed requests use a staff-assistance response without claiming that a call transfer occurred.
