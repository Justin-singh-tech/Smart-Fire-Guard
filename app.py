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
    service_account_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT")

    if service_account_json:
        service_account = json.loads(service_account_json)
        cred = credentials.Certificate(service_account)

        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)

        firebase_ready = True
        print("Firebase Admin connected.")

    else:
        print("FIREBASE_SERVICE_ACCOUNT is not set.")

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

# Store multiple devices instead of only one FCM token.
fcm_tokens = set()


fire_status = {
    "fire": False,
    "flame": "NOT DETECTED",
    "temperature": 0,
    "extinguisher": "READY",
    "notification_sent": False
}


# =========================================================
# SEND NOTIFICATION TO ONE DEVICE
# =========================================================

def send_notification(token):
    if not firebase_ready:
        print("Firebase is not ready.")
        return False

    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title="🔥 FIRE ALERT!",
                body="Smart Fire Guard detected a possible fire."
            ),
            data={
                "type": "fire_alert",
                "message": "Fire detected by Smart Fire Guard."
            },
            token=token
        )

        messaging.send(message)

        print("Notification sent to device.")
        return True

    except Exception as e:
        print("Notification error:", e)

        # Remove bad/expired token.
        fcm_tokens.discard(token)

        return False


# =========================================================
# SEND TO ALL REGISTERED DEVICES
# =========================================================

def send_to_all_devices():
    if not fcm_tokens:
        print("No FCM devices registered.")
        return False

    success = False

    for token in list(fcm_tokens):
        if send_notification(token):
            success = True

    return success


# =========================================================
# FIREBASE SERVICE WORKER
# =========================================================

@app.route("/firebase-messaging-sw.js")
def firebase_service_worker():

    firebase_config = {
        "apiKey": "AIzaSyD1JM4e0Ztg3FUhCkA4tYh8UzEOYcdn9k",
        "authDomain": "smart-fire-project.firebaseapp.com",
        "projectId": "smart-fire-project",
        "storageBucket": "smart-fire-project.firebasestorage.app",
        "messagingSenderId": "591246962485",
        "appId": "1:591246962485:web:2030ebe6c34a81f5bd667c"
    }

    js = f"""
importScripts(
    "https://www.gstatic.com/firebasejs/10.13.2/firebase-app-compat.js"
);

importScripts(
    "https://www.gstatic.com/firebasejs/10.13.2/firebase-messaging-compat.js"
);

firebase.initializeApp({json.dumps(firebase_config)});

const messaging = firebase.messaging();

messaging.onBackgroundMessage(function(payload) {{

    console.log("Background message:", payload);

    const title =
        payload.notification?.title || "🔥 FIRE ALERT!";

    const options = {{
        body:
            payload.notification?.body ||
            "Smart Fire Guard detected a possible fire.",
        icon: "/favicon.ico",
        tag: "smart-fire-alert"
    }};

    self.registration.showNotification(title, options);
}});

self.addEventListener("notificationclick", function(event) {{
    event.notification.close();

    event.waitUntil(
        clients.matchAll({{
            type: "window",
            includeUncontrolled: true
        }}).then(function(clientList) {{

            for (const client of clientList) {{
                if ("focus" in client) {{
                    return client.focus();
                }}
            }}

            if (clients.openWindow) {{
                return clients.openWindow("/");
            }}
        }})
    );
}});
"""

    return js, 200, {
        "Content-Type": "application/javascript"
    }


# =========================================================
# MAIN WEBSITE
# =========================================================

@app.route("/")
def home():

    return render_template_string("""
<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>Smart Fire Guard</title>

<style>

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family:
        Inter,
        system-ui,
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;

    min-height: 100vh;

    background:
        radial-gradient(
            circle at top left,
            #26345c,
            transparent 35%
        ),
        radial-gradient(
            circle at bottom right,
            #3a1820,
            transparent 35%
        ),
        #080b14;

    color: #ffffff;
}


/* =====================================================
   HEADER
   ===================================================== */

header {
    position: sticky;
    top: 0;
    z-index: 10;

    display: flex;
    justify-content: space-between;
    align-items: center;

    padding: 18px 7%;

    background: rgba(10, 14, 25, 0.75);

    backdrop-filter: blur(18px);

    border-bottom: 1px solid rgba(255,255,255,0.08);
}

.logo {
    display: flex;
    align-items: center;
    gap: 12px;

    font-size: 20px;
    font-weight: 800;
    letter-spacing: 0.5px;
}

.logo-icon {
    width: 42px;
    height: 42px;

    display: flex;
    justify-content: center;
    align-items: center;

    border-radius: 13px;

    background:
        linear-gradient(
            135deg,
            #ff6b35,
            #ff304f
        );

    box-shadow:
        0 8px 25px rgba(255, 70, 60, 0.3);
}

.online {
    display: flex;
    align-items: center;
    gap: 8px;

    color: #8df7b1;
    font-size: 13px;
}

.online-dot {
    width: 9px;
    height: 9px;

    border-radius: 50%;

    background: #4ade80;

    box-shadow:
        0 0 12px #4ade80;
}


/* =====================================================
   PAGE
   ===================================================== */

.container {
    width: 86%;
    max-width: 1200px;

    margin: 45px auto;
}

.hero {
    margin-bottom: 30px;
}

.hero h1 {
    font-size: clamp(32px, 5vw, 54px);

    line-height: 1.05;

    margin-bottom: 14px;

    background:
        linear-gradient(
            90deg,
            #ffffff,
            #ff9b75
        );

    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.hero p {
    color: #aeb7ca;
    font-size: 16px;
}


/* =====================================================
   GLASS CARD
   ===================================================== */

.card {
    background:
        linear-gradient(
            145deg,
            rgba(255,255,255,0.09),
            rgba(255,255,255,0.035)
        );

    border: 1px solid rgba(255,255,255,0.09);

    border-radius: 24px;

    padding: 25px;

    backdrop-filter: blur(20px);

    box-shadow:
        0 20px 60px rgba(0,0,0,0.25);
}


/* =====================================================
   REGISTRATION
   ===================================================== */

#registerPage {
    max-width: 600px;
    margin: 50px auto;
}

.section-title {
    font-size: 25px;
    margin-bottom: 8px;
}

.section-subtitle {
    color: #9ca8bc;
    margin-bottom: 25px;
}

.input-group {
    margin-bottom: 17px;
}

label {
    display: block;

    margin-bottom: 7px;

    color: #c5cede;

    font-size: 13px;
}

input {
    width: 100%;

    padding: 14px 16px;

    border-radius: 13px;

    border: 1px solid rgba(255,255,255,0.1);

    background: rgba(0,0,0,0.25);

    color: white;

    outline: none;

    font-size: 15px;
}

input:focus {
    border-color: #ff684b;

    box-shadow:
        0 0 0 3px rgba(255,104,75,0.12);
}


/* =====================================================
   BUTTONS
   ===================================================== */

button {
    border: none;

    cursor: pointer;

    border-radius: 13px;

    padding: 13px 18px;

    font-size: 14px;

    font-weight: 700;

    transition: 0.2s;
}

button:hover {
    transform: translateY(-2px);
}

.primary {
    width: 100%;

    color: white;

    background:
        linear-gradient(
            135deg,
            #ff6b35,
            #ff3d58
        );

    box-shadow:
        0 10px 25px rgba(255,70,60,0.25);
}

.secondary {
    color: white;

    background: rgba(255,255,255,0.08);

    border: 1px solid rgba(255,255,255,0.1);
}

.danger {
    color: white;

    background:
        linear-gradient(
            135deg,
            #ef4444,
            #b91c1c
        );
}


/* =====================================================
   DASHBOARD
   ===================================================== */

#dashboardPage {
    display: none;
}

.dashboard-grid {
    display: grid;

    grid-template-columns:
        repeat(4, 1fr);

    gap: 17px;

    margin-bottom: 20px;
}

.status-card {
    min-height: 145px;
}

.status-label {
    color: #9da8bb;

    font-size: 13px;

    margin-bottom: 14px;
}

.status-value {
    font-size: 25px;

    font-weight: 800;
}

.status-icon {
    font-size: 27px;

    margin-bottom: 12px;
}

.safe {
    color: #70e39a;
}

.warning {
    color: #ffb15e;
}

.danger-text {
    color: #ff6868;
}


/* =====================================================
   MAIN GRID
   ===================================================== */

.main-grid {
    display: grid;

    grid-template-columns:
        1.4fr 0.8fr;

    gap: 20px;
}

.fire-panel {
    min-height: 310px;

    display: flex;

    flex-direction: column;

    justify-content: space-between;
}

.fire-circle {
    width: 125px;
    height: 125px;

    margin: 15px auto 20px;

    display: flex;

    justify-content: center;
    align-items: center;

    border-radius: 50%;

    font-size: 48px;

    background:
        rgba(75, 220, 120, 0.08);

    border:
        1px solid rgba(75, 220, 120, 0.2);

    box-shadow:
        0 0 50px rgba(75,220,120,0.08);
}

.fire-circle.alert {
    background:
        rgba(255,60,60,0.12);

    border-color:
        rgba(255,70,70,0.35);

    box-shadow:
        0 0 60px rgba(255,50,50,0.15);
}

.fire-title {
    text-align: center;

    font-size: 22px;

    font-weight: 800;
}

.fire-description {
    text-align: center;

    color: #9da8bb;

    margin-top: 7px;
}


/* =====================================================
   OWNER CARD
   ===================================================== */

.owner-row {
    display: flex;

    justify-content: space-between;

    gap: 20px;

    padding: 13px 0;

    border-bottom:
        1px solid rgba(255,255,255,0.07);
}

.owner-row:last-child {
    border-bottom: none;
}

.owner-key {
    color: #8f9aae;
}

.owner-value {
    text-align: right;

    max-width: 60%;

    word-break: break-word;
}


/* =====================================================
   ACTIONS
   ===================================================== */

.actions {
    display: grid;

    grid-template-columns:
        repeat(3, 1fr);

    gap: 10px;

    margin-top: 20px;
}

.actions button {
    width: 100%;
}


/* =====================================================
   NOTIFICATION
   ===================================================== */

.notification-box {
    margin-top: 20px;

    padding: 15px;

    border-radius: 15px;

    background:
        rgba(255,255,255,0.05);

    color: #b8c2d3;

    font-size: 14px;
}

.notification-box strong {
    color: white;
}


/* =====================================================
   FOOTER
   ===================================================== */

footer {
    text-align: center;

    color: #667085;

    font-size: 12px;

    margin-top: 35px;
}


/* =====================================================
   MOBILE
   ===================================================== */

@media (max-width: 850px) {

    .dashboard-grid {
        grid-template-columns:
            repeat(2, 1fr);
    }

    .main-grid {
        grid-template-columns: 1fr;
    }
}


@media (max-width: 550px) {

    header {
        padding: 15px 5%;
    }

    .container {
        width: 92%;
        margin: 30px auto;
    }

    .dashboard-grid {
        grid-template-columns: 1fr;
    }

    .actions {
        grid-template-columns: 1fr;
    }

    .logo span {
        display: none;
    }
}

</style>

</head>


<body>


<header>

    <div class="logo">

        <div class="logo-icon">
            🔥
        </div>

        <span>SMART FIRE GUARD</span>

    </div>

    <div class="online">

        <div class="online-dot"></div>

        System Online

    </div>

</header>


<main class="container">


<!-- =====================================================
     REGISTRATION PAGE
===================================================== -->

<section id="registerPage" class="card">

    <h2 class="section-title">
        Welcome to Smart Fire Guard
    </h2>

    <p class="section-subtitle">
        Register the owner once to configure your fire alert system.
    </p>


    <div class="input-group">

        <label>Owner Name</label>

        <input
            id="name"
            type="text"
            placeholder="Enter owner name"
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

        <label>House / Location</label>

        <input
            id="location"
            type="text"
            placeholder="Enter house location"
        >

    </div>


    <button
        class="primary"
        onclick="registerOwner()"
    >
        Register & Continue
    </button>

</section>


<!-- =====================================================
     DASHBOARD
===================================================== -->

<section id="dashboardPage">


    <div class="hero">

        <h1>
            Fire Protection Dashboard
        </h1>

        <p>
            Monitor your Smart Fire Guard system in real time.
        </p>

    </div>


    <!-- STATUS CARDS -->

    <div class="dashboard-grid">


        <div class="card status-card">

            <div class="status-icon">
                🔥
            </div>

            <div class="status-label">
                FIRE STATUS
            </div>

            <div
                id="fireStatus"
                class="status-value safe"
            >
                SAFE
            </div>

        </div>


        <div class="card status-card">

            <div class="status-icon">
                🌡️
            </div>

            <div class="status-label">
                TEMPERATURE
            </div>

            <div
                id="temperature"
                class="status-value"
            >
                0 °C
            </div>

        </div>


        <div class="card status-card">

            <div class="status-icon">
                👁️
            </div>

            <div class="status-label">
                FLAME SENSOR
            </div>

            <div
                id="flameStatus"
                class="status-value safe"
            >
                NOT DETECTED
            </div>

        </div>


        <div class="card status-card">

            <div class="status-icon">
                💧
            </div>

            <div class="status-label">
                EXTINGUISHER
            </div>

            <div
                id="extinguisher"
                class="status-value safe"
            >
                READY
            </div>

        </div>

    </div>


    <!-- MAIN -->

    <div class="main-grid">


        <!-- FIRE PANEL -->

        <div class="card fire-panel">

            <div>

                <div
                    id="fireCircle"
                    class="fire-circle"
                >
                    🛡️
                </div>

                <div
                    id="fireTitle"
                    class="fire-title"
                >
                    System Protected
                </div>

                <div
                    id="fireDescription"
                    class="fire-description"
                >
                    No fire has been detected.
                </div>

            </div>


            <div class="notification-box">

                🔔

                <strong>
                    Notifications:
                </strong>

                <span id="notificationStatus">
                    Not enabled
                </span>

            </div>


            <div class="actions">

                <button
                    class="primary"
                    onclick="enableNotifications()"
                >
                    🔔 Enable Notifications
                </button>

                <button
                    class="danger"
                    onclick="testFire()"
                >
                    🚨 Test Fire
                </button>

                <button
                    class="secondary"
                    onclick="resetSystem()"
                >
                    ↻ Reset
                </button>

            </div>

        </div>


        <!-- OWNER -->

        <div class="card">

            <h2 class="section-title">
                👤 Owner
            </h2>

            <p class="section-subtitle">
                Registered information
            </p>


            <div class="owner-row">

                <span class="owner-key">
                    Name
                </span>

                <span
                    id="ownerName"
                    class="owner-value"
                >
                    -
                </span>

            </div>


            <div class="owner-row">

                <span class="owner-key">
                    Phone
                </span>

                <span
                    id="ownerPhone"
                    class="owner-value"
                >
                    -
                </span>

            </div>


            <div class="owner-row">

                <span class="owner-key">
                    Email
                </span>

                <span
                    id="ownerEmail"
                    class="owner-value"
                >
                    -
                </span>

            </div>


            <div class="owner-row">

                <span class="owner-key">
                    Location
                </span>

                <span
                    id="ownerLocation"
                    class="owner-value"
                >
                    -
                </span>

            </div>


            <button
                class="secondary"
                style="width:100%; margin-top:20px;"
                onclick="changeOwner()"
            >
                ⚙️ Change Owner Details
            </button>

        </div>

    </div>


</section>


<footer>

    Smart Fire Guard • School Competition Project

</footer>


</main>


<!-- =====================================================
     FIREBASE
===================================================== -->

<script src="https://www.gstatic.com/firebasejs/10.13.2/firebase-app-compat.js"></script>

<script src="https://www.gstatic.com/firebasejs/10.13.2/firebase-messaging-compat.js"></script>


<script>


// =========================================================
// FIREBASE CONFIG
// =========================================================

const firebaseConfig = {

    apiKey:
        "AIzaSyD1JM4e0Ztg3FUhCkA4tYh8UzEOYcdn9k",

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


let currentFcmToken =
    localStorage.getItem("smartFireFcmToken") || "";


// =========================================================
// YOUR FCM VAPID KEY
// =========================================================
//
// Keep your existing Firebase Web Push certificate key here.
// Do NOT put your Firebase Admin private key here.
//

const vapidKey = "YOUR_EXISTING_FIREBASE_VAPID_KEY";


// =========================================================
// LOAD SAVED OWNER
// =========================================================

window.addEventListener("load", async function() {

    const savedOwner =
        localStorage.getItem("smartFireOwner");

    if (savedOwner) {

        try {

            const data =
                JSON.parse(savedOwner);

            showDashboard(data);

            // Re-register owner with server.
            await fetch("/register", {

                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify(data)

            });

        }

        catch (error) {

            console.log(
                "Saved owner data error:",
                error
            );

            localStorage.removeItem(
                "smartFireOwner"
            );

            showRegistration();
        }

    }

    else {

        showRegistration();

    }


    // If notification permission was already granted,
    // automatically refresh the FCM token.

    if (
        "Notification" in window &&
        Notification.permission === "granted"
    ) {

        enableNotifications();

    }


    // Start live status updates.

    updateStatus();

    setInterval(updateStatus, 3000);

});


// =========================================================
// REGISTRATION
// =========================================================

async function registerOwner() {

    const data = {

        name:
            document.getElementById("name").value.trim(),

        phone:
            document.getElementById("phone").value.trim(),

        email:
            document.getElementById("email").value.trim(),

        location:
            document.getElementById("location").value.trim(),

        device_id:
            getDeviceId()

    };


    if (!data.name || !data.phone) {

        alert(
            "Please enter owner name and phone number."
        );

        return;
    }


    try {

        const response =
            await fetch("/register", {

                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body:
                    JSON.stringify(data)

            });


        if (!response.ok) {

            throw new Error(
                "Registration failed."
            );
        }


        // Save owner in this browser/device.

        localStorage.setItem(
            "smartFireOwner",
            JSON.stringify(data)
        );


        showDashboard(data);


        // Ask for notification permission.

        await enableNotifications();

    }

    catch (error) {

        console.error(error);

        alert(
            "Registration could not be completed."
        );

    }

}


// =========================================================
// DEVICE ID
// =========================================================

function getDeviceId() {

    let id =
        localStorage.getItem(
            "smartFireDeviceId"
        );


    if (!id) {

        id =
            "device-" +
            Date.now() +
            "-" +
            Math.random()
                .toString(36)
                .substring(2, 10);

        localStorage.setItem(
            "smartFireDeviceId",
            id
        );
    }


    return id;
}


// =========================================================
// SHOW DASHBOARD
// =========================================================

function showDashboard(data) {

    document.getElementById(
        "registerPage"
    ).style.display = "none";


    document.getElementById(
        "dashboardPage"
    ).style.display = "block";


    document.getElementById(
        "ownerName"
    ).textContent =
        data.name || "-";


    document.getElementById(
        "ownerPhone"
    ).textContent =
        data.phone || "-";


    document.getElementById(
        "ownerEmail"
    ).textContent =
        data.email || "-";


    document.getElementById(
        "ownerLocation"
    ).textContent =
        data.location || "-";

}


// =========================================================
// SHOW REGISTRATION
// =========================================================

function showRegistration() {

    document.getElementById(
        "registerPage"
    ).style.display = "block";


    document.getElementById(
        "dashboardPage"
    ).style.display = "none";

}


// =========================================================
// CHANGE OWNER
// =========================================================

function changeOwner() {

    if (
        confirm(
            "Do you want to change the registered owner?"
        )
    ) {

        localStorage.removeItem(
            "smartFireOwner"
        );

        showRegistration();

    }

}


// =========================================================
// ENABLE FCM NOTIFICATIONS
// =========================================================

async function enableNotifications() {

    if (!("Notification" in window)) {

        alert(
            "This browser does not support notifications."
        );

        return null;
    }


    try {

        const permission =
            await Notification.requestPermission();


        if (permission !== "granted") {

            document.getElementById(
                "notificationStatus"
            ).textContent =
                "Permission not granted.";

            return null;
        }


        // Register Firebase service worker.

        const registration =
            await navigator.serviceWorker.register(
                "/firebase-messaging-sw.js"
            );


        // Get this browser's unique FCM token.

        const token =
            await messaging.getToken({

                vapidKey: vapidKey,

                serviceWorkerRegistration:
                    registration

            });


        if (!token) {

            throw new Error(
                "FCM token was not created."
            );
        }


        currentFcmToken = token;


        localStorage.setItem(
            "smartFireFcmToken",
            token
        );


        // Send token to Flask server.

        await fetch(
            "/save-fcm-token",
            {

                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({
                    token: token
                })

            }
        );


        document.getElementById(
            "notificationStatus"
        ).textContent =
            "Enabled on this device";


        return token;

    }

    catch (error) {

        console.error(
            "FCM error:",
            error
        );


        document.getElementById(
            "notificationStatus"
        ).textContent =
            "Could not enable notifications.";


        return null;

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
        "🔥 FIRE ALERT!";


    const body =
        payload.notification?.body ||
        "Smart Fire Guard detected a possible fire.";


    if (
        "Notification" in window &&
        Notification.permission === "granted"
    ) {

        new Notification(
            title,
            {
                body: body
            }
        );

    }


    updateStatus();

});


// =========================================================
// TEST FIRE
// =========================================================

async function testFire() {

    // Make sure this device has a current FCM token.

    let token = currentFcmToken;


    if (
        "Notification" in window &&
        Notification.permission === "granted"
    ) {

        try {

            const refreshedToken =
                await enableNotifications();

            if (refreshedToken) {

                token = refreshedToken;

            }

        }

        catch (error) {

            console.log(error);

        }

    }


    if (!token) {

        alert(
            "First press 'Enable Notifications' and allow notifications."
        );

        return;
    }


    try {

        const response =
            await fetch(
                "/api/test-fire",
                {

                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        token: token
                    })

                }
            );


        const result =
            await response.json();


        if (!response.ok) {

            alert(
                result.message ||
                "Test failed."
            );

            return;
        }


        alert(
            "🔥 Test Fire sent to this device."
        );


        updateStatus();

    }

    catch (error) {

        console.error(error);

        alert(
            "Could not contact the server."
        );

    }

}


// =========================================================
// RESET
// =========================================================

async function resetSystem() {

    try {

        await fetch(
            "/api/reset",
            {
                method: "POST"
            }
        );

        updateStatus();

    }

    catch (error) {

        console.error(error);

    }

}


// =========================================================
// LIVE STATUS
// =========================================================

async function updateStatus() {

    try {

        const response =
            await fetch("/status");


        if (!response.ok) {

            return;
        }


        const data =
            await response.json();


        const fire =
            data.fire === true;


        const fireStatus =
            document.getElementById(
                "fireStatus"
            );


        const flameStatus =
            document.getElementById(
                "flameStatus"
            );


        const extinguisher =
            document.getElementById(
                "extinguisher"
            );


        const fireCircle =
            document.getElementById(
                "fireCircle"
            );


        const fireTitle =
            document.getElementById(
                "fireTitle"
            );


        const fireDescription =
            document.getElementById(
                "fireDescription"
            );


        document.getElementById(
            "temperature"
        ).textContent =
            (data.temperature ?? 0) +
            " °C";


        // FIRE

        if (fire) {

            fireStatus.textContent =
                "FIRE DETECTED";

            fireStatus.className =
                "status-value danger-text";


            fireCircle.classList.add(
                "alert"
            );

            fireCircle.textContent =
                "🔥";


            fireTitle.textContent =
                "Fire Alert";


            fireDescription.textContent =
                "The system has detected a possible fire.";

        }

        else {

            fireStatus.textContent =
                "SAFE";

            fireStatus.className =
                "status-value safe";


            fireCircle.classList.remove(
                "alert"
            );

            fireCircle.textContent =
                "🛡️";


            fireTitle.textContent =
                "System Protected";


            fireDescription.textContent =
                "No fire has been detected.";

        }


        // FLAME

        flameStatus.textContent =
            data.flame || "NOT DETECTED";


        if (fire) {

            flameStatus.className =
                "status-value danger-text";

        }

        else {

            flameStatus.className =
                "status-value safe";

        }


        // EXTINGUISHER

        extinguisher.textContent =
            data.extinguisher || "READY";


        if (data.extinguisher === "ACTIVE") {

            extinguisher.className =
                "status-value warning";

        }

        else {

            extinguisher.className =
                "status-value safe";

        }


        // NOTIFICATION

        document.getElementById(
            "notificationStatus"
        ).textContent =
            data.notification_sent
                ? "Notification sent"
                : (
                    document.getElementById(
                        "notificationStatus"
                    ).textContent
                );

    }

    catch (error) {

        console.log(
            "Status update error:",
            error
        );

    }

}

</script>

</body>

</html>
""")


# =========================================================
# REGISTER OWNER
# =========================================================

@app.route("/register", methods=["POST"])
def register():

    global owner

    data = request.get_json(silent=True) or {}


    owner["name"] = data.get(
        "name",
        ""
    )

    owner["phone"] = data.get(
        "phone",
        ""
    )

    owner["email"] = data.get(
        "email",
        ""
    )

    owner["location"] = data.get(
        "location",
        ""
    )

    owner["device_id"] = data.get(
        "device_id",
        ""
    )


    return jsonify({
        "success": True,
        "message": "Owner registered."
    })


# =========================================================
# SAVE FCM TOKEN
# =========================================================

@app.route("/save-fcm-token", methods=["POST"])
def save_fcm_token():

    data = request.get_json(silent=True) or {}

    token = data.get("token", "").strip()


    if not token:

        return jsonify({
            "success": False,
            "message": "FCM token missing."
        }), 400


    fcm_tokens.add(token)


    print(
        "Registered FCM devices:",
        len(fcm_tokens)
    )


    return jsonify({
        "success": True,
        "message": "Device notification token saved.",
        "devices": len(fcm_tokens)
    })


# =========================================================
# STATUS
# =========================================================

@app.route("/status")
def status():

    return jsonify(fire_status)


# =========================================================
# REAL ESP8266 FIRE EVENT
# =========================================================

@app.route("/api/fire", methods=["POST"])
def api_fire():

    global fire_status

    data = request.get_json(silent=True) or {}


    fire_value = data.get(
        "fire",
        True
    )


    fire_status["fire"] = bool(
        fire_value
    )


    fire_status["flame"] = data.get(
        "flame",
        "DETECTED"
    )


    fire_status["temperature"] = data.get(
        "temperature",
        0
    )


    if fire_status["fire"]:

        fire_status["extinguisher"] = "ACTIVE"


        notification_ok =
            send_to_all_devices()


        fire_status[
            "notification_sent"
        ] = notification_ok


    else:

        fire_status[
            "extinguisher"
        ] = "READY"


    return jsonify({
        "success": True,
        "fire": fire_status["fire"],
        "notification_sent":
            fire_status["notification_sent"]
    })


# =========================================================
# TEST FIRE
# =========================================================

@app.route("/api/test-fire", methods=["POST"])
def api_test_fire():

    global fire_status

    data = request.get_json(silent=True) or {}

    test_token = data.get(
        "token",
        ""
    ).strip()


    fire_status["fire"] = True

    fire_status["flame"] = "TEST FIRE"

    fire_status["temperature"] = 0

    fire_status["extinguisher"] = "ACTIVE"


    # IMPORTANT:
    # Test Fire sends ONLY to the device that pressed
    # the Test Fire button.

    if test_token:

        notification_ok =
            send_notification(
                test_token
            )

    else:

        notification_ok = False


    fire_status[
        "notification_sent"
    ] = notification_ok


    return jsonify({
        "success": True,
        "message":
            "Test fire processed.",
        "notification_sent":
            notification_ok
    })


# =========================================================
# RESET
# =========================================================

@app.route("/api/reset", methods=["POST"])
def reset():

    global fire_status

    fire_status = {

        "fire": False,

        "flame":
            "NOT DETECTED",

        "temperature":
            0,

        "extinguisher":
            "READY",

        "notification_sent":
            False

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
