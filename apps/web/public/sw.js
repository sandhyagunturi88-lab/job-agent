// Minimal service worker: makes the app installable. Phase 4 adds an offline
// shell + cached Application Packs so answers are copyable without signal.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));
self.addEventListener("fetch", () => {});
