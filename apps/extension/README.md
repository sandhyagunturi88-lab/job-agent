# JobPilot UK Autofill (Chrome extension, Manifest V3)

Fills Greenhouse and Lever application forms from your **approved** Application
Pack. Every filled field is highlighted in blue, a toast reports what was
filled, and the extension **never touches the submit button** — that click is
always yours.

## What it fills

- **Contact details** (name, email, phone, location, LinkedIn, current
  company) — entered once in the popup's settings, stored in
  `chrome.storage.sync`, never sent anywhere except into the form you're
  looking at.
- **Custom questions** matched by label: notice period, salary expectation,
  right to work, sponsorship, "why this company" — from the pack's copy-ready
  answers. Yes/no dropdowns are answered from the answer text.
- **Tailored CV** attached as a `.txt` file to the resume upload where the
  widget accepts it (some don't — the pack screen's copy button is the
  fallback).
- Fields you've already typed into are **never overwritten**.

## Try it in 2 minutes (no ATS account needed)

Open `test-pages/greenhouse.html` or `test-pages/lever.html` in any browser
and press **▶ Test: fill with sample JobPilot pack**. These replicate the two
ATS form structures and load the real content scripts.

## Install for real use

1. `chrome://extensions` → enable *Developer mode* → *Load unpacked* → select
   `apps/extension`.
2. Click the JobPilot icon → *Your details & settings* → fill your contact
   details and the API URL (defaults to `http://localhost:8000` for dev; leave
   the token empty in dev mode).
3. Approve a CV in the JobPilot app so a pack exists, open the job's
   application page, click the icon — the pack auto-matches by URL (manual
   picker otherwise) — press **Fill this form**.
4. Review the highlighted fields, then press the employer's submit button
   yourself.

## Tests

`npm run test:extension` (from the repo root) runs the pure mapping logic
(label→answer matching, yes/no detection, URL→pack matching) under
`node --test`. DOM behaviour is covered by the fixture pages above.
