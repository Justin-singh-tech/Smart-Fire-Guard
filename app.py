import os
import json
from functools import wraps

from flask import Flask, request, jsonify, render_template
import firebase_admin
from firebase_admin import credentials, firestore, auth, messaging

app = Flask(__name__)
PORT = int(os.environ.get("PORT", 10000))
ESP_API_KEY = os.environ.get("ESP_API_KEY", "").strip()

def initialize_firebase():
    if firebase_admin._apps:
        return
    firebase_json = (
        os.environ.get("FIREBASE_SERVICE_ACCOUNT")
        or os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
    )
    if not firebase_json:
        raise RuntimeError("FIREBASE_SERVICE_ACCOUNT is missing.")
    try:
        info = json.loads(firebase_json)
        firebase_admin.initialize_app(credentials.Certificate(info))
    except json.JSONDecodeError as e:
        raise RuntimeError("FIREBASE_SERVICE_ACCOUNT contains invalid JSON.") from e

initialize_firebase()
db = firestore.client()

def error(message, status=400):
    return jsonify({"success": False, "error": message}), status

def success(**data):
    return jsonify({"success": True, **data})

def bearer():
    value = request.headers.get("Authorization", "")
    return value[7:].strip() if value.startswith("Bearer ") else None

def current_user():
    token = bearer()
    if not token:
        return None
    try:
        return auth.verify_id_token(token)
    except Exception:
        return None

def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user:
            return error("Authentication required.", 401)
        return fn(user, *args, **kwargs)
    return wrapped

def esp_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not ESP_API_KEY:
            return error("ESP_API_KEY is not configured.", 500)
        if request.headers.get("X-ESP-KEY", "") != ESP_API_KEY:
            return error("Invalid ESP API key.", 401)
        return fn(*args, **kwargs)
    return wrapped

def fire_value(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {
            "true", "1", "yes", "fire", "detected", "on"
        }
    return False

def send_fire_notification(uid, device_id):
    ref = db.collection("users").document(uid)
    doc = ref.get()
    if not doc.exists:
        return {"sent": 0, "removed": 0}

    data = doc.to_dict() or {}
    tokens = data.get("notificationTokens", [])
    if not isinstance(tokens, list):
        tokens = []

    tokens = list(dict.fromkeys(str(x).strip() for x in tokens if str(x).strip()))
    sent = 0
    removed = []

    for token in tokens:
        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title="🔥 FIRE ALERT",
                    body=f"Fire detected by {device_id}."
                ),
                data={
                    "type": "fire_alert",
                    "device_id": str(device_id),
                    "fire": "true"
                },
                token=token
            )
            messaging.send(message)
            sent += 1
        except (messaging.UnregisteredError, messaging.SenderIdMismatchError):
            removed.append(token)
        except Exception as exc:
            print("FCM error:", exc)

    if removed:
        ref.set({
            "notificationTokens": [x for x in tokens if x not in removed]
        }, merge=True)

    return {"sent": sent, "removed": len(removed)}

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/dashboard")
def dashboard_page():
    return render_template("dashboard.html")

@app.route("/profile")
def profile_page():
    return render_template("profile.html")

@app.route("/api/health")
def health():
    return jsonify({
        "success": True,
        "name": "Smart Fire Guard",
        "status": "online",
        "firebase": bool(firebase_admin._apps),
        "esp_api_key_configured": bool(ESP_API_KEY)
    })

@app.route("/api/profile", methods=["GET"])
@login_required
def get_profile(user):
    uid = user["uid"]
    doc = db.collection("users").document(uid).get()
    if doc.exists:
        data = doc.to_dict() or {}
        data.pop("notificationTokens", None)
    else:
        data = {}
    data["uid"] = uid
    data.setdefault("email", user.get("email", ""))
    data.setdefault("displayName", user.get("name", ""))
    return success(profile=data)

@app.route("/api/profile", methods=["POST"])
@login_required
def save_profile(user):
    body = request.get_json(silent=True) or {}
    fields = ["displayName", "phone", "address", "city", "state", "emergencyContact"]
    data = {k: str(body.get(k, "")).strip() for k in fields if k in body}
    data.update({
        "uid": user["uid"],
        "email": user.get("email", ""),
        "updatedAt": firestore.SERVER_TIMESTAMP
    })
    db.collection("users").document(user["uid"]).set(data, merge=True)
    return success(message="Profile saved.")

@app.route("/api/notification-token", methods=["POST"])
@login_required
def save_token(user):
    body = request.get_json(silent=True) or {}
    token = str(body.get("token", "")).strip()
    if not token:
        return error("FCM token is required.")
    ref = db.collection("users").document(user["uid"])
    doc = ref.get()
    data = doc.to_dict() if doc.exists else {}
    tokens = data.get("notificationTokens", [])
    if not isinstance(tokens, list):
        tokens = []
    if token not in tokens:
        tokens.append(token)
    ref.set({
        "uid": user["uid"],
        "email": user.get("email", ""),
        "notificationTokens": tokens,
        "updatedAt": firestore.SERVER_TIMESTAMP
    }, merge=True)
    return success(message="Notification permission/token saved.")

@app.route("/api/notification-token", methods=["DELETE"])
@login_required
def delete_token(user):
    body = request.get_json(silent=True) or {}
    token = str(body.get("token", "")).strip()
    ref = db.collection("users").document(user["uid"])
    doc = ref.get()
    if doc.exists:
        data = doc.to_dict() or {}
        tokens = data.get("notificationTokens", [])
        if isinstance(tokens, list):
            ref.set({"notificationTokens": [x for x in tokens if x != token]}, merge=True)
    return success(message="Token removed.")

@app.route("/api/esp/register", methods=["POST"])
@login_required
def register_esp(user):
    body = request.get_json(silent=True) or {}
    device_id = str(body.get("device_id", "")).strip()
    if not device_id:
        return error("device_id is required.")

    ref = db.collection("esp_devices").document(device_id)
    existing = ref.get()
    if existing.exists:
        old = existing.to_dict() or {}
        if old.get("owner_uid") and old["owner_uid"] != user["uid"]:
            return error("This ESP belongs to another user.", 403)

    data = {
        "device_id": device_id,
        "owner_uid": user["uid"],
        "name": str(body.get("name", device_id)).strip(),
        "location": str(body.get("location", "")).strip(),
        "fire": False,
        "status": "normal",
        "updatedAt": firestore.SERVER_TIMESTAMP
    }
    if not existing.exists:
        data["registeredAt"] = firestore.SERVER_TIMESTAMP
    ref.set(data, merge=True)
    return success(message="ESP8266 registered.", device_id=device_id)

@app.route("/api/esp/devices")
@login_required
def devices(user):
    result = []
    for doc in db.collection("esp_devices").where("owner_uid", "==", user["uid"]).stream():
        item = doc.to_dict() or {}
        item["id"] = doc.id
        result.append(item)
    return success(devices=result)

@app.route("/api/esp/status", methods=["POST"])
@esp_required
def esp_status():
    body = request.get_json(silent=True) or {}
    device_id = str(body.get("device_id", "")).strip()
    if not device_id:
        return error("device_id is required.")

    ref = db.collection("esp_devices").document(device_id)
    doc = ref.get()
    if not doc.exists:
        return error("ESP device is not registered.", 404)

    old = doc.to_dict() or {}
    old_fire = fire_value(old.get("fire", False))
    fire = fire_value(body.get("fire", False))

    update = {
        "fire": fire,
        "status": "fire" if fire else "normal",
        "updatedAt": firestore.SERVER_TIMESTAMP
    }
    if "temperature" in body:
        update["temperature"] = body["temperature"]
    if "smoke" in body:
        update["smoke"] = body["smoke"]
    ref.set(update, merge=True)

    notification = {"sent": 0, "removed": 0}
    if fire and not old_fire:
        owner_uid = old.get("owner_uid")
        if owner_uid:
            notification = send_fire_notification(owner_uid, device_id)

    return success(
        message="ESP status updated.",
        device_id=device_id,
        fire=fire,
        notification=notification
    )

@app.route("/api/esp/status/<device_id>")
@login_required
def device_status(user, device_id):
    doc = db.collection("esp_devices").document(device_id).get()
    if not doc.exists:
        return error("Device not found.", 404)
    data = doc.to_dict() or {}
    if data.get("owner_uid") != user["uid"]:
        return error("Access denied.", 403)
    data["id"] = doc.id
    return success(device=data)

@app.route("/api/esp/reset/<device_id>", methods=["POST"])
@login_required
def reset_device(user, device_id):
    ref = db.collection("esp_devices").document(device_id)
    doc = ref.get()
    if not doc.exists:
        return error("Device not found.", 404)
    data = doc.to_dict() or {}
    if data.get("owner_uid") != user["uid"]:
        return error("Access denied.", 403)
    ref.set({
        "fire": False,
        "status": "normal",
        "updatedAt": firestore.SERVER_TIMESTAMP
    }, merge=True)
    return success(message="Alert reset.")

@app.route("/api/esp/<device_id>", methods=["DELETE"])
@login_required
def delete_device(user, device_id):
    ref = db.collection("esp_devices").document(device_id)
    doc = ref.get()
    if not doc.exists:
        return error("Device not found.", 404)
    data = doc.to_dict() or {}
    if data.get("owner_uid") != user["uid"]:
        return error("Access denied.", 403)
    ref.delete()
    return success(message="Device deleted.")

@app.route("/api/test-notification", methods=["POST"])
@login_required
def test_notification(user):
    ref = db.collection("users").document(user["uid"])
    doc = ref.get()
    data = doc.to_dict() if doc.exists else {}
    tokens = data.get("notificationTokens", [])
    if not isinstance(tokens, list):
        tokens = []

    sent, removed = 0, []
    for token in tokens:
        try:
            messaging.send(messaging.Message(
                notification=messaging.Notification(
                    title="🔥 Smart Fire Guard",
                    body="Test notification received successfully."
                ),
                data={"type": "test"},
                token=token
            ))
            sent += 1
        except (messaging.UnregisteredError, messaging.SenderIdMismatchError):
            removed.append(token)
        except Exception as exc:
            print("Test notification error:", exc)

    if removed:
        ref.set({"notificationTokens": [x for x in tokens if x not in removed]}, merge=True)

    return success(sent=sent, removed=len(removed))

@app.errorhandler(404)
def not_found(_):
    return jsonify({"success": False, "error": "Route not found."}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False)
