// Lever application forms (jobs.lever.co / jobs.eu.lever.co). Fills contact
// details, the additional-information box, mapped custom question cards, and
// attaches the tailored CV. Never submits.

function jpFillLever(payload) {
  const { pack, contact } = payload;
  let filled = 0;
  const byName = (n) => document.querySelector(`input[name="${n}"], textarea[name="${n}"]`);

  if (jpFill(byName("name"), contact.full_name)) filled += 1;
  if (jpFill(byName("email"), contact.email)) filled += 1;
  if (jpFill(byName("phone"), contact.phone)) filled += 1;
  if (jpFill(byName("location"), contact.location)) filled += 1;
  if (jpFill(byName("org"), contact.current_company)) filled += 1;
  if (jpFill(byName("urls[LinkedIn]"), contact.linkedin)) filled += 1;

  // "Additional information" — the natural home for the why-this-company answer
  const comments = byName("comments");
  if (comments && jpFill(comments, jpAnswerFor(pack, "why_this_company"))) filled += 1;

  // custom question cards: name="cards[<uuid>][field0]" with a nearby label
  filled += jpFillCustomQuestions(document, pack);

  const attached = jpAttachCv(
    document.querySelector('input[name="resume"], input[type="file"]'),
    `CV - ${pack.job_title || pack.job_id}.txt`,
    pack.tailored_cv && pack.tailored_cv.full_text,
  );

  return { filled, attached };
}

if (typeof chrome !== "undefined" && chrome.runtime && chrome.runtime.onMessage) {
  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (msg && msg.type === "JP_FILL") {
      const result = jpFillLever(msg.payload);
      jpToast(
        `JobPilot filled ${result.filled} field${result.filled === 1 ? "" : "s"}` +
          (result.attached ? " and attached your tailored CV" : "") +
          " — review everything, then press submit yourself.",
      );
      sendResponse(result);
    }
  });
}
