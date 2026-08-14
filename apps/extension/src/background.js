// Phase 5: fetch the user's Application Packs from the API (Supabase session)
// and hand the matching pack to the content script for the current tab.
chrome.runtime.onInstalled.addListener(() => {
  console.log("JobPilot UK Autofill installed");
});
