 from flask import Flask, request, jsonify, render_template_string
import os
import json

import firebase_admin
from firebase_admin import credentials, messaging


app = Flask(__name__)


# =========================================================
# FIREBASE ADMIN SETUP
# =========================================================

firebase_ready = False

try:
    firebase_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT")

    if firebase_json:
        service_account = json.loads(firebase_json)
        cred = credentials.Certificate(service_account)

        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)

        firebase_ready = True
        print("Firebase Admin connected.")
    else:
        print("FIREBASE_SERVICE_ACCOUNT not found.")

except Exception as e:
    print("Firebase setup error:", e)


# =========================================================
# DATA
# =========================================================

owner = {
    "name": "",
    "phone": "",
    "email": "",
    "location": "",
    "device_id": ""
}

# Multiple phones/computers can be registered.
fcm_tokens = set()

fire_status = {
    "fire": False,
    "flame": "NOT DETECTED",
    "temperature": 0,
    "extinguisher": "READY",
    "notification_sent": False
}


# =========================================================
# NOTIFICATION FUNCTIONS
# =========================================================

def send_notification(token, title, body, notification_type="fire_alert"):
    """Send an FCM notification to one device."""

    if not firebase_ready:
        print("Firebase is not ready.")
        return False

    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body
            ),
            data={
                "type": notification_type,
                "message": body
            },
            token=token
        )

        messaging.send(message)
        print("Notification sent.")
        return True

    except Exception as e:
        print("Notification error:", e)

        # Remove invalid/expired token.
        fcm_tokens.discard(token)

        return False


def send_fire_to_all_devices():
    """Send fire alert to every registered device."""

    if not fcm_tokens:
        print("No registered FCM devices.")
        return False

    success = False

    for token in list(fcm_tokens):
        result = send_notification(
            token,
            "🔥 FIRE ALERT!",
            "Smart Fire Guard detected a possible fire.",
            "fire_alert"
        )

        if result:
            success = True

    return success


# =========================================================
# FIREBASE SERVICE WORKER
# =========================================================

@app.route("/firebase-messaging-sw.js")
def firebase_service_worker():

    worker = """
importScripts(
  "https://www.gstatic.com/firebasejs/10.13.2/firebase-app-compat.js"
);

importScripts(
  "https://www.gstatic.com/firebasejs/10.13.2/firebase-messaging-compat.js"
);

firebase.initializeApp({
  apiKey: "AIzaSyD1JM4e0Ztg3FUhCkA4tYh8UzEOYcdn9k",
  authDomain: "smart-fire-project.firebaseapp.com",
  projectId: "smart-fire-project",
  storageBucket: "smart-fire-project.firebasestorage.app",
  messagingSenderId: "591246962485",
  appId: "1:591246962485:web:2030ebe6c34a81f5bd667c"
});

const messaging = firebase.messaging();

messaging.onBackgroundMessage(function(payload) {

  const title =
    payload.notification?.title || "🔥 Smart Fire Guard";

  const options = {
    body:
      payload.notification?.body ||
      "Fire alert received.",
    tag: "smart-fire-alert"
  };

  self.registration.showNotification(title, options);
});
"""

    return worker, 200, {
        "Content-Type": "application/javascript"
    }


# =========================================================
# MAIN WEBSITE
# =========================================================

HTML = r"""
<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>Smart Fire Guard</title>

<script src="https://www.gstatic.com/firebasejs/10.13.2/firebase-app-compat.js"></script>

<script src="https://www.gstatic.com/firebasejs/10.13.2/firebase-messaging-compat.js"></script>


<style>

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family: Arial, sans-serif;
    background:
        radial-gradient(circle at top left, #182848, #080b16 55%);
    color: #ffffff;
    min-height: 100vh;
    line-height: 1.25;
}

.container {
    width: 92%;
    max-width: 1050px;
    margin: auto;
}

header {
    padding: 14px 0;
    border-bottom: 1px solid rgba(255,255,255,0.08);
}

.nav {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 10px;
}

.logo {
    font-size: 20px;
    font-weight: 800;
}

.logo span {
    color: #ff5b35;
}

.online {
    font-size: 12px;
    color: #6dff9a;
    display: flex;
    align-items: center;
    gap: 5px;
}

.dot {
    width: 8px;
    height: 8px;
    background: #37e878;
    border-radius: 50%;
}

.page {
    padding: 25px 0;
}

.hero {
    text-align: center;
    margin-bottom: 20px;
}

.hero-icon {
    font-size: 45px;
    margin-bottom: 5px;
}

.hero h1 {
    font-size: 29px;
    margin-bottom: 5px;
}

.hero p {
    color: #9ca8bd;
    font-size: 13px;
}

.card {
    background: rgba(18, 24, 42, 0.86);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 15px;
    padding: 17px;
    margin-bottom: 14px;
    box-shadow: 0 10px 35px rgba(0,0,0,0.25);
}

.card h2 {
    font-size: 17px;
    margin-bottom: 12px;
}

.form-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
}

.input-group {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.input-group.full {
    grid-column: 1 / -1;
}

label {
    font-size: 11px;
    color: #9ca8bd;
}

input {
    width: 100%;
    padding: 10px;
    border-radius: 9px;
    border: 1px solid #30394f;
    background: #0d1322;
    color: white;
    outline: none;
    font-size: 13px;
}

input:focus {
    border-color: #ff5b35;
}

button {
    border: 0;
    border-radius: 9px;
    padding: 10px 15px;
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
}

.primary {
    background: #ff5636;
    color: white;
}

.primary:hover {
    background: #ff704f;
}

.secondary {
    background: #202b42;
    color: white;
}

.danger {
    background: #7e2430;
    color: white;
}

.buttons {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-top: 13px;
}

.status-main {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 10px;
    padding: 13px;
    border-radius: 11px;
    background: #0d1322;
    margin-bottom: 12px;
}

.status-title {
    font-size: 16px;
    font-weight: 800;
}

.status-text {
    font-size: 11px;
    color: #8f9ab0;
    margin-top: 2px;
}

.badge {
    padding: 6px 9px;
    border-radius: 20px;
    font-size: 10px;
    font-weight: 800;
}

.safe {
    background: rgba(50,220,120,0.15);
    color: #5cff99;
}

.fire {
    background: rgba(255,70,50,0.18);
    color: #ff765e;
}

.grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 9px;
}

.stat {
    background: #0d1322;
    border-radius: 10px;
    padding: 11px;
}

.stat-icon {
    font-size: 19px;
}

.stat-name {
    color: #8f9ab0;
    font-size: 10px;
    margin-top: 4px;
}

.stat-value {
    font-size: 13px;
    font-weight: 700;
    margin-top: 3px;
}

.owner-box {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
}

.owner-item {
    background: #0d1322;
    padding: 10px;
    border-radius: 9px;
}

.owner-label {
    color: #8f9ab0;
    font-size: 10px;
}

.owner-value {
    font-size: 12px;
    margin-top: 3px;
    word-break: break-word;
}

.notice {
    padding: 10px;
    border-radius: 9px;
    background: rgba(255, 166, 0, 0.10);
    color: #ffc861;
    font-size: 11px;
    margin-top: 10px;
}

.success {
    padding: 10px;
    border-radius: 9px;
    background: rgba(50,220,120,0.10);
    color: #65f99b;
    font-size: 11px;
    margin-top: 10px;
}

.hidden {
    display: none !important;
}

footer {
    text-align: center;
    color: #69758c;
    font-size: 10px;
    padding: 10px 0 25px;
}

@media (max-width: 700px) {

    .form-grid {
        grid-template-columns: 1fr;
    }

    .input-group.full {
        grid-column: auto;
    }

    .grid {
        grid-template-columns: 1fr 1fr;
    }

    .owner-box {
        grid-template-columns: 1fr;
    }

    .hero h1 {
        font-size: 25px;
    }

    .page {
        padding-top: 18px;
    }
}

</style>

</head>


<body>


<header>

<div class="container nav">

<div class="logo">
🔥 SMART <span>FIRE GUARD</span>
</div>

<div class="online">
<div class="dot"></div>
ONLINE
</div>

</div>

</header>


<div class="container page">


<!-- =====================================================
     REGISTRATION
====================================================== -->

<section id="registration">

<div class="hero">

<div class="hero-icon">🛡️</div>

<h1>Protect Your Home</h1>

<p>
Register once to activate your Smart Fire Guard dashboard.
</p>

</div>


<div class="card">

<h2>👤 Owner Registration</h2>

<div class="form-grid">

<div class="input-group">

<label>Owner Name</label>

<input
id="name"
type="text"
placeholder="Enter your name"
>

</div>


<div class="input-group">

<label>Phone Number</label>

<input
id="phone"
type="tel"
placeholder="Enter phone number"
>

</div>


<div class="input-group">

<label>Email</label>

<input
id="email"
type="email"
placeholder="Enter email"
>

</div>


<div class="input-group">

<label>Location</label>

<input
id="location"
type="text"
placeholder="Home location"
>

</div>


<div class="input-group full">

<label>Device ID</label>

<input
id="device_id"
type="text"
placeholder="Example: HOME-001"
>

</div>

</div>


<div class="buttons">

<button
class="primary"
onclick="registerOwner()"
>
Register & Continue
</button>

</div>

<div id="registerMessage"></div>

</div>

</section>



<!-- =====================================================
     DASHBOARD
====================================================== -->

<section id="dashboard" class="hidden">


<div class="hero">

<div class="hero-icon">🔥</div>

<h1>Fire Guard Dashboard</h1>

<p>
Real-time protection monitoring
</p>

</div>


<!-- SYSTEM STATUS -->

<div class="card">

<h2>📊 System Status</h2>

<div class="status-main">

<div>

<div
id="statusTitle"
class="status-title"
>
System Safe
</div>

<div
id="statusText"
class="status-text"
>
No fire detected
</div>

</div>

<div
id="statusBadge"
class="badge safe"
>
SAFE
</div>

</div>


<div class="grid">


<div class="stat">

<div class="stat-icon">🔥</div>

<div class="stat-name">
Flame
</div>

<div
id="flame"
class="stat-value"
>
NOT DETECTED
</div>

</div>


<div class="stat">

<div class="stat-icon">🌡️</div>

<div class="stat-name">
Temperature
</div>

<div
id="temperature"
class="stat-value"
>
0 °C
</div>

</div>


<div class="stat">

<div class="stat-icon">🚿</div>

<div class="stat-name">
Extinguisher
</div>

<div
id="extinguisher"
class="stat-value"
>
READY
</div>

</div>


<div class="stat">

<div class="stat-icon">🔔</div>

<div class="stat-name">
Notification
</div>

<div
id="notification"
class="stat-value"
>
READY
</div>

</div>


</div>

</div>



<!-- OWNER -->

<div class="card">

<h2>👤 Registered Owner</h2>

<div class="owner-box">

<div class="owner-item">

<div class="owner-label">
NAME
</div>

<div
id="ownerName"
class="owner-value"
>
-
</div>

</div>


<div class="owner-item">

<div class="owner-label">
PHONE
</div>

<div
id="ownerPhone"
class="owner-value"
>
-
</div>

</div>


<div class="owner-item">

<div class="owner-label">
EMAIL
</div>

<div
id="ownerEmail"
class="owner-value"
>
-
</div>

</div>


<div class="owner-item">

<div class="owner-label">
LOCATION
</div>

<div
id="ownerLocation"
class="owner-value"
>
-
</div>

</div>


<div class="owner-item">

<div class="owner-label">
DEVICE ID
</div>

<div
id="ownerDevice"
class="owner-value"
>
-
</div>

</div>

</div>

</div>



<!-- ACTIONS -->

<div class="card">

<h2>⚡ Quick Actions</h2>

<div class="buttons">

<button
class="primary"
onclick="enableNotifications()"
>
🔔 Enable Notifications
</button>


<button
class="primary"
onclick="testFire()"
>
🔥 Test Fire
</button>


<button
class="secondary"
onclick="resetSystem()"
>
ↄ Reset
</button>


<button
class="danger"
onclick="changeOwner()"
>
✎ Change Owner
</button>

</div>


<div id="actionMessage"></div>

</div>


</section>


<footer>
Smart Fire Guard • School Competition Project
</footer>


</div>


<script>


// =========================================================
// FIREBASE CONFIG
// =========================================================

const firebaseConfig = {

    apiKey: "AIzaSyD1JM4e0Ztg3FUhCkA4tYh8UzEOYcdn9k",

    authDomain:
        "smart-fire-project.firebaseapp.com",

    projectId:
        "smart-fire-project",

    storageBucket:
        "smart-fire-project.firebasestorage.app",

    messagingSenderId:
        "591246962485",

    appId:
        "1:591246962485:web:2030ebe6c34a81f5bd667c"

};


firebase.initializeApp(firebaseConfig);

const messaging = firebase.messaging();


// =========================================================
// PUT YOUR EXISTING FIREBASE VAPID KEY HERE
// =========================================================

const vapidKey = "YOUR_EXISTING_FIREBASE_VAPID_KEY";


// =========================================================
// ELEMENT HELPERS
// =========================================================

function $(id) {
    return document.getElementById(id);
}


function showMessage(text, type = "notice") {

    $("actionMessage").innerHTML =
        `<div class="${type}">${text}</div>`;
}


// =========================================================
// REGISTRATION
// =========================================================

async function registerOwner() {

    const data = {

        name: $("name").value.trim(),

        phone: $("phone").value.trim(),

        email: $("email").value.trim(),

        location: $("location").value.trim(),

        device_id: $("device_id").value.trim()

    };


    if (!data.name || !data.phone) {

        $("registerMessage").innerHTML =
            '<div class="notice">Please enter your name and phone number.</div>';

        return;
    }


    try {

        const response = await fetch("/register", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify(data)

        });


        const result = await response.json();


        if (!result.success) {

            $("registerMessage").innerHTML =
                `<div class="notice">${result.message}</div>`;

            return;
        }


        // Save registration on this device/browser.
        localStorage.setItem(
            "smartFireOwner",
            JSON.stringify(data)
        );


        showDashboard(data);


    } catch (error) {

        $("registerMessage").innerHTML =
            '<div class="notice">Could not connect to server.</div>';

    }

}


// =========================================================
// SHOW DASHBOARD
// =========================================================

function showDashboard(data) {

    $("registration").classList.add("hidden");

    $("dashboard").classList.remove("hidden");


    $("ownerName").textContent =
        data.name || "-";

    $("ownerPhone").textContent =
        data.phone || "-";

    $("ownerEmail").textContent =
        data.email || "-";

    $("ownerLocation").textContent =
        data.location || "-";

    $("ownerDevice").textContent =
        data.device_id || "-";


    // Try to register this browser's FCM token.
    if (
        "Notification" in window &&
        Notification.permission === "granted"
    ) {

        enableNotifications(false);
    }


    updateStatus();

}


// =========================================================
// LOAD SAVED OWNER
// =========================================================

async function loadOwner() {

    const saved =
        localStorage.getItem("smartFireOwner");


    if (!saved) {

        $("registration").classList.remove("hidden");

        $("dashboard").classList.add("hidden");

        return;
    }


    try {

        const data = JSON.parse(saved);

        showDashboard(data);


        // Also update server copy after page reload.
        await fetch("/register", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify(data)

        });


    } catch (error) {

        localStorage.removeItem("smartFireOwner");

        $("registration").classList.remove("hidden");

        $("dashboard").classList.add("hidden");

    }

}


// =========================================================
// ENABLE FCM NOTIFICATIONS
// =========================================================

async function enableNotifications(showMessageBox = true) {

    try {

        if (!("Notification" in window)) {

            if (showMessageBox) {
                showMessage(
                    "This browser does not support notifications."
                );
            }

            return;
        }


        const permission =
            await Notification.requestPermission();


        if (permission !== "granted") {

            if (showMessageBox) {
                showMessage(
                    "Notification permission was not granted."
                );
            }

            return;
        }


        const registration =
            await navigator.serviceWorker.register(
                "/firebase-messaging-sw.js"
            );


        const token =
            await messaging.getToken({

                vapidKey: vapidKey,

                serviceWorkerRegistration:
                    registration

            });


        if (!token) {

            if (showMessageBox) {
                showMessage(
                    "Could not get Firebase device token."
                );
            }

            return;
        }


        localStorage.setItem(
            "smartFireFCMToken",
            token
        );


        const response =
            await fetch("/save-fcm-token", {

                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    token: token
                })

            });


        const result =
            await response.json();


        if (showMessageBox) {

            if (result.success) {

                showMessage(
                    "🔔 Notifications are enabled on this device.",
                    "success"
                );

            } else {

                showMessage(
                    "Could not save notification device."
                );

            }

        }

    } catch (error) {

        console.error(error);

        if (showMessageBox) {

            showMessage(
                "Notification setup failed. Check your Firebase VAPID key."
            );

        }

    }

}


// =========================================================
// FOREGROUND FCM MESSAGE
// =========================================================

messaging.onMessage(function(payload) {

    console.log(
        "Foreground notification:",
        payload
    );


    const title =
        payload.notification?.title ||
        "🔥 Smart Fire Guard";


    const body =
        payload.notification?.body ||
        "Fire alert received.";


    showMessage(
        `${title}<br>${body}`,
        "notice"
    );


    if (
        "Notification" in window &&
        Notification.permission === "granted"
    ) {

        new Notification(title, {
            body: body
        });

    }

});


// =========================================================
// TEST FIRE
// =========================================================

async function testFire() {

    let token =
        localStorage.getItem("smartFireFCMToken");


    // Try to get a fresh token first.
    try {

        if (
            "Notification" in window &&
            Notification.permission === "granted"
        ) {

            const registration =
                await navigator.serviceWorker.register(
                    "/firebase-messaging-sw.js"
                );


            const freshToken =
                await messaging.getToken({

                    vapidKey: vapidKey,

                    serviceWorkerRegistration:
                        registration

                });


            if (freshToken) {

                token = freshToken;

                localStorage.setItem(
                    "smartFireFCMToken",
                    token
                );


                await fetch("/save-fcm-token", {

                    method: "POST",

                    headers: {
                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify({
                        token: token
                    })

                });

            }

        }

    } catch (error) {

        console.log(
            "Token refresh error:",
            error
        );

    }


    try {

        const response =
            await fetch("/api/test-fire", {

                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    token: token || ""
                })

            });


        const result =
            await response.json();


        if (result.success) {

            showMessage(
                "🔥 Test Fire sent. Check this device for the notification.",
                "success"
            );

        } else {

            showMessage(
                result.message || "Test failed."
            );

        }


        updateStatus();


    } catch (error) {

        showMessage(
            "Could not send Test Fire."
        );

    }

}


// =========================================================
// RESET
// =========================================================

async function resetSystem() {

    try {

        await fetch("/api/reset", {
            method: "POST"
        });

        updateStatus();

        showMessage(
            "System reset successfully.",
            "success"
        );

    } catch (error) {

        showMessage(
            "Reset failed."
        );

    }

}


// =========================================================
// CHANGE OWNER
// =========================================================

function changeOwner() {

    const confirmed =
        confirm(
            "Change owner details?"
        );


    if (!confirmed) {
        return;
    }


    localStorage.removeItem(
        "smartFireOwner"
    );


    $("dashboard").classList.add("hidden");

    $("registration").classList.remove("hidden");


    $("name").value = "";

    $("phone").value = "";

    $("email").value = "";

    $("location").value = "";

    $("device_id").value = "";

}


// =========================================================
// STATUS
// =========================================================

async function updateStatus() {

    try {

        const response =
            await fetch("/status");


        const data =
            await response.json();


        $("flame").textContent =
            data.flame || "NOT DETECTED";


        $("temperature").textContent =
            `${data.temperature || 0} °C`;


        $("extinguisher").textContent =
            data.extinguisher || "READY";


        $("notification").textContent =
            data.notification_sent
                ? "SENT"
                : "READY";


        if (data.fire) {

            $("statusTitle").textContent =
                "🔥 FIRE DETECTED";

            $("statusText").textContent =
                "Emergency alert active";

            $("statusBadge").textContent =
                "FIRE";

            $("statusBadge").className =
                "badge fire";

        } else {

            $("statusTitle").textContent =
                "System Safe";

            $("statusText").textContent =
                "No fire detected";

            $("statusBadge").textContent =
                "SAFE";

            $("statusBadge").className =
                "badge safe";

        }

    } catch (error) {

        console.log(
            "Status error:",
            error
        );

    }

}


// =========================================================
// START
// =========================================================

loadOwner();


// Update every 3 seconds.
setInterval(
    updateStatus,
    3000
);


</script>


</body>
</html>
"""


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():
    return render_template_string(HTML)


# =========================================================
# REGISTER OWNER
# =========================================================

@app.route("/register", methods=["POST"])
def register():

    global owner

    data = request.get_json(silent=True) or {}

    owner["name"] = str(data.get("name", "")).strip()
    owner["phone"] = str(data.get("phone", "")).strip()
    owner["email"] = str(data.get("email", "")).strip()
    owner["location"] = str(data.get("location", "")).strip()
    owner["device_id"] = str(data.get("device_id", "")).strip()

    print("Owner registered:", owner["name"])

    return jsonify({
        "success": True,
        "message": "Owner registered successfully."
    })


# =========================================================
# SAVE FCM DEVICE TOKEN
# =========================================================

@app.route("/save-fcm-token", methods=["POST"])
def save_fcm_token():

    data = request.get_json(silent=True) or {}

    token = str(data.get("token", "")).strip()


    if not token:

        return jsonify({
            "success": False,
            "message": "FCM token missing."
        }), 400


    fcm_tokens.add(token)

    print(
        "FCM device registered. Total devices:",
        len(fcm_tokens)
    )


    return jsonify({
        "success": True,
        "devices": len(fcm_tokens)
    })


# =========================================================
# STATUS
# =========================================================

@app.route("/status")
def status():

    return jsonify(fire_status)


# =========================================================
# ESP8266 FIRE API
# =========================================================

@app.route("/api/fire", methods=["POST"])
def api_fire():

    global fire_status

    data = request.get_json(silent=True) or {}


    fire_value = data.get("fire", True)


    # Convert string values safely.
    if isinstance(fire_value, str):

        fire_value = fire_value.lower() in [
            "true",
            "1",
            "yes",
            "fire",
            "detected"
        ]


    fire = bool(fire_value)


    fire_status["fire"] = fire

    fire_status["flame"] = str(
        data.get(
            "flame",
            "DETECTED" if fire else "NOT DETECTED"
        )
    )

    fire_status["temperature"] = data.get(
        "temperature",
        0
    )

    fire_status["extinguisher"] = (
        "ACTIVE" if fire else "READY"
    )

    fire_status["notification_sent"] = False


    # Send alert when fire is detected.
    if fire:

        sent = send_fire_to_all_devices()

        fire_status["notification_sent"] = sent


    return jsonify({
        "success": True,
        "fire": fire,
        "notification_sent":
            fire_status["notification_sent"]
    })


# =========================================================
# TEST FIRE
# =========================================================

@app.route("/api/test-fire", methods=["POST"])
def test_fire():

    global fire_status

    data = request.get_json(silent=True) or {}

    token = str(
        data.get("token", "")
    ).strip()


    fire_status["fire"] = True

    fire_status["flame"] = "TEST FIRE"

    fire_status["temperature"] = 50

    fire_status["extinguisher"] = "TEST MODE"

    fire_status["notification_sent"] = False


    # -----------------------------------------------------
    # IMPORTANT:
    # If a token is supplied, send ONLY to the device
    # that pressed Test Fire.
    # -----------------------------------------------------

    if token:

        fcm_tokens.add(token)

        sent = send_notification(
            token,
            "🧪 TEST FIRE ALERT",
            "This is a Smart Fire Guard test notification.",
            "test_fire"
        )

    else:

        # No token means we cannot target the test device.
        sent = False


    fire_status["notification_sent"] = sent


    return jsonify({
        "success": sent,
        "message":
            "Test notification sent to this device."
            if sent
            else
            "Test notification could not be sent. Enable notifications first."
    })


# =========================================================
# RESET
# =========================================================

@app.route("/api/reset", methods=["POST"])
def reset():

    global fire_status

    fire_status = {
        "fire": False,
        "flame": "NOT DETECTED",
        "temperature": 0,
        "extinguisher": "READY",
        "notification_sent": False
    }


    return jsonify({
        "success": True,
        "message": "System reset."
    })


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        )
    )
