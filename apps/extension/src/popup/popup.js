// Phase 5: show the pack matched to the active tab and a "Fill this form" button.
chrome.storage.local.get("applicationPack", ({ applicationPack }) => {
  if (applicationPack) {
    document.getElementById("status").textContent =
      "Application Pack loaded for " + (applicationPack.job_id || "current job");
  }
});
