import os
import json
from functools import wraps

from flask import Flask, request, jsonify, render_template
import firebase_admin
from firebase_admin import credentials, firestore, auth, messaging


# ============================================================
# APP CONFIGURATION
# ============================================================

app = Flask(__name__)

PORT = int(os.environ.get("PORT", 10000))
ESP_API_KEY = os.environ.get("ESP_API_KEY", "").strip()


# ============================================================
# FIREBASE INITIALIZATION
# ============================================================

def initialize_firebase():
    """
    Reads the Firebase Admin service-account JSON from Render.

    Render variable can be named either:
        FIREBASE_SERVICE_ACCOUNT
    or:
        FIREBASE_SERVICE_ACCOUNT_JSON
    """

    if firebase_admin._apps:
        return

    firebase_json = (
        os.environ.get("FIREBASE_SERVICE_ACCOUNT")
        or os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
    )

    if not firebase_json:
        raise RuntimeError(
            "Firebase service account environment variable is missing. "
            "Set FIREBASE_SERVICE_ACCOUNT in Render."
        )

    try:
        service_account_info = json.loads(firebase_json)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            "FIREBASE_SERVICE_ACCOUNT contains invalid JSON."
        ) from e

    try:
        cred = credentials.Certificate(service_account_info)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        raise RuntimeError(
            f"Firebase initialization failed: {e}"
        ) from e


initialize_firebase()
db = firestore.client()


# ============================================================
# BASIC HELPERS
# ============================================================

def json_error(message, status=400):
    return jsonify({
        "success": False,
        "error": message
    }), status


def json_success(data=None, status=200):
    response = {
        "success": True
    }

    if data:
        response.update(data)

    return jsonify(response), status


def get_bearer_token():
    header = request.headers.get("Authorization", "")

    if not header.startswith("Bearer "):
        return None

    return header[7:].strip()


def get_current_user():
    token = get_bearer_token()

    if not token:
        return None

    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception:
        return None


def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        user = get_current_user()

        if not user:
            return json_error(
                "Authentication required.",
                401
            )

        return function(user, *args, **kwargs)

    return wrapper


def esp_key_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if not ESP_API_KEY:
            return json_error(
                "ESP_API_KEY is not configured on the server.",
                500
            )

        supplied_key = request.headers.get("X-ESP-KEY", "")

        if supplied_key != ESP_API_KEY:
            return json_error(
                "Invalid ESP API key.",
                401
            )

        return function(*args, **kwargs)

    return wrapper


def convert_fire_value(value):
    """
    Converts common ESP8266 values into True/False.
    """

    if isinstance(value, bool):
        return value

    if isinstance(value, int):
        return value != 0

    if isinstance(value, str):
        value = value.strip().lower()

        if value in [
            "true",
            "1",
            "yes",
            "fire",
            "detected",
            "on"
        ]:
            return True

        if value in [
            "false",
            "0",
            "no",
            "normal",
            "off"
        ]:
            return False

    return False


# ============================================================
# FCM NOTIFICATION
# ============================================================

def send_fire_notification(uid, device_id):
    """
    Sends the fire notification only to FCM tokens belonging
    to the Firebase user who owns this ESP device.
    """

    user_ref = db.collection("users").document(uid)
    user_doc = user_ref.get()

    if not user_doc.exists:
        return {
            "sent": 0,
            "removed": 0
        }

    user_data = user_doc.to_dict() or {}

    tokens = user_data.get("notificationTokens", [])

    if not isinstance(tokens, list):
        tokens = []

    tokens = list(dict.fromkeys(
        str(token).strip()
        for token in tokens
        if str(token).strip()
    ))

    if not tokens:
        return {
            "sent": 0,
            "removed": 0
        }

    sent_count = 0
    removed_tokens = []

    for token in tokens:
        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title="🔥 FIRE ALERT",
                    body=f"Fire detected by device {device_id}."
                ),
                data={
                    "type": "fire_alert",
                    "device_id": str(device_id),
                    "fire": "true"
                },
                token=token
            )

            messaging.send(message)
            sent_count += 1

        except messaging.UnregisteredError:
            removed_tokens.append(token)

        except messaging.SenderIdMismatchError:
            removed_tokens.append(token)

        except Exception as e:
            # One bad token should not stop notifications
            # for other devices.
            print(f"FCM error: {e}")

    if removed_tokens:
        try:
            updated_tokens = [
                token for token in tokens
                if token not in removed_tokens
            ]

            user_ref.set(
                {
                    "notificationTokens": updated_tokens
                },
                merge=True
            )
        except Exception as e:
            print(f"Could not clean old FCM tokens: {e}")

    return {
        "sent": sent_count,
        "removed": len(removed_tokens)
    }


# ============================================================
# HOME / FRONTEND
# ============================================================

@app.route("/")
def home():
    """
    Loads templates/index.html if it exists.
    """

    try:
        return render_template("index.html")
    except Exception:
        return jsonify({
            "name": "Smart Fire Guard",
            "status": "online",
            "message": "Backend is running."
        })


@app.route("/dashboard")
def dashboard():
    try:
        return render_template("dashboard.html")
    except Exception:
        return jsonify({
            "success": True,
            "message": "Dashboard endpoint is working."
        })


@app.route("/profile")
def profile_page():
    try:
        return render_template("profile.html")
    except Exception:
        return jsonify({
            "success": True,
            "message": "Profile endpoint is working."
        })


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "success": True,
        "service": "Smart Fire Guard",
        "status": "online",
        "firebase": bool(firebase_admin._apps),
        "esp_api_key_configured": bool(ESP_API_KEY)
    })


# ============================================================
# USER PROFILE
# ============================================================

@app.route("/api/profile", methods=["GET"])
@login_required
def get_profile(user):
    uid = user["uid"]

    try:
        doc = db.collection("users").document(uid).get()

        if not doc.exists:
            return json_success({
                "profile": {
                    "uid": uid,
                    "email": user.get("email", ""),
                    "displayName": user.get("name", ""),
                    "phone": "",
                    "address": ""
                }
            })

        data = doc.to_dict() or {}

        # Do not expose notification tokens to frontend.
        data.pop("notificationTokens", None)

        data["uid"] = uid

        if "email" not in data:
            data["email"] = user.get("email", "")

        return json_success({
            "profile": data
        })

    except Exception as e:
        return json_error(
            f"Could not load profile: {e}",
            500
        )


@app.route("/api/profile", methods=["POST"])
@login_required
def save_profile(user):
    uid = user["uid"]

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return json_error("Invalid JSON data.")

    allowed_fields = [
        "displayName",
        "phone",
        "address",
        "city",
        "state",
        "emergencyContact"
    ]

    profile = {}

    for field in allowed_fields:
        if field in data:
            profile[field] = str(data[field]).strip()

    profile["uid"] = uid
    profile["email"] = user.get("email", "")
    profile["updatedAt"] = firestore.SERVER_TIMESTAMP

    try:
        db.collection("users").document(uid).set(
            profile,
            merge=True
        )

        return json_success({
            "message": "Profile saved successfully."
        })

    except Exception as e:
        return json_error(
            f"Could not save profile: {e}",
            500
        )


# ============================================================
# FCM DEVICE TOKEN
# ============================================================

@app.route("/api/notification-token", methods=["POST"])
@login_required
def save_notification_token(user):
    uid = user["uid"]

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return json_error("Invalid JSON data.")

    token = str(data.get("token", "")).strip()

    if not token:
        return json_error("FCM token is required.")

    user_ref = db.collection("users").document(uid)

    try:
        user_doc = user_ref.get()

        if user_doc.exists:
            user_data = user_doc.to_dict() or {}
            tokens = user_data.get("notificationTokens", [])

            if not isinstance(tokens, list):
                tokens = []
        else:
            tokens = []

        if token not in tokens:
            tokens.append(token)

        user_ref.set(
            {
                "uid": uid,
                "email": user.get("email", ""),
                "notificationTokens": tokens,
                "updatedAt": firestore.SERVER_TIMESTAMP
            },
            merge=True
        )

        return json_success({
            "message": "Notification token saved."
        })

    except Exception as e:
        return json_error(
            f"Could not save notification token: {e}",
            500
        )


@app.route("/api/notification-token", methods=["DELETE"])
@login_required
def delete_notification_token(user):
    uid = user["uid"]

    data = request.get_json(silent=True) or {}

    token = str(data.get("token", "")).strip()

    if not token:
        return json_error("FCM token is required.")

    user_ref = db.collection("users").document(uid)

    try:
        doc = user_ref.get()

        if not doc.exists:
            return json_success({
                "message": "Token was not registered."
            })

        user_data = doc.to_dict() or {}

        tokens = user_data.get("notificationTokens", [])

        if not isinstance(tokens, list):
            tokens = []

        tokens = [
            item for item in tokens
            if item != token
        ]

        user_ref.set(
            {
                "notificationTokens": tokens
            },
            merge=True
        )

        return json_success({
            "message": "Notification token removed."
        })

    except Exception as e:
        return json_error(
            f"Could not remove token: {e}",
            500
        )


# ============================================================
# ESP DEVICE REGISTRATION
# ============================================================

@app.route("/api/esp/register", methods=["POST"])
@login_required
def register_esp(user):
    uid = user["uid"]

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return json_error("Invalid JSON data.")

    device_id = str(data.get("device_id", "")).strip()

    if not device_id:
        return json_error("device_id is required.")

    if len(device_id) > 100:
        return json_error("device_id is too long.")

    device_ref = db.collection("esp_devices").document(device_id)

    try:
        existing = device_ref.get()

        if existing.exists:
            existing_data = existing.to_dict() or {}
            existing_owner = existing_data.get("owner_uid")

            if existing_owner and existing_owner != uid:
                return json_error(
                    "This ESP device already belongs to another user.",
                    403
                )

        device_data = {
            "device_id": device_id,
            "owner_uid": uid,
            "name": str(
                data.get("name", device_id)
            ).strip(),
            "location": str(
                data.get("location", "")
            ).strip(),
            "fire": False,
            "status": "normal",
            "registeredAt": firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.SERVER_TIMESTAMP
        }

        if existing.exists:
            device_data.pop("registeredAt", None)

        device_ref.set(
            device_data,
            merge=True
        )

        return json_success({
            "message": "ESP8266 registered successfully.",
            "device_id": device_id
        })

    except Exception as e:
        return json_error(
            f"Could not register ESP device: {e}",
            500
        )


# ============================================================
# GET USER'S ESP DEVICES
# ============================================================

@app.route("/api/esp/devices", methods=["GET"])
@login_required
def get_user_devices(user):
    uid = user["uid"]

    try:
        query = (
            db.collection("esp_devices")
            .where("owner_uid", "==", uid)
            .stream()
        )

        devices = []

        for document in query:
            device = document.to_dict() or {}
            device["id"] = document.id

            devices.append(device)

        return json_success({
            "devices": devices
        })

    except Exception as e:
        return json_error(
            f"Could not load devices: {e}",
            500
        )


# ============================================================
# ESP8266 SENDS FIRE STATUS
# ============================================================

@app.route("/api/esp/status", methods=["POST"])
@esp_key_required
def esp_status():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return json_error("Invalid JSON data.")

    device_id = str(
        data.get("device_id", "")
    ).strip()

    if not device_id:
        return json_error(
            "device_id is required."
        )

    if len(device_id) > 100:
        return json_error(
            "device_id is too long."
        )

    fire = convert_fire_value(
        data.get("fire", False)
    )

    temperature = data.get("temperature")
    smoke = data.get("smoke")

    device_ref = db.collection(
        "esp_devices"
    ).document(device_id)

    try:
        device_doc = device_ref.get()

        if not device_doc.exists:
            return json_error(
                "ESP device is not registered.",
                404
            )

        device_data = device_doc.to_dict() or {}

        owner_uid = device_data.get("owner_uid")

        if not owner_uid:
            return json_error(
                "ESP device has no owner.",
                400
            )

        old_fire = convert_fire_value(
            device_data.get("fire", False)
        )

        update_data = {
            "fire": fire,
            "status": "fire" if fire else "normal",
            "updatedAt": firestore.SERVER_TIMESTAMP
        }

        if temperature is not None:
            update_data["temperature"] = temperature

        if smoke is not None:
            update_data["smoke"] = smoke

        device_ref.set(
            update_data,
            merge=True
        )

        notification_result = {
            "sent": 0,
            "removed": 0
        }

        # Send notification only when the state changes
        # from normal -> fire.
        if fire and not old_fire:
            notification_result = send_fire_notification(
                owner_uid,
                device_id
            )

        return json_success({
            "message": "ESP status updated.",
            "device_id": device_id,
            "fire": fire,
            "notification": notification_result
        })

    except Exception as e:
        return json_error(
            f"Could not update ESP status: {e}",
            500
        )


# ============================================================
# GET ONE ESP STATUS
# ============================================================

@app.route(
    "/api/esp/status/<device_id>",
    methods=["GET"]
)
@login_required
def get_esp_status(user, device_id):
    uid = user["uid"]

    device_id = str(device_id).strip()

    if not device_id:
        return json_error(
            "device_id is required."
        )

    try:
        device_ref = db.collection(
            "esp_devices"
        ).document(device_id)

        doc = device_ref.get()

        if not doc.exists:
            return json_error(
                "Device not found.",
                404
            )

        device = doc.to_dict() or {}

        if device.get("owner_uid") != uid:
            return json_error(
                "You do not have access to this device.",
                403
            )

        device["id"] = doc.id

        return json_success({
            "device": device
        })

    except Exception as e:
        return json_error(
            f"Could not get device status: {e}",
            500
        )


# ============================================================
# RESET FIRE ALERT
# ============================================================

@app.route(
    "/api/esp/reset/<device_id>",
    methods=["POST"]
)
@login_required
def reset_fire(user, device_id):
    uid = user["uid"]

    device_id = str(device_id).strip()

    device_ref = db.collection(
        "esp_devices"
    ).document(device_id)

    try:
        doc = device_ref.get()

        if not doc.exists:
            return json_error(
                "Device not found.",
                404
            )

        device = doc.to_dict() or {}

        if device.get("owner_uid") != uid:
            return json_error(
                "You do not have access to this device.",
                403
            )

        device_ref.set(
            {
                "fire": False,
                "status": "normal",
                "updatedAt": firestore.SERVER_TIMESTAMP
            },
            merge=True
        )

        return json_success({
            "message": "Fire alert reset.",
            "device_id": device_id
        })

    except Exception as e:
        return json_error(
            f"Could not reset alert: {e}",
            500
        )


# ============================================================
# DELETE ESP DEVICE
# ============================================================

@app.route(
    "/api/esp/<device_id>",
    methods=["DELETE"]
)
@login_required
def delete_esp(user, device_id):
    uid = user["uid"]

    device_id = str(device_id).strip()

    device_ref = db.collection(
        "esp_devices"
    ).document(device_id)

    try:
        doc = device_ref.get()

        if not doc.exists:
            return json_error(
                "Device not found.",
                404
            )

        device = doc.to_dict() or {}

        if device.get("owner_uid") != uid:
            return json_error(
                "You do not have permission to delete this device.",
                403
            )

        device_ref.delete()

        return json_success({
            "message": "ESP device deleted."
        })

    except Exception as e:
        return json_error(
            f"Could not delete device: {e}",
            500
        )


# ============================================================
# TEST NOTIFICATION
# ============================================================

@app.route(
    "/api/test-notification",
    methods=["POST"]
)
@login_required
def test_notification(user):
    """
    Sends a test notification only to the currently
    logged-in user's registered browser/device tokens.
    """

    uid = user["uid"]

    user_ref = db.collection(
        "users"
    ).document(uid)

    try:
        doc = user_ref.get()

        if not doc.exists:
            return json_error(
                "User profile not found.",
                404
            )

        data = doc.to_dict() or {}

        tokens = data.get(
            "notificationTokens",
            []
        )

        if not isinstance(tokens, list):
            tokens = []

        sent = 0
        removed = []

        for token in tokens:
            try:
                message = messaging.Message(
                    notification=messaging.Notification(
                        title="🔥 Smart Fire Guard",
                        body="Test notification received successfully."
                    ),
                    data={
                        "type": "test"
                    },
                    token=token
                )

                messaging.send(message)
                sent += 1

            except messaging.UnregisteredError:
                removed.append(token)

            except messaging.SenderIdMismatchError:
                removed.append(token)

            except Exception as e:
                print(f"Test FCM error: {e}")

        if removed:
            tokens = [
                token for token in tokens
                if token not in removed
            ]

            user_ref.set(
                {
                    "notificationTokens": tokens
                },
                merge=True
            )

        return json_success({
            "message": "Test notification processed.",
            "sent": sent,
            "removed": len(removed)
        })

    except Exception as e:
        return json_error(
            f"Could not send test notification: {e}",
            500
        )


# ============================================================
# 404 HANDLER
# ============================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "error": "Route not found."
    }), 404


# ============================================================
# 500 HANDLER
# ============================================================

@app.errorhandler(500)
def server_error(error):
    return jsonify({
        "success": False,
        "error": "Internal server error."
    }), 500


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False
    )
