// Greenhouse application forms (boards.greenhouse.io / job-boards.greenhouse.io).
// Phase 5 implements full mapping (name/email/phone/CV upload/custom questions)
// from the Application Pack delivered by the background worker.
chrome.storage.local.get("applicationPack", ({ applicationPack }) => {
  if (!applicationPack) return;
  jpFill(document.querySelector("#first_name"), applicationPack.first_name);
  jpFill(document.querySelector("#last_name"), applicationPack.last_name);
  jpFill(document.querySelector("#email"), applicationPack.email);
});
