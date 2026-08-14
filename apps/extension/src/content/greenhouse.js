// Greenhouse application forms — classic (boards.greenhouse.io, id-based
// fields) and the newer React boards (job-boards.greenhouse.io, name/aria
// based). Fills contact details, cover letter, mapped custom questions, and
// attaches the tailored CV. Never submits.

function jpFillGreenhouse(payload) {
  const { pack, contact } = payload;
  const name = jpSplitName(contact.full_name || "");
  let filled = 0;
  const byIdOrName = (key) =>
    document.getElementById(key) || document.querySelector(`input[name="${key}"]`);

  if (jpFill(byIdOrName("first_name"), name.first)) filled += 1;
  if (jpFill(byIdOrName("last_name"), name.last)) filled += 1;
  if (jpFill(byIdOrName("email"), contact.email)) filled += 1;
  if (jpFill(byIdOrName("phone"), contact.phone)) filled += 1;
  if (
    jpFill(
      document.querySelector(
        '#job_application_location, input[name="job_application[location]"], input[autocomplete="address-level2"]',
      ),
      contact.location,
    )
  )
    filled += 1;

  // LinkedIn lives in Greenhouse's custom-question block; match by label
  const linkedin = [...document.querySelectorAll("input")].find((el) =>
    /linkedin/i.test(jpLabelText(el)),
  );
  if (linkedin && !linkedin.value && jpFill(linkedin, contact.linkedin)) filled += 1;

  const coverLetter = document.querySelector(
    '#cover_letter_text, textarea[name="cover_letter_text"], textarea[name="cover_letter"]',
  );
  if (coverLetter && jpFill(coverLetter, jpAnswerFor(pack, "why_this_company"))) filled += 1;

  filled += jpFillCustomQuestions(document, pack);

  const resumeInput = [...document.querySelectorAll('input[type="file"]')].find((el) =>
    /resume|cv/i.test(el.name + " " + el.id + " " + jpLabelText(el)),
  );
  const attached = jpAttachCv(
    resumeInput,
    `CV - ${pack.job_title || pack.job_id}.txt`,
    pack.tailored_cv && pack.tailored_cv.full_text,
  );

  return { filled, attached };
}

if (typeof chrome !== "undefined" && chrome.runtime && chrome.runtime.onMessage) {
  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (msg && msg.type === "JP_FILL") {
      const result = jpFillGreenhouse(msg.payload);
      jpToast(
        `JobPilot filled ${result.filled} field${result.filled === 1 ? "" : "s"}` +
          (result.attached ? " and attached your tailored CV" : "") +
          " — review everything, then press submit yourself.",
      );
      sendResponse(result);
    }
  });
}
