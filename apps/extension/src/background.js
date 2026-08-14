// MV3 service worker. Deliberately minimal: the popup talks to the JobPilot
// API directly (host_permissions cover it) and hands packs to the content
// scripts via tab messages — no background state to go stale.
chrome.runtime.onInstalled.addListener(() => {
  console.log("JobPilot UK Autofill installed");
});
