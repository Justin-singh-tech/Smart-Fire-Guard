from flask import Flask, request, jsonify, render_template_string
from twilio.rest import Client
import os

app = Flask(__name__)

# -----------------------------
# OWNER DATA
# -----------------------------
owner = {
    "name": "",
    "phone": "",
    "email": "",
    "location": "",
    "device_id": ""
}

# -----------------------------
# FIRE STATUS
# -----------------------------
fire_status = {
    "fire": False,
    "flame": "SAFE",
    "temperature": 0,
    "extinguisher": "OFF",
    "sms_sent": False
}


# -----------------------------
# SEND SMS
# -----------------------------
def send_sms(phone_number):
    try:
        account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        twilio_number = os.environ.get("TWILIO_PHONE_NUMBER")

        # Check that Twilio settings exist
        if not account_sid or not auth_token or not twilio_number:
            print("Twilio environment variables are missing.")
            return False

        client = Client(account_sid, auth_token)

        message = client.messages.create(
            body=(
                "FIRE ALERT!\n"
                "Smart Fire Guard detected a possible fire.\n"
                "Please check the location immediately."
            ),
            from_=twilio_number,
            to=phone_number
        )

        print("SMS sent:", message.sid)
        return True

    except Exception as e:
        print("SMS ERROR:", e)
        return False


# -----------------------------
# WEBSITE
# -----------------------------
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Smart Fire Guard</title>

    <meta name="viewport"
          content="width=device-width, initial-scale=1">

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
            background: #ffffff;
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
    <p>Automatic Fire Detection & Alert System</p>
</header>

<div class="container">

    <!-- OWNER REGISTRATION -->
    <div class="card">

        <h2>👤 Owner Registration</h2>

        <input id="name"
               placeholder="Owner Name">

        <input id="phone"
               placeholder="Phone Number (+91...)">

        <input id="email"
               placeholder="Email Address">

        <input id="location"
               placeholder="Fire Guard Location">

        <input id="device"
               placeholder="Device ID">

        <button onclick="registerOwner()">
            Register Owner
        </button>

        <p id="registerMessage"></p>

    </div>


    <!-- FIRE STATUS -->
    <div class="card">

        <h2>🚨 System Status</h2>

        <div id="status"
             class="status">

            System is SAFE

        </div>

    </div>


    <!-- SENSOR DATA -->
    <div class="card">

        <h2>📊 Sensor Information</h2>

        <div class="grid">

            <div class="box">
                Flame
                <div id="flame"
                     class="value">
                    SAFE
                </div>
            </div>

            <div class="box">
                Temperature
                <div id="temperature"
                     class="value">
                    0 °C
                </div>
            </div>

            <div class="box">
                Extinguisher
                <div id="extinguisher"
                     class="value">
                    OFF
                </div>
            </div>

            <div class="box">
                SMS
                <div id="sms"
                     class="value">
                    NOT SENT
                </div>
            </div>

        </div>

    </div>


    <!-- DEMO CONTROLS -->
    <div class="card">

        <h2>🧪 Demonstration</h2>

        <p>
            Use these buttons to test the website.
            Do not use real fire for testing.
        </p>

        <button class="danger"
                onclick="testFire()">
            🔥 Test Fire
        </button>

        <button class="safe"
                onclick="resetSystem()">
            ✅ Reset System
        </button>

        <p id="message"></p>

    </div>

</div>


<footer>
    Smart Fire Guard © 2026
</footer>


<script>

async function registerOwner() {

    const data = {

        name: document.getElementById("name").value,
        phone: document.getElementById("phone").value,
        email: document.getElementById("email").value,
        location: document.getElementById("location").value,
        device_id: document.getElementById("device").value

    };

    const response = await fetch("/register", {

        method: "POST",

        headers: {
            "Content-Type": "application/json"
        },

        body: JSON.stringify(data)

    });

    const result = await response.json();

    document.getElementById("registerMessage")
        .innerText = result.message;
}


async function testFire() {

    const response =
        await fetch("/api/test-fire", {
            method: "POST"
        });

    const result = await response.json();

    document.getElementById("message")
        .innerText = result.message;

    updateStatus();
}


async function resetSystem() {

    const response =
        await fetch("/api/reset", {
            method: "POST"
        });

    const result = await response.json();

    document.getElementById("message")
        .innerText = result.message;

    updateStatus();
}


async function updateStatus() {

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


    document.getElementById("flame")
        .innerText = data.flame;


    document.getElementById("temperature")
        .innerText =
        data.temperature + " °C";


    document.getElementById("extinguisher")
        .innerText =
        data.extinguisher;


    document.getElementById("sms")
        .innerText =
        data.sms_sent
        ? "SENT"
        : "NOT SENT";
}


setInterval(updateStatus, 3000);

updateStatus();

</script>

</body>
</html>
"""


# -----------------------------
# HOME PAGE
# -----------------------------
@app.route("/")
def home():
    return render_template_string(HTML)


# -----------------------------
# REGISTER OWNER
# -----------------------------
@app.route("/register", methods=["POST"])
def register():

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "message": "No registration data received."
        }), 400

    owner["name"] = data.get("name", "").strip()
    owner["phone"] = data.get("phone", "").strip()
    owner["email"] = data.get("email", "").strip()
    owner["location"] = data.get("location", "").strip()
    owner["device_id"] = data.get("device_id", "").strip()

    if not owner["name"] or not owner["phone"]:
        return jsonify({
            "success": False,
            "message": "Name and phone number are required."
        }), 400

    return jsonify({
        "success": True,
        "message": "Owner registered successfully!"
    })


# -----------------------------
# GET SYSTEM STATUS
# -----------------------------
@app.route("/status", methods=["GET"])
def status():

    return jsonify({
        "fire": fire_status["fire"],
        "flame": fire_status["flame"],
        "temperature": fire_status["temperature"],
        "extinguisher": fire_status["extinguisher"],
        "sms_sent": fire_status["sms_sent"],
        "owner": owner["name"]
    })


# -----------------------------
# ESP8266 FIRE API
# -----------------------------
@app.route("/api/fire", methods=["POST"])
def fire_api():

    data = request.get_json(silent=True) or {}

    fire = data.get("fire", False)
    flame = data.get("flame", "DETECTED")
    temperature = data.get("temperature", 82)

    # Fire detected
    if fire:

        fire_status["fire"] = True
        fire_status["flame"] = "DETECTED"
        fire_status["temperature"] = temperature
        fire_status["extinguisher"] = "ACTIVATED"

        # Send only ONE SMS until system is reset
        if not fire_status["sms_sent"]:

            if owner["phone"]:

                success = send_sms(owner["phone"])

                if success:
                    fire_status["sms_sent"] = True

        return jsonify({
            "success": True,
            "fire": True,
            "message": "Fire detected. Extinguisher activated."
        })

    # No fire
    fire_status["fire"] = False
    fire_status["flame"] = flame
    fire_status["temperature"] = temperature
    fire_status["extinguisher"] = "OFF"

    return jsonify({
        "success": True,
        "fire": False,
        "message": "System is safe."
    })


# -----------------------------
# TEST FIRE
# -----------------------------
@app.route("/api/test-fire", methods=["POST"])
def test_fire():

    fire_status["fire"] = True
    fire_status["flame"] = "DETECTED"
    fire_status["temperature"] = 82
    fire_status["extinguisher"] = "ACTIVATED"

    # Send SMS
    if not fire_status["sms_sent"] and owner["phone"]:

        success = send_sms(owner["phone"])

        if success:
            fire_status["sms_sent"] = True

    return jsonify({
        "success": True,
        "message": "Test fire activated."
    })


# -----------------------------
# RESET SYSTEM
# -----------------------------
@app.route("/api/reset", methods=["POST"])
def reset():

    fire_status["fire"] = False
    fire_status["flame"] = "SAFE"
    fire_status["temperature"] = 0
    fire_status["extinguisher"] = "OFF"

    # Allow SMS to be sent again
    fire_status["sms_sent"] = False

    return jsonify({
        "success": True,
        "message": "System reset successfully."
    })


# -----------------------------
# RUN SERVER
# -----------------------------
if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
