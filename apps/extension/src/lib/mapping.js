// Pure mapping logic shared by the content scripts and the popup, and unit
// tested with `node --test` (no DOM here — DOM interaction lives in
// content/common.js). Loaded first in every content-script bundle.

/** Map a form label's text to a CopyAnswer field name, or null. */
function jpAnswerField(labelText) {
  const t = (labelText || "").toLowerCase();
  if (!t) return null;
  if (/\bnotice\b/.test(t)) return "notice_period";
  if (/salary|compensation|remuneration|pay expectation|day rate/.test(t))
    return "salary_expectation";
  if (/right to work|eligible to work|authori[sz]ed to work|work authori[sz]ation/.test(t))
    return "right_to_work";
  if (/sponsor|visa/.test(t)) return "sponsorship";
  if (/why (do you want|are you interested|this (company|role|job))|motivat|cover letter/.test(t))
    return "why_this_company";
  return null;
}

/** "Yes — full right to work in the UK" → "yes"; "No sponsorship required" → "no". */
function jpYesNo(answerText) {
  const t = (answerText || "").trim().toLowerCase();
  if (t.startsWith("yes")) return "yes";
  if (t.startsWith("no")) return "no";
  return null;
}

/** "Jane Anne Doe" → { first: "Jane", last: "Anne Doe" } (single names: last=""). */
function jpSplitName(fullName) {
  const parts = (fullName || "").trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return { first: "", last: "" };
  return { first: parts[0], last: parts.slice(1).join(" ") };
}

const jpSlug = (s) =>
  (s || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");

/**
 * Pick the Application Pack row that matches the tab the user has open.
 * Scoring: exact apply_url prefix (3) > same host + company slug in path (2)
 * > same host (1). Returns null if nothing scores — the popup then offers a
 * manual picker instead of guessing.
 */
function jpMatchPack(tabUrl, rows) {
  let best = null;
  let bestScore = 0;
  let url;
  try {
    url = new URL(tabUrl);
  } catch {
    return null;
  }
  for (const row of rows || []) {
    let score = 0;
    try {
      const apply = new URL(row.apply_url);
      if (tabUrl.startsWith(apply.origin + apply.pathname)) score = 3;
      else if (apply.host === url.host) {
        const slug = jpSlug(row.company);
        score = slug && url.pathname.toLowerCase().includes(slug) ? 2 : 1;
      }
    } catch {
      continue;
    }
    if (score > bestScore) {
      best = row;
      bestScore = score;
    }
  }
  return best;
}

/** The pack answer for a CopyAnswer field name, or null. */
function jpAnswerFor(pack, field) {
  const answer = ((pack && pack.answers) || []).find((a) => a.field === field);
  return answer ? answer.text : null;
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { jpAnswerField, jpYesNo, jpSplitName, jpMatchPack, jpAnswerFor, jpSlug };
}
