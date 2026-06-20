# Live Test Notes

## Shared Sandbox Policy

- Do not call the EMR administrative reset endpoint.
- Use `python -m scripts.live_emr_verification` for each live run.
- Every run creates a distinct synthetic patient name and reserved `+1555...` phone number.
- Created synthetic patient and appointment records remain in the shared sandbox.
- Record only run IDs, EMR IDs, status values, and timestamps. Do not record names, phone numbers, dates of birth, bearer secrets, transcripts, or raw request payloads.


- No-reset run `20260620T191828Z-10978307`: patient `pat_079d7d32`, appointment `apt_3a963ae5`, status `scheduled`.


- No-reset run `20260620T191833Z-2ba57767`: patient `pat_7688673d`, appointment `apt_5a0ddb53`, status `scheduled`.
