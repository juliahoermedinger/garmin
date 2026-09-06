function urlBase64ToUint8Array(base64String) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

async function enablePushNotifications() {
  const statusEl = document.getElementById("push-status");
  try {
    if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
      statusEl.textContent = "Push notifications are not supported in this browser.";
      return;
    }

    const reg = await navigator.serviceWorker.register("/sw.js");
    const permission = await Notification.requestPermission();
    if (permission !== "granted") {
      statusEl.textContent = "Notification permission was not granted.";
      return;
    }

    const keyResp = await fetch("/push/public-key");
    if (!keyResp.ok) {
      statusEl.textContent = "Push notifications are not configured on the server.";
      return;
    }
    const { publicKey } = await keyResp.json();

    let sub = await reg.pushManager.getSubscription();
    if (!sub) {
      sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(publicKey),
      });
    }

    await fetch("/push/subscribe", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(sub.toJSON()),
    });

    statusEl.textContent = "Notifications enabled on this device.";
  } catch (err) {
    statusEl.textContent = "Could not enable notifications: " + err.message;
  }
}

async function disablePushNotifications() {
  const statusEl = document.getElementById("push-status");
  try {
    const reg = await navigator.serviceWorker.getRegistration();
    const sub = reg && (await reg.pushManager.getSubscription());
    if (sub) {
      await fetch("/push/unsubscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ endpoint: sub.endpoint }),
      });
      await sub.unsubscribe();
    }
    statusEl.textContent = "Notifications disabled on this device.";
  } catch (err) {
    statusEl.textContent = "Could not disable notifications: " + err.message;
  }
}
