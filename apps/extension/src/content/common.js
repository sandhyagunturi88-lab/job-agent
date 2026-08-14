// Shared autofill helpers. NEVER submits a form — filling + highlighting only;
// the user always presses the submit button themselves.

function jpFill(input, value) {
  if (!input || value == null) return false;
  input.focus();
  input.value = value;
  input.dispatchEvent(new Event("input", { bubbles: true }));
  input.dispatchEvent(new Event("change", { bubbles: true }));
  input.style.outline = "2px solid #1d4ed8"; // highlight what JobPilot filled
  input.style.outlineOffset = "1px";
  return true;
}

// eslint-disable-next-line no-unused-vars
function jpAnswerFor(pack, field) {
  const answer = (pack.answers || []).find((a) => a.field === field);
  return answer ? answer.text : null;
}
