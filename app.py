from flask import Flask, request, jsonify, render_template_string
import os
import json

import firebase_admin
from firebase_admin import credentials, messaging


app = Flask(__name__)


# ============================================================
# FIREBASE ADMIN
# ============================================================

firebase_ready = False

try:
    service_account = os.environ.get("FIREBASE_SERVICE_ACCOUNT")

    if service_account:
        firebase_credential = credentials.Certificate(
            json.loads(service_account)
        )

        if not firebase_admin._apps:
            firebase_admin.initialize_app(firebase_credential)

        firebase_ready = True
        print("Firebase initialized successfully.")

    else:
        print("WARNING: FIREBASE_SERVICE_ACCOUNT is missing.")

except Exception as error:
    print("Firebase initialization error:", error)


# ============================================================
# OWNER
# ============================================================

owner = {
    "name": "",
    "phone": "",
    "email": "",
    "location": "",
    "device_id": "",
    "fcm_token": ""
}


# ============================================================
# FIRE STATUS
# ============================================================

fire_status = {
    "fire": False,
    "flame": "SAFE",
    "temperature": 0,
    "extinguisher": "OFF",
    "notification_sent": False
}


# ============================================================
# SEND FIREBASE NOTIFICATION
# ============================================================

def send_notification(token):

    if not firebase_ready:
        print("Firebase is not ready.")
        return False

    if not token:
        print("FCM token is missing.")
        return False

    try:

        message = messaging.Message(
            notification=messaging.Notification(
                title="🚨 SMART FIRE GUARD",
                body=(
                    "🔥 FIRE DETECTED! "
                    "Please check the location immediately."
                )
            ),
            data={
                "type": "fire_alert",
                "temperature": str(
                    fire_status["temperature"]
                ),
                "location": owner["location"]
            },
            token=token
        )

        response = messaging.send(message)

        print("FCM notification sent:", response)

        return True

    except Exception as error:

        print("FCM notification error:", error)

        return False


# ============================================================
# FIREBASE SERVICE WORKER
# ============================================================

@app.route("/firebase-messaging-sw.js")
def firebase_messaging_sw():

    javascript = """
importScripts(
    "https://www.gstatic.com/firebasejs/12.19.0/firebase-app-compat.js"
);

importScripts(
    "https://www.gstatic.com/firebasejs/12.19.0/firebase-messaging-compat.js"
);

firebase.initializeApp({
    apiKey: "YOUR_FIREBASE_API_KEY",
    authDomain: "smart-fire-project.firebaseapp.com",
    projectId: "smart-fire-project",
    storageBucket: "smart-fire-project.firebasestorage.app",
    messagingSenderId: "591246962485",
    appId: "1:591246962485:web:2030ebe6c34a81f5bd667c"
});

const messaging = firebase.messaging();

messaging.onBackgroundMessage(function(payload) {

    console.log("Background notification:", payload);

    const title =
        payload.notification?.title ||
        "🚨 SMART FIRE GUARD";

    const options = {
        body:
            payload.notification?.body ||
            "🔥 Fire detected. Please check immediately.",
        data: payload.data || {}
    };

    self.registration.showNotification(
        title,
        options
    );
});
"""

    return javascript, 200, {
        "Content-Type": "application/javascript"
    }


# ============================================================
# HTML
# ============================================================

HTML = """
<!DOCTYPE html>

<html>

<head>

<title>Smart Fire Guard</title>

<meta
    name="viewport"
    content="width=device-width, initial-scale=1"
>

<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    font-family: Arial, sans-serif;
    background: #f4f8ff;
    color: #172033;
}

header {
    background: white;
    border-bottom: 4px solid #1677ff;
    padding: 20px;
    text-align: center;
}

header h1 {
    margin: 0;
    color: #1677ff;
}

header p {
    margin: 7px 0 0;
    color: #555;
}

.container {
    max-width: 1000px;
    margin: auto;
    padding: 20px;
}

.card {
    background: white;
    border: 2px solid #1677ff;
    border-radius: 15px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 5px 15px rgba(0,0,0,0.08);
}

h2 {
    color: #1677ff;
}

input {
    width: 100%;
    padding: 13px;
    margin: 7px 0 12px;
    border: 1px solid #bbb;
    border-radius: 8px;
    font-size: 16px;
}

button {
    padding: 12px 18px;
    border: none;
    border-radius: 8px;
    background: #1677ff;
    color: white;
    font-size: 16px;
    cursor: pointer;
    margin: 5px;
}

button:hover {
    opacity: 0.85;
}

.danger {
    background: #e53935;
}

.safe {
    background: #20a050;
}

.notification {
    background: #673ab7;
}

.status {
    padding: 20px;
    border-radius: 12px;
    text-align: center;
    font-size: 22px;
    font-weight: bold;
    background: #e8fff0;
    color: #16833c;
}

.fire {
    background: #ffe5e5;
    color: #d00000;
}

.grid {
    display: grid;
    grid-template-columns:
        repeat(auto-fit, minmax(200px, 1fr));
    gap: 15px;
}

.box {
    background: #f7f9fc;
    padding: 15px;
    border-radius: 10px;
    border: 1px solid #ddd;
}

.value {
    font-size: 25px;
    font-weight: bold;
    margin-top: 5px;
}

.notification-box {
    padding: 12px;
    margin-top: 10px;
    border-radius: 8px;
    background: #f2f2f2;
}

footer {
    text-align: center;
    padding: 20px;
    color: #666;
}

</style>

</head>


<body>


<header>

<h1>🔥 SMART FIRE GUARD</h1>

<p>
Automatic Fire Detection & Alert System
</p>

</header>


<div class="container">


<!-- OWNER -->

<div class="card">

<h2>👤 Owner Registration</h2>

<input
    id="name"
    placeholder="Owner Name"
>

<input
    id="phone"
    placeholder="Phone Number (+91...)"
>

<input
    id="email"
    placeholder="Email Address"
>

<input
    id="location"
    placeholder="Fire Guard Location"
>

<input
    id="device"
    placeholder="Device ID"
>

<button onclick="registerOwner()">
Register Owner
</button>

<p id="registerMessage"></p>

</div>


<!-- NOTIFICATIONS -->

<div class="card">

<h2>🔔 Firebase Notifications</h2>

<p>
Enable notifications on this device so Smart Fire Guard
can send fire alerts.
</p>

<button
    class="notification"
    onclick="enableNotifications()"
>
🔔 Enable Notifications
</button>

<div
    id="notificationMessage"
    class="notification-box"
>
Notifications are not enabled.
</div>

</div>


<!-- STATUS -->

<div class="card">

<h2>🚨 System Status</h2>

<div
    id="status"
    class="status"
>
✅ SYSTEM IS SAFE
</div>

</div>


<!-- SENSOR -->

<div class="card">

<h2>📊 Sensor Information</h2>

<div class="grid">


<div class="box">

Flame

<div
    id="flame"
    class="value"
>
SAFE
</div>

</div>


<div class="box">

Temperature

<div
    id="temperature"
    class="value"
>
0 °C
</div>

</div>


<div class="box">

Extinguisher

<div
    id="extinguisher"
    class="value"
>
OFF
</div>

</div>


<div class="box">

Notification

<div
    id="notification"
    class="value"
>
NOT SENT
</div>

</div>


</div>

</div>


<!-- DEMO -->

<div class="card">

<h2>🧪 Demonstration</h2>

<p>
Use these buttons to test the website.
Do not use real fire for testing.
</p>

<button
    class="danger"
    onclick="testFire()"
>
🔥 Test Fire
</button>

<button
    class="safe"
    onclick="resetSystem()"
>
✅ Reset System
</button>

<p id="message"></p>

</div>


</div>


<footer>

Smart Fire Guard © 2026

</footer>


<script type="module">

import {
    initializeApp
}
from
"https://www.gstatic.com/firebasejs/12.19.0/firebase-app.js";


import {
    getMessaging,
    getToken,
    onMessage
}
from
"https://www.gstatic.com/firebasejs/12.19.0/firebase-messaging.js";


// ==========================================================
// FIREBASE WEB CONFIG
// ==========================================================

const firebaseConfig = {

    apiKey:
        "AIzaSyD1JM4e0Ztg3FUhCkA4t9Yh8UzEOYcdn9k",

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


const firebaseApp =
    initializeApp(firebaseConfig);


const messaging =
    getMessaging(firebaseApp);


// ==========================================================
// ENABLE NOTIFICATIONS
// ==========================================================

window.enableNotifications = async function() {

    const messageBox =
        document.getElementById(
            "notificationMessage"
        );

    try {

        if (!("Notification" in window)) {

            messageBox.innerText =
                "❌ This browser does not support notifications.";

            return;
        }


        const registration =
            await navigator.serviceWorker.register(
                "/firebase-messaging-sw.js"
            );


        const permission =
            await Notification.requestPermission();


        if (permission !== "granted") {

            messageBox.innerText =
                "❌ Notification permission was not granted.";

            return;
        }


        const token =
            await getToken(
                messaging,
                {
                    vapidKey:
                        "BDMQ6bqrix1EQOm7fOuz-PBd_jHarjFNl3WrQtmFYVg72scD_rwzvLleIwVw0jJ9JXAxrlb0ygUSquZBWYBLm4I",

                    serviceWorkerRegistration:
                        registration
                }
            );


        if (!token) {

            messageBox.innerText =
                "❌ Firebase notification token was not created.";

            return;
        }


        const response =
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


        const result =
            await response.json();


        if (result.success) {

            messageBox.innerText =
                "✅ Notifications enabled successfully!";

        } else {

            messageBox.innerText =
                "❌ " + result.message;

        }


    } catch (error) {

        console.error(
            "Notification error:",
            error
        );

        messageBox.innerText =
            "❌ Notification setup failed: "
            + error.message;

    }

};


// ==========================================================
// FOREGROUND NOTIFICATION
// ==========================================================

onMessage(
    messaging,
    function(payload) {

        console.log(
            "Firebase foreground message:",
            payload
        );


        const title =
            payload.notification?.title ||
            "🚨 SMART FIRE GUARD";


        const body =
            payload.notification?.body ||
            "🔥 Fire detected!";


        if (
            Notification.permission ===
            "granted"
        ) {

            new Notification(
                title,
                {
                    body: body
                }
            );

        }

    }
);


// ==========================================================
// REGISTER OWNER
// ==========================================================

window.registerOwner = async function() {

    const data = {

        name:
            document.getElementById("name").value,

        phone:
            document.getElementById("phone").value,

        email:
            document.getElementById("email").value,

        location:
            document.getElementById("location").value,

        device_id:
            document.getElementById("device").value

    };


    try {

        const response =
            await fetch(
                "/register",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify(data)
                }
            );


        const result =
            await response.json();


        document.getElementById(
            "registerMessage"
        ).innerText =
            result.message;

    } catch (error) {

        document.getElementById(
            "registerMessage"
        ).innerText =
            "Registration failed.";

    }

};


// ==========================================================
// TEST FIRE
// ==========================================================

window.testFire = async function() {

    try {

        const response =
            await fetch(
                "/api/test-fire",
                {
                    method: "POST"
                }
            );


        const result =
            await response.json();


        document.getElementById(
            "message"
        ).innerText =
            result.message;


        updateStatus();

    } catch (error) {

        document.getElementById(
            "message"
        ).innerText =
            "Test failed.";

    }

};


// ==========================================================
// RESET
// ==========================================================

window.resetSystem = async function() {

    try {

        const response =
            await fetch(
                "/api/reset",
                {
                    method: "POST"
                }
            );


        const result =
            await response.json();


        document.getElementById(
            "message"
        ).innerText =
            result.message;


        updateStatus();

    } catch (error) {

        document.getElementById(
            "message"
        ).innerText =
            "Reset failed.";

    }

};


// ==========================================================
// UPDATE STATUS
// ==========================================================

async function updateStatus() {

    try {

        const response =
            await fetch("/status");


        const data =
            await response.json();


        const status =
            document.getElementById("status");


        if (data.fire === true) {

            status.innerText =
                "🚨 FIRE DETECTED!";

            status.className =
                "status fire";

        } else {

            status.innerText =
                "✅ SYSTEM IS SAFE";

            status.className =
                "status";

        }


        document.getElementById(
            "flame"
        ).innerText =
            data.flame;


        document.getElementById(
            "temperature"
        ).innerText =
            data.temperature + " °C";


        document.getElementById(
            "extinguisher"
        ).innerText =
            data.extinguisher;


        document.getElementById(
            "notification"
        ).innerText =
            data.notification_sent
            ? "SENT"
            : "NOT SENT";


    } catch (error) {

        console.error(
            "Status update error:",
            error
        );

    }

}


setInterval(
    updateStatus,
    3000
);


updateStatus();

</script>


</body>

</html>
"""


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    return render_template_string(HTML)


# ============================================================
# REGISTER OWNER
# ============================================================

@app.route("/register", methods=["POST"])
def register():

    data = request.get_json(silent=True) or {}

    owner["name"] = data.get(
        "name",
        ""
    ).strip()

    owner["phone"] = data.get(
        "phone",
        ""
    ).strip()

    owner["email"] = data.get(
        "email",
        ""
    ).strip()

    owner["location"] = data.get(
        "location",
        ""
    ).strip()

    owner["device_id"] = data.get(
        "device_id",
        ""
    ).strip()


    if not owner["name"] or not owner["phone"]:

        return jsonify({
            "success": False,
            "message":
                "Name and phone number are required."
        }), 400


    return jsonify({
        "success": True,
        "message":
            "Owner registered successfully!"
    })


# ============================================================
# SAVE FCM TOKEN
# ============================================================

@app.route("/save-fcm-token", methods=["POST"])
def save_fcm_token():

    data = request.get_json(silent=True) or {}

    token = data.get(
        "token",
        ""
    ).strip()


    if not token:

        return jsonify({
            "success": False,
            "message":
                "No Firebase token received."
        }), 400


    owner["fcm_token"] = token

    print("FCM token saved.")


    return jsonify({
        "success": True,
        "message":
            "Notification device registered."
    })


# ============================================================
# STATUS
# ============================================================

@app.route("/status", methods=["GET"])
def status():

    return jsonify({

        "fire":
            fire_status["fire"],

        "flame":
            fire_status["flame"],

        "temperature":
            fire_status["temperature"],

        "extinguisher":
            fire_status["extinguisher"],

        "notification_sent":
            fire_status["notification_sent"],

        "owner":
            owner["name"]

    })


# ============================================================
# ESP8266 FIRE API
# ============================================================

@app.route("/api/fire", methods=["POST"])
def fire_api():

    data = request.get_json(
        silent=True
    ) or {}


    fire = data.get(
        "fire",
        False
    )

    flame = data.get(
        "flame",
        "DETECTED"
    )

    temperature = data.get(
        "temperature",
        82
    )


    # --------------------------------------------------------
    # FIRE DETECTED
    # --------------------------------------------------------

    if fire:

        fire_status["fire"] = True

        fire_status["flame"] = "DETECTED"

        fire_status["temperature"] = temperature

        fire_status["extinguisher"] = "ACTIVATED"


        # Send only once until reset

        if (
            not fire_status["notification_sent"]
            and owner["fcm_token"]
        ):

            success = send_notification(
                owner["fcm_token"]
            )

            if success:

                fire_status[
                    "notification_sent"
                ] = True


        return jsonify({

            "success": True,

            "fire": True,

            "message":
                "Fire detected. "
                "Extinguisher activated."

        })


    # --------------------------------------------------------
    # SAFE
    # --------------------------------------------------------

    fire_status["fire"] = False

    fire_status["flame"] = flame

    fire_status["temperature"] = temperature

    fire_status["extinguisher"] = "OFF"


    return jsonify({

        "success": True,

        "fire": False,

        "message":
            "System is safe."

    })


# ============================================================
# TEST FIRE
# ============================================================

@app.route("/api/test-fire", methods=["POST"])
def test_fire():

    fire_status["fire"] = True

    fire_status["flame"] = "DETECTED"

    fire_status["temperature"] = 82

    fire_status["extinguisher"] = "ACTIVATED"


    if (
        not fire_status["notification_sent"]
        and owner["fcm_token"]
    ):

        success = send_notification(
            owner["fcm_token"]
        )

        if success:

            fire_status[
                "notification_sent"
            ] = True


    return jsonify({

        "success": True,

        "message":
            "Test fire activated."

    })


# ============================================================
# RESET
# ============================================================

@app.route("/api/reset", methods=["POST"])
def reset():

    fire_status["fire"] = False

    fire_status["flame"] = "SAFE"

    fire_status["temperature"] = 0

    fire_status["extinguisher"] = "OFF"

    fire_status["notification_sent"] = False


    return jsonify({

        "success": True,

        "message":
            "System reset successfully."

    })


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )
