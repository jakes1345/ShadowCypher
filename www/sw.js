// ShadowCypher service worker
// - Caches the shell for offline-friendly UX
// - Handles web-push events (delivers Guardian incident notifications)
// - Click-through navigates the user to the relevant dashboard page

const CACHE = "shadowcypher-v2";
const SHELL = ["/", "/index.html", "/styles.css", "/manifest.json"];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(SHELL).catch(() => null)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

// Network-first for HTML, cache-first for static assets
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== self.location.origin) return;
  // Don't intercept API calls — always go to the network
  if (url.pathname.startsWith("/v1/") || url.host.includes("workers.dev")) return;

  if (e.request.mode === "navigate") {
    e.respondWith(
      fetch(e.request).catch(() => caches.match("/index.html"))
    );
    return;
  }
  e.respondWith(
    caches.match(e.request).then((cached) => cached || fetch(e.request))
  );
});

// ─── Web Push ───────────────────────────────────────────────────────────────
self.addEventListener("push", (event) => {
  let data = { title: "ShadowCypher", body: "New event", url: "/?nav=account" };
  try { if (event.data) data = { ...data, ...event.data.json() }; } catch (e) {}
  const options = {
    body: data.body,
    icon: "/icon-192.png",
    badge: "/icon-192.png",
    tag: data.tag || "shadowcypher-event",
    data: { url: data.url || "/?nav=account" },
    requireInteraction: data.severity === "critical",
  };
  event.waitUntil(self.registration.showNotification(data.title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const rawUrl = event.notification.data?.url || "/?nav=account";
  const safeUrl = (() => {
    try {
      const parsed = new URL(rawUrl, self.location.origin);
      return parsed.origin === self.location.origin ? parsed.href : "/?nav=account";
    } catch { return "/?nav=account"; }
  })();
  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then((list) => {
      const focused = list.find((c) => c.url.includes(self.location.origin));
      if (focused) { focused.focus(); focused.navigate(safeUrl); return; }
      return clients.openWindow(safeUrl);
    })
  );
});
