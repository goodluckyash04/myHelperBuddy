/**
 * firebase-messaging-sw.js — FCM Background Message Handler
 *
 * NEW FILE: Required by Firebase Cloud Messaging spec.
 * Must be served from domain root ("/firebase-messaging-sw.js").
 *
 * This file uses the compat SDK (importScripts) because ESM modules
 * are not available in all service worker contexts.
 *
 * Serving: add a URL pattern in urls.py that serves this file from /static/
 * with the path /firebase-messaging-sw.js (handled in mysite/urls.py or
 * via the static serve path set in accounts/urls.py).
 */

// Firebase compat SDK — must use importScripts in SW context
importScripts("https://www.gstatic.com/firebasejs/10.12.2/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/10.12.2/firebase-messaging-compat.js");

// Parse credentials passed from the frontend registration URL
const urlParams = new URLSearchParams(location.search);
const apiKey = urlParams.get("apiKey") || "";
const appId = urlParams.get("appId") || "";
const senderId = urlParams.get("senderId") || "";

// Firebase project config — must match what's in index.html
firebase.initializeApp({
  apiKey:            apiKey,
  authDomain:        "myhelperbuddy-04.firebaseapp.com",
  projectId:         "myhelperbuddy-04",
  storageBucket:     "myhelperbuddy-04.appspot.com",
  messagingSenderId: senderId,
  appId:             appId,
});

const messaging = firebase.messaging();

// ── Lifecycle: force immediate activation ─────────────────────────────
self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(clients.claim());
});

// ── Background message handler ────────────────────────────────────────
messaging.onBackgroundMessage((payload) => {
  console.log("[Firebase SW] Background message received:", payload);

  const notification = payload.notification || {};
  const data         = payload.data         || {};

  const title   = notification.title || "myHelperBuddy";
  const body    = notification.body  || "";
  const icon    = notification.icon  || "/static/icons/icon-192x192.png";
  const dataUrl = data.url           || "/dashboard/";

  // Deduplicate notifications using the FCM data type + id
  const tag = data.type ? `mhb-${data.type}-${data.id || "0"}` : "mhb-fcm";

  self.registration.showNotification(title, {
    body,
    icon,
    badge: "/static/icons/icon-192x192.png",
    tag,
    data: { url: dataUrl },
    requireInteraction: false,
    vibrate: [200, 100, 200],
  });
});

// ── Notification click: deep-link routing ──────────────────────────────
self.addEventListener("notificationclick", (event) => {
  event.notification.close();

  const notifData = event.notification.data || {};
  let targetUrl = notifData.url || "/dashboard/";

  // Support explicit deep links from the data payload
  // Expected data keys: type ("reminder"|"task"|"ledger"), id
  if (notifData.type && notifData.id) {
    switch (notifData.type) {
      case "reminder":
        targetUrl = `/view-reminder/`;
        break;
      case "task":
        targetUrl = `/taskReports/`;
        break;
      case "ledger":
        targetUrl = `/ledger-transaction-details/`;
        break;
      default:
        targetUrl = notifData.url || "/dashboard/";
    }
  }

  event.waitUntil(
    clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then((windowClients) => {
        for (const client of windowClients) {
          if ("focus" in client) {
            client.focus();
            client.navigate(targetUrl);
            return;
          }
        }
        return clients.openWindow(targetUrl);
      })
  );
});
