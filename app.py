from flask import Flask, request, jsonify, render_template_string
import os

app = Flask(__name__)

# =============================
# DEMO DATA
# No SQL
# No file handling
# =============================

owner = {
    "name": "",
    "phone": "",
    "email": "",
    "location": "",
    "device_id": ""
}

status = {
    "fire": False,
    "temperature": 28,
    "flame": "NOT DETECTED",
    "extinguisher": "READY",
    "device_online": True
}


# =============================
# WEBSITE
# =============================

HTML = """
<!DOCTYPE html>
<html>
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
            font-family: Arial, sans-serif;
        }

        body {
            background: #0b1220;
            color: white;
        }

        .container {
            width: 92%;
            max-width: 1100px;
            margin: auto;
        }

        header {
            padding: 20px 0;
            border-bottom: 1px solid #26344d;
        }

        nav {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .logo {
            font-size: 24px;
            font-weight: bold;
        }

        .logo span {
            color: #ff4b3e;
        }

        .hero {
            text-align: center;
            padding: 70px 10px;
        }

        .hero h1 {
            font-size: 60px;
            margin-bottom: 15px;
        }

        .hero h1 span {
            color: #ff4b3e;
        }

        .hero p {
            color: #aebbd0;
            font-size: 18px;
            line-height: 1.6;
        }

        .button {
            border: none;
            border-radius: 10px;
            padding: 13px 20px;
            margin-top: 20px;
            background: #ff4b3e;
            color: white;
            font-weight: bold;
            cursor: pointer;
        }

        .button:hover {
            opacity: 0.85;
        }

        .section {
            margin: 35px 0;
        }

        .card {
            background: #121c2e;
            border: 1px solid #26344d;
            border-radius: 16px;
            padding: 25px;
            margin-bottom: 20px;
        }

        h2 {
            margin-bottom: 20px;
        }

        form {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }

        input {
            width: 100%;
            padding: 13px;
            border-radius: 8px;
            border: 1px solid #34435e;
            background: #0b1220;
            color: white;
        }

        .full {
            grid-column: 1 / -1;
        }

        .dashboard {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
        }

        .status-card {
            background: #121c2e;
            border: 1px solid #26344d;
            border-radius: 14px;
            padding: 22px;
            text-align: center;
        }

        .status-card h3 {
            color: #9eacc1;
            font-size: 14px;
            margin-bottom: 10px;
        }

        .value {
            font-size: 22px;
            font-weight: bold;
        }

        .safe {
            color: #39d98a;
        }

        .danger {
            color: #ff4b3e;
        }

        .alert {
            display: none;
            background: #4a1717;
            border: 1px solid #ff4b3e;
            border-radius: 14px;
            padding: 25px;
            margin-top: 20px;
            text-align: center;
        }

        .alert h2 {
            color: #ff6b61;
        }

        .info {
            color: #aebbd0;
            line-height: 1.7;
        }

        .steps {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
        }

        .step {
            background: #121c2e;
            border: 1px solid #26344d;
            border-radius: 14px;
            padding: 20px;
            text-align: center;
        }

        footer {
            text-align: center;
            padding: 35px 0;
            color: #71809a;
        }

        @media(max-width: 750px) {

            form,
            .dashboard,
            .steps {
                grid-template-columns: 1fr;
            }

            .full {
                grid-column: auto;
            }

            .hero h1 {
                font-size: 40px;
            }
        }

    </style>

</head>

<body>


<header>

    <div class="container">

        <nav>

            <div class="logo">
                SMART <span>FIRE</span> GUARD
            </div>

            <div>
                🔥 Safety System
            </div>

        </nav>

    </div>

</header>


<!-- HERO -->

<section class="hero">

    <div class="container">

        <h1>
            SMART <span>FIRE</span> GUARD
        </h1>

        <p>
            Automatic fire monitoring and warning system.
            Detect fire, activate safety system and warn
            the registered owner.
        </p>

        <button
            class="button"
            onclick="document.getElementById('register').scrollIntoView({behavior:'smooth'})">

            REGISTER OWNER

        </button>

    </div>

</section>


<!-- OWNER REGISTRATION -->

<section class="section" id="register">

    <div class="container">

        <div class="card">

            <h2>
                👤 Register Owner
            </h2>

            <form id="registerForm">

                <input
                    id="name"
                    placeholder="Owner Name"
                    required>

                <input
                    id="phone"
                    placeholder="Phone Number"
                    required>

                <input
                    id="email"
                    type="email"
                    placeholder="Email Address">

                <input
                    id="location"
                    placeholder="House / Location"
                    required>

                <input
                    id="device_id"
                    class="full"
                    placeholder="Fire Guard Device ID"
                    required>

                <button
                    class="button full"
                    type="submit">

                    SAVE REGISTRATION

                </button>

            </form>

            <p
                id="registerMessage"
                class="info"
                style="margin-top:15px;">
            </p>

        </div>

    </div>

</section>


<!-- DASHBOARD -->

<section class="section">

    <div class="container">

        <div class="card">

            <h2>
                📊 Live Safety Dashboard
            </h2>

            <div class="dashboard">


                <div class="status-card">

                    <h3>
                        TEMPERATURE
                    </h3>

                    <div
                        id="temperature"
                        class="value">

                        -- °C

                    </div>

                </div>


                <div class="status-card">

                    <h3>
                        FLAME SENSOR
                    </h3>

                    <div
                        id="flame"
                        class="value safe">

                        --

                    </div>

                </div>


                <div class="status-card">

                    <h3>
                        EXTINGUISHER
                    </h3>

                    <div
                        id="extinguisher"
                        class="value safe">

                        --

                    </div>

                </div>


                <div class="status-card">

                    <h3>
                        DEVICE
                    </h3>

                    <div
                        id="device"
                        class="value safe">

                        --

                    </div>

                </div>

            </div>


            <!-- FIRE ALERT -->

            <div
                id="fireAlert"
                class="alert">

                <h2>
                    🚨 FIRE ALERT!
                </h2>

                <p>
                    A possible fire has been detected.
                </p>

                <p
                    id="ownerAlert"
                    style="margin-top:10px;">
                </p>

            </div>


            <!-- TEST BUTTONS -->

            <div style="text-align:center;">

                <button
                    class="button"
                    onclick="testFire()">

                    TEST FIRE ALERT

                </button>


                <button
                    class="button"
                    style="background:#33435e;"
                    onclick="resetSystem()">

                    RESET TO SAFE

                </button>

            </div>

        </div>

    </div>

</section>


<!-- HOW IT WORKS -->

<section class="section">

    <div class="container">

        <div class="card">

            <h2>
                ⚙️ How It Works
            </h2>

            <div class="steps">


                <div class="step">

                    <h3>
                        🔥 Sensor
                    </h3>

                    <p class="info">
                        Detects flame or abnormal temperature.
                    </p>

                </div>


                <div class="step">

                    <h3>
                        📡 ESP32
                    </h3>

                    <p class="info">
                        Sends safety information through Wi-Fi.
                    </p>

                </div>


                <div class="step">

                    <h3>
                        ☁️ Server
                    </h3>

                    <p class="info">
                        Receives and processes the fire alert.
                    </p>

                </div>


                <div class="step">

                    <h3>
                        📱 Owner
                    </h3>

                    <p class="info">
                        The registered owner is warned.
                    </p>

                </div>

            </div>

        </div>

    </div>

</section>


<footer>

    Smart Fire Guard — School Project Prototype

</footer>


<script>


// =============================
// LOAD STATUS
// =============================

async function loadStatus() {

    try {

        const response =
            await fetch("/status");

        const data =
            await response.json();


        document.getElementById(
            "temperature"
        ).innerText =
            data.temperature + " °C";


        document.getElementById(
            "flame"
        ).innerText =
            data.flame;


        document.getElementById(
            "extinguisher"
        ).innerText =
            data.extinguisher;


        document.getElementById(
            "device"
        ).innerText =
            data.device_online
            ? "ONLINE"
            : "OFFLINE";


        const flame =
            document.getElementById("flame");

        const extinguisher =
            document.getElementById("extinguisher");

        const device =
            document.getElementById("device");

        const alertBox =
            document.getElementById("fireAlert");


        if (data.fire) {

            flame.className =
                "value danger";

            extinguisher.className =
                "value danger";

            alertBox.style.display =
                "block";

            document.getElementById(
                "ownerAlert"
            ).innerText =
                "Warning generated for the registered owner.";

        }

        else {

            flame.className =
                "value safe";

            extinguisher.className =
                "value safe";

            alertBox.style.display =
                "none";

        }


        device.className =
            data.device_online
            ? "value safe"
            : "value danger";

    }

    catch(error) {

        console.log(error);

    }

}


// =============================
// REGISTER OWNER
// =============================

document.getElementById(
    "registerForm"
).addEventListener(
    "submit",
    async function(event) {

        event.preventDefault();


        const data = {

            name:
                document.getElementById(
                    "name"
                ).value,

            phone:
                document.getElementById(
                    "phone"
                ).value,

            email:
                document.getElementById(
                    "email"
                ).value,

            location:
                document.getElementById(
                    "location"
                ).value,

            device_id:
                document.getElementById(
                    "device_id"
                ).value

        };


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

    }
);


// =============================
// TEST FIRE
// =============================

async function testFire() {

    await fetch(
        "/api/test-fire",
        {
            method: "POST"
        }
    );

    loadStatus();

}


// =============================
// RESET
// =============================

async function resetSystem() {

    await fetch(
        "/api/reset",
        {
            method: "POST"
        }
    );

    loadStatus();

}


// Update every 2 seconds

loadStatus();

setInterval(
    loadStatus,
    2000
);

</script>


</body>
</html>
"""


# =============================
# HOME
# =============================

@app.route("/")
def home():

    return render_template_string(HTML)


# =============================
# REGISTER OWNER
# =============================

@app.route("/register", methods=["POST"])
def register():

    data = request.get_json(
        silent=True
    ) or {}


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


    return jsonify({

        "success": True,

        "message":
            "Owner registered successfully!"

    })


# =============================
# GET SYSTEM STATUS
# =============================

@app.route("/status")
def get_status():

    return jsonify(status)


# =============================
# ESP32 FIRE API
# =============================

@app.route(
    "/api/fire",
    methods=["POST"]
)
def fire_event():

    data = request.get_json(
        silent=True
    ) or {}


    fire = bool(
        data.get(
            "fire",
            False
        )
    )


    status["fire"] = fire


    status["temperature"] = data.get(
        "temperature",
        82 if fire else 28
    )


    status["flame"] = data.get(
        "flame",
        "DETECTED"
        if fire
        else "NOT DETECTED"
    )


    status["extinguisher"] = (
        "ACTIVATED"
        if fire
        else "READY"
    )


    return jsonify({

        "success": True,

        "message":
            "Fire status received"

    })


# =============================
# TEST FIRE
# =============================

@app.route(
    "/api/test-fire",
    methods=["POST"]
)
def test_fire():

    status["fire"] = True

    status["temperature"] = 82

    status["flame"] = "DETECTED"

    status["extinguisher"] = "ACTIVATED"


    return jsonify({

        "success": True,

        "message":
            "Test fire alert activated"

    })


# =============================
# RESET SYSTEM
# =============================

@app.route(
    "/api/reset",
    methods=["POST"]
)
def reset():

    status["fire"] = False

    status["temperature"] = 28

    status["flame"] = "NOT DETECTED"

    status["extinguisher"] = "READY"


    return jsonify({

        "success": True,

        "message":
            "System reset to safe"

    })


# =============================
# RUN SERVER
# =============================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
