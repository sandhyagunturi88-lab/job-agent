// Shared DOM fill helpers. HARD RULE: nothing in this file (or any content
// script) ever submits a form, clicks a submit button, or triggers form
// submission — filling + highlighting only; the user always presses submit.

const JP_HIGHLIGHT = "2px solid #1d4ed8";

function jpFill(input, value) {
  if (!input || value == null || value === "") return false;
  // React-controlled inputs (job-boards.greenhouse.io) ignore plain .value =
  // assignment, so go through the native setter before dispatching events.
  const proto =
    input instanceof HTMLTextAreaElement
      ? HTMLTextAreaElement.prototype
      : HTMLInputElement.prototype;
  const setter = Object.getOwnPropertyDescriptor(proto, "value");
  if (setter && setter.set) setter.set.call(input, value);
  else input.value = value;
  input.dispatchEvent(new Event("input", { bubbles: true }));
  input.dispatchEvent(new Event("change", { bubbles: true }));
  input.style.outline = JP_HIGHLIGHT;
  input.style.outlineOffset = "1px";
  return true;
}

/** Select the option whose text matches yes/no (for right-to-work style questions). */
function jpSelectYesNo(select, yesNo) {
  if (!select || !yesNo) return false;
  for (const option of select.options) {
    if (option.text.trim().toLowerCase().startsWith(yesNo)) {
      select.value = option.value;
      select.dispatchEvent(new Event("change", { bubbles: true }));
      select.style.outline = JP_HIGHLIGHT;
      return true;
    }
  }
  return false;
}

/** Attach the tailored CV as a plain-text file to a resume file input. */
function jpAttachCv(fileInput, filename, text) {
  if (!fileInput || !text) return false;
  try {
    const dt = new DataTransfer();
    dt.items.add(new File([text], filename, { type: "text/plain" }));
    fileInput.files = dt.files;
    fileInput.dispatchEvent(new Event("change", { bubbles: true }));
    fileInput.style.outline = JP_HIGHLIGHT;
    return true;
  } catch {
    return false; // some upload widgets reject synthetic files — copy path still works
  }
}

/** Human-readable label for a form control, from whatever the ATS provides. */
function jpLabelText(el) {
  if (!el) return "";
  const aria = el.getAttribute("aria-label");
  if (aria) return aria;
  if (el.id) {
    const label = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
    if (label) return label.textContent || "";
  }
  const wrapping = el.closest("label");
  if (wrapping) return wrapping.textContent || "";
  const container = el.closest(".field, .application-question, li, fieldset, div");
  const near = container && container.querySelector("label, legend, .text, .application-label");
  return near ? near.textContent || "" : "";
}

/**
 * Fill every unanswered custom question whose label maps to a pack answer.
 * Returns the number of fields filled.
 */
function jpFillCustomQuestions(root, pack) {
  let filled = 0;
  const controls = root.querySelectorAll(
    'input[type="text"], input:not([type]), textarea, select',
  );
  for (const el of controls) {
    if (el.value) continue; // never overwrite something the user already typed
    const field = jpAnswerField(jpLabelText(el));
    if (!field) continue;
    const answer = jpAnswerFor(pack, field);
    if (!answer) continue;
    if (el instanceof HTMLSelectElement) {
      if (jpSelectYesNo(el, jpYesNo(answer))) filled += 1;
    } else if (jpFill(el, answer)) {
      filled += 1;
    }
  }
  return filled;
}

/** In-page confirmation toast. Static (no animation) — motion-safe by default. */
function jpToast(message) {
  const existing = document.getElementById("jp-toast");
  if (existing) existing.remove();
  const el = document.createElement("div");
  el.id = "jp-toast";
  el.setAttribute("role", "status");
  el.setAttribute("aria-live", "polite");
  el.textContent = message;
  el.style.cssText =
    "position:fixed;left:50%;bottom:24px;transform:translateX(-50%);" +
    "background:#1e40af;color:#fff;padding:10px 16px;border-radius:10px;" +
    "font:13px system-ui,sans-serif;z-index:2147483647;box-shadow:0 4px 12px rgba(0,0,0,.25);" +
    "max-width:90vw;text-align:center;";
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 6000);
}
