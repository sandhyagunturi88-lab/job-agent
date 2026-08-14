// Lever application forms (jobs.lever.co). Phase 5 implements full mapping.
chrome.storage.local.get("applicationPack", ({ applicationPack }) => {
  if (!applicationPack) return;
  jpFill(document.querySelector('input[name="name"]'), applicationPack.full_name);
  jpFill(document.querySelector('input[name="email"]'), applicationPack.email);
});
