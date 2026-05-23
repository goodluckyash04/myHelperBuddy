/**
 * service-worker.js — myHelperBuddy PWA Service Worker
 *
 * FIXED: cache paths now match files that actually exist.
 * NEW:   FCM push event handler + notificationclick deep links.
 */

const CACHE_NAME = "mhb-pwa-v2";  //  bumped version to force cache refresh

// Only cache files that actually exist  // removed non-existent /static/js/script.js
const STATIC_URLS = [
  "/",
  "/static/css/style.css",
  "/static/icons/icon-192x192.png",
  "/static/icons/icon-512x512.png",
];

// ── Install: pre-cache known-good static assets ──────────────────────────────
self.addEventListener("install", (event) => {
  self.skipWaiting();  // Activate immediately — don't wait for old SW to die
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) =>
      // Use individual add calls so one missing file doesn't kill the whole install
      Promise.allSettled(STATIC_URLS.map((url) => cache.add(url)))
    )
  );
});

// ── Activate: remove stale caches ────────────────────────────────────────────
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((names) =>
      Promise.all(
        names
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      )
    ).then(() => self.clients.claim())  // Take control of existing pages immediately
  );
});

// ── Fetch: cache-first for static, network-first for API ─────────────────────
self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET and cross-origin requests
  if (request.method !== "GET" || url.origin !== self.location.origin) return;

  // Skip API / Django admin / auth endpoints — always go to network
  if (
    url.pathname.startsWith("/admin/") ||
    url.pathname.startsWith("/accounts/") ||
    url.pathname.startsWith("/fcm/") ||
    url.pathname.startsWith("/api/")
  ) return;

  // Cache-first strategy for static files
  if (url.pathname.startsWith("/static/")) {
    event.respondWith(
      caches.match(request).then((cached) => cached || fetch(request))
    );
    return;
  }

  // Network-first for pages (so content stays fresh)
  event.respondWith(
    fetch(request)
      .catch(() => caches.match(request))
  );
});

// ── Push: receive FCM push events  # NEW ─────────────────────────────────────
self.addEventListener("push", (event) => {
  let payload = {};
  try {
    payload = event.data ? event.data.json() : {};
  } catch (_) {
    payload = { notification: { title: "myHelperBuddy", body: event.data?.text() || "" } };
  }

  const notification = payload.notification || {};
  const data         = payload.data         || {};

  const title   = notification.title || "myHelperBuddy";
  const body    = notification.body  || "";
  const icon    = notification.icon  || "/static/icons/icon-192x192.png";
  const badge   = "/static/icons/icon-192x192.png";
  const tag     = data.type ? `mhb-${data.type}-${data.id || "0"}` : "mhb-push";
  const dataUrl = data.url  || "/dashboard/";

  event.waitUntil(
    self.registration.showNotification(title, {
      body,
      icon,
      badge,
      tag,
      data: { url: dataUrl },
      requireInteraction: false,
    })
  );
});

// ── Notification click: deep-link routing  # NEW ──────────────────────────────
self.addEventListener("notificationclick", (event) => {
  event.notification.close();

  const targetUrl = event.notification.data?.url || "/dashboard/";

  event.waitUntil(
    clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then((windowClients) => {
        // Focus existing tab if one already has the app open
        for (const client of windowClients) {
          if (client.url.includes(self.location.origin) && "focus" in client) {
            client.focus();
            client.navigate(targetUrl);
            return;
          }
        }
        // Otherwise open a new tab
        return clients.openWindow(targetUrl);
      })
  );
});
