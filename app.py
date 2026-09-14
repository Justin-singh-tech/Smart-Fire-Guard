 from flask import Flask, request, jsonify, render_template_string
import os, json
import firebase_admin
from firebase_admin import credentials, messaging

app = Flask(__name__)

# ---------- Firebase ----------
firebase_ready = False

try:
    key = os.getenv("FIREBASE_SERVICE_ACCOUNT")
    if key:
        cred = credentials.Certificate(json.loads(key))
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        firebase_ready = True
except Exception as e:
    print("Firebase error:", e)

# ---------- Data ----------
owner = {}
tokens = set()

status = {
    "fire": False,
    "flame": "NOT DETECTED",
    "temperature": 0,
    "extinguisher": "READY",
    "notification_sent": False
}

# ---------- Notification ----------
def send_alert(token, title, body):
    if not firebase_ready:
        return False

    try:
        msg = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body
            ),
            token=token
        )
        messaging.send(msg)
        return True
    except Exception as e:
        print("Notification error:", e)
        tokens.discard(token)
        return False


def notify_all():
    sent = False

    for token in list(tokens):
        if send_alert(
            token,
            "🔥 FIRE ALERT!",
            "Smart Fire Guard detected a possible fire."
        ):
            sent = True

    return sent


# ---------- Service Worker ----------
@app.route("/firebase-messaging-sw.js")
def service_worker():
    return """
importScripts(
"https://www.gstatic.com/firebasejs/10.13.2/firebase-app-compat.js");
importScripts(
"https://www.gstatic.com/firebasejs/10.13.2/firebase-messaging-compat.js");

firebase.initializeApp({
 apiKey:"AIzaSyD1JM4e0Ztg3FUhCkA4tYh8UzEOYcdn9k",
 authDomain:"smart-fire-project.firebaseapp.com",
 projectId:"smart-fire-project",
 storageBucket:"smart-fire-project.firebasestorage.app",
 messagingSenderId:"591246962485",
 appId:"1:591246962485:web:2030ebe6c34a81f5bd667c"
});

const messaging=firebase.messaging();

messaging.onBackgroundMessage(p=>{
 const n=p.notification||{};
 self.registration.showNotification(
   n.title||"🔥 Smart Fire Guard",
   {body:n.body||"Fire alert received."}
 );
});
""", 200, {"Content-Type": "application/javascript"}


# ---------- Website ----------
HTML = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Smart Fire Guard</title>

<script src="https://www.gstatic.com/firebasejs/10.13.2/firebase-app-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/10.13.2/firebase-messaging-compat.js"></script>

<style>
body{
font-family:Arial;
background:#101522;
color:white;
text-align:center;
padding:20px;
}
.card{
max-width:600px;
margin:15px auto;
padding:20px;
background:#1b2335;
border-radius:15px;
}
input,button{
width:90%;
padding:12px;
margin:6px;
border-radius:8px;
border:0;
}
button{
background:#ff5636;
color:white;
font-weight:bold;
}
.safe{color:#55ff88}
.fire{color:#ff6045}
</style>
</head>

<body>

<h1>🔥 SMART FIRE GUARD</h1>

<div id="register" class="card">
<h2>👤 Owner Registration</h2>

<input id="name" placeholder="Owner Name">
<input id="phone" placeholder="Phone Number">
<input id="email" placeholder="Email">
<input id="location" placeholder="Location">
<input id="device" placeholder="Device ID">

<button onclick="register()">Register</button>
</div>


<div id="dashboard" class="card" style="display:none">

<h2>📊 Fire Guard Dashboard</h2>

<h2 id="main" class="safe">SYSTEM SAFE</h2>

<p>🔥 Flame: <b id="flame">NOT DETECTED</b></p>
<p>🌡️ Temperature: <b id="temp">0 °C</b></p>
<p>🚿 Extinguisher: <b id="pump">READY</b></p>
<p>🔔 Notification: <b id="notification">READY</b></p>

<hr>

<h3>👤 Owner</h3>
<p id="owner"></p>

<button onclick="enableNotifications()">
🔔 Enable Notifications
</button>

<button onclick="testFire()">
🧪 Test Fire
</button>

<button onclick="resetFire()">
🔄 Reset
</button>

</div>


<script>

const config={
apiKey:"AIzaSyD1JM4e0Ztg3FUhCkA4tYh8UzEOYcdn9k",
authDomain:"smart-fire-project.firebaseapp.com",
projectId:"smart-fire-project",
storageBucket:"smart-fire-project.firebasestorage.app",
messagingSenderId:"591246962485",
appId:"1:591246962485:web:2030ebe6c34a81f5bd667c"
};

firebase.initializeApp(config);
const messaging=firebase.messaging();

/* PUT YOUR EXISTING VAPID KEY HERE */
const vapidKey="BDMQ6bqrix1EQOm7fOuz-PBd_jHarjFNl3WrQtmFYVg72scD_rwzvLleIwVw0jJ9JXAxrlb0ygUSquZBWYBLm4I";


function register(){

let data={
name:document.getElementById("name").value,
phone:document.getElementById("phone").value,
email:document.getElementById("email").value,
location:document.getElementById("location").value,
device_id:document.getElementById("device").value
};

if(!data.name||!data.phone){
alert("Enter name and phone");
return;
}

localStorage.setItem(
"owner",
JSON.stringify(data)
);

fetch("/register",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify(data)
});

showDashboard(data);
}


function showDashboard(data){

document.getElementById("register").style.display="none";
document.getElementById("dashboard").style.display="block";

document.getElementById("owner").innerText=
data.name+" | "+data.phone;

updateStatus();
}


async function enableNotifications(){

try{

let permission=await Notification.requestPermission();

if(permission!="granted"){
alert("Notification permission denied");
return;
}

let reg=await navigator.serviceWorker.register(
"/firebase-messaging-sw.js"
);

let token=await messaging.getToken({
vapidKey:vapidKey,
serviceWorkerRegistration:reg
});

if(token){

localStorage.setItem("fcm",token);

await fetch("/save-fcm-token",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({token:token})
});

alert("🔔 Notifications enabled!");

}

}catch(e){
console.log(e);
alert("Notification setup failed");
}
}


async function testFire(){

let token=localStorage.getItem("fcm")||"";

await fetch("/api/test-fire",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({token:token})
});

updateStatus();
}


async function resetFire(){

await fetch("/api/reset",{method:"POST"});
updateStatus();
}


async function updateStatus(){

let r=await fetch("/status");
let d=await r.json();

document.getElementById("flame").innerText=d.flame;
document.getElementById("temp").innerText=d.temperature+" °C";
document.getElementById("pump").innerText=d.extinguisher;
document.getElementById("notification").innerText=
d.notification_sent?"SENT":"READY";

let main=document.getElementById("main");

if(d.fire){
main.innerText="🔥 FIRE DETECTED";
main.className="fire";
}else{
main.innerText="SYSTEM SAFE";
main.className="safe";
}
}


let saved=localStorage.getItem("owner");

if(saved){
showDashboard(JSON.parse(saved));
}

setInterval(updateStatus,3000);

</script>

</body>
</html>
"""


@app.route("/")
def home():
    return render_template_string(HTML)


# ---------- Register ----------
@app.route("/register", methods=["POST"])
def register_owner():
    global owner
    owner = request.get_json() or {}
    return jsonify({"success": True})


# ---------- FCM Token ----------
@app.route("/save-fcm-token", methods=["POST"])
def save_token():
    data = request.get_json() or {}
    token = data.get("token")

    if not token:
        return jsonify({"success": False}), 400

    tokens.add(token)

    return jsonify({
        "success": True,
        "devices": len(tokens)
    })


# ---------- Status ----------
@app.route("/status")
def get_status():
    return jsonify(status)


# ---------- ESP8266 ----------
@app.route("/api/fire", methods=["POST"])
def fire_api():

    data = request.get_json() or {}

    fire = bool(data.get("fire", True))

    status["fire"] = fire
    status["flame"] = data.get(
        "flame",
        "DETECTED" if fire else "NOT DETECTED"
    )
    status["temperature"] = data.get("temperature", 0)
    status["extinguisher"] = "ACTIVE" if fire else "READY"
    status["notification_sent"] = False

    if fire:
        status["notification_sent"] = notify_all()

    return jsonify(status)


# ---------- Test ----------
@app.route("/api/test-fire", methods=["POST"])
def test_fire():

    data = request.get_json() or {}
    token = data.get("token")

    status["fire"] = True
    status["flame"] = "TEST FIRE"
    status["temperature"] = 50
    status["extinguisher"] = "TEST MODE"

    if token:
        tokens.add(token)
        status["notification_sent"] = send_alert(
            token,
            "🧪 TEST FIRE ALERT",
            "Smart Fire Guard test notification."
        )
    else:
        status["notification_sent"] = False

    return jsonify(status)


# ---------- Reset ----------
@app.route("/api/reset", methods=["POST"])
def reset():

    status.update({
        "fire": False,
        "flame": "NOT DETECTED",
        "temperature": 0,
        "extinguisher": "READY",
        "notification_sent": False
    })

    return jsonify(status)


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT",5000))
    )
