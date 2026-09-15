import os
from datetime import datetime, timezone
from functools import wraps

from flask import Flask, jsonify, request
from dotenv import load_dotenv

import firebase_admin
from firebase_admin import credentials, firestore, auth, messaging


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

app = Flask(__name__)

SERVICE_ACCOUNT = os.getenv(
    "FIREBASE_SERVICE_ACCOUNT",
    "serviceAccountKey.json"
)

ESP_API_KEY = os.getenv(
    "ESP_API_KEY",
    "CHANGE_THIS_KEY"
)


# ============================================================
# FIREBASE INITIALIZATION
# ============================================================

if not firebase_admin._apps:

    cred = credentials.Certificate(
        SERVICE_ACCOUNT
    )

    firebase_admin.initialize_app(
        cred
    )


db = firestore.client()


# ============================================================
# HELPERS
# ============================================================

def now():
    return datetime.now(timezone.utc)


def get_bearer_token():

    header = request.headers.get(
        "Authorization",
        ""
    )

    if not header.startswith("Bearer "):
        return None

    return header.split(
        "Bearer ",
        1
    )[1].strip()


def authenticated(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        token = get_bearer_token()

        if not token:

            return jsonify({
                "success": False,
                "error": "Login required"
            }), 401

        try:

            decoded = auth.verify_id_token(
                token
            )

            request.firebase_user = decoded

            return function(
                *args,
                **kwargs
            )

        except Exception as error:

            print("Authentication error:", error)

            return jsonify({
                "success": False,
                "error": "Invalid or expired login"
            }), 401

    return wrapper


def current_uid():

    return request.firebase_user["uid"]


def user_ref(uid):

    return db.collection(
        "users"
    ).document(uid)


def device_ref(device_id):

    return db.collection(
        "esp_devices"
    ).document(device_id)


# ============================================================
# BASIC TEST
# ============================================================

@app.route("/")
def home():

    return jsonify({
        "success": True,
        "message": "Fire Detection API is running",
        "version": "1.0"
    })


@app.route("/api/health")
def health():

    return jsonify({
        "success": True,
        "server": "online"
    })


# ============================================================
# USER PROFILE
# ============================================================

@app.route(
    "/api/profile",
    methods=["GET"]
)
@authenticated
def get_profile():

    uid = current_uid()

    document = user_ref(uid).get()

    if not document.exists:

        profile = {
            "uid": uid,
            "email":
                request.firebase_user.get(
                    "email",
                    ""
                ),
            "name": "",
            "phone": "",
            "createdAt": now()
        }

        user_ref(uid).set(
            profile
        )

        return jsonify({
            "success": True,
            "profile": profile
        })

    return jsonify({
        "success": True,
        "profile": document.to_dict()
    })


@app.route(
    "/api/profile",
    methods=["POST"]
)
@authenticated
def update_profile():

    uid = current_uid()

    data = request.get_json(
        silent=True
    ) or {}

    name = str(
        data.get(
            "name",
            ""
        )
    ).strip()

    phone = str(
        data.get(
            "phone",
            ""
        )
    ).strip()

    if len(name) > 100:

        return jsonify({
            "success": False,
            "error": "Name is too long"
        }), 400

    if len(phone) > 30:

        return jsonify({
            "success": False,
            "error": "Phone number is too long"
        }), 400

    user_ref(uid).set({

        "uid": uid,

        "email":
            request.firebase_user.get(
                "email",
                ""
            ),

        "name": name,

        "phone": phone,

        "updatedAt": now()

    }, merge=True)

    return jsonify({
        "success": True,
        "message": "Profile updated"
    })


# ============================================================
# FCM NOTIFICATION TOKEN
# ============================================================

@app.route(
    "/api/notification-token",
    methods=["POST"]
)
@authenticated
def register_notification_token():

    uid = current_uid()

    data = request.get_json(
        silent=True
    ) or {}

    token = str(
        data.get(
            "token",
            ""
        )
    ).strip()

    if not token:

        return jsonify({
            "success": False,
            "error": "FCM token is required"
        }), 400

    if len(token) > 5000:

        return jsonify({
            "success": False,
            "error": "Invalid token"
        }), 400

    user_ref(uid).set({

        "notificationTokens":
            firestore.ArrayUnion([
                token
            ]),

        "updatedAt": now()

    }, merge=True)

    return jsonify({
        "success": True,
        "message": "Notification device registered"
    })


@app.route(
    "/api/notification-token",
    methods=["DELETE"]
)
@authenticated
def remove_notification_token():

    uid = current_uid()

    data = request.get_json(
        silent=True
    ) or {}

    token = str(
        data.get(
            "token",
            ""
        )
    ).strip()

    if token:

        user_ref(uid).set({

            "notificationTokens":
                firestore.ArrayRemove([
                    token
                ])

        }, merge=True)

    return jsonify({
        "success": True
    })


# ============================================================
# ESP DEVICE REGISTRATION
# ============================================================

@app.route(
    "/api/esp/register",
    methods=["POST"]
)
@authenticated
def register_esp():

    uid = current_uid()

    data = request.get_json(
        silent=True
    ) or {}

    device_id = str(
        data.get(
            "device_id",
            ""
        )
    ).strip()

    device_name = str(
        data.get(
            "device_name",
            "Fire Sensor"
        )
    ).strip()

    if not device_id:

        return jsonify({
            "success": False,
            "error": "device_id is required"
        }), 400

    if len(device_id) > 100:

        return jsonify({
            "success": False,
            "error": "Invalid device ID"
        }), 400

    device_ref(device_id).set({

        "device_id": device_id,

        "device_name": device_name,

        "owner_uid": uid,

        "fire": False,

        "online": True,

        "last_seen": now(),

        "created_at": now()

    }, merge=True)

    return jsonify({
        "success": True,
        "message": "ESP registered",
        "device_id": device_id
    })


@app.route(
    "/api/esp/devices",
    methods=["GET"]
)
@authenticated
def get_my_devices():

    uid = current_uid()

    query = db.collection(
        "esp_devices"
    ).where(
        "owner_uid",
        "==",
        uid
    ).stream()

    devices = []

    for document in query:

        data = document.to_dict()

        devices.append(data)

    return jsonify({
        "success": True,
        "devices": devices
    })


# ============================================================
# ESP AUTHENTICATION
# ============================================================

def esp_authenticated():

    key = request.headers.get(
        "X-ESP-KEY",
        ""
    )

    return (
        key and
        key == ESP_API_KEY
    )


# ============================================================
# SEND FIRE NOTIFICATION
# ============================================================

def send_fire_notification(
    owner_uid,
    device_id
):

    document = user_ref(
        owner_uid
    ).get()

    if not document.exists:
        return 0

    user_data = document.to_dict()

    tokens = user_data.get(
        "notificationTokens",
        []
    )

    if not tokens:
        return 0

    successful = 0

    invalid_tokens = []

    for token in tokens:

        message = messaging.Message(

            notification=
                messaging.Notification(

                    title=
                        "🔥 FIRE DETECTED!",

                    body=
                        "Fire has been detected by your ESP device."
                ),

            data={

                "type": "fire",

                "status": "detected",

                "device_id":
                    str(device_id)
            },

            token=token
        )

        try:

            messaging.send(
                message
            )

            successful += 1

        except Exception as error:

            print(
                "FCM error:",
                error
            )

            invalid_tokens.append(
                token
            )


    # Remove tokens that are no longer valid.

    if invalid_tokens:

        user_ref(
            owner_uid
        ).set({

            "notificationTokens":
                firestore.ArrayRemove(
                    invalid_tokens
                )

        }, merge=True)


    return successful


# ============================================================
# ESP FIRE STATUS
# ============================================================

@app.route(
    "/api/esp/status",
    methods=["POST"]
)
def esp_status():

    if not esp_authenticated():

        return jsonify({
            "success": False,
            "error": "Unauthorized ESP"
        }), 401

    data = request.get_json(
        silent=True
    ) or {}

    device_id = str(
        data.get(
            "device_id",
            ""
        )
    ).strip()

    fire = bool(
        data.get(
            "fire",
            False
        )
    )

    if not device_id:

        return jsonify({
            "success": False,
            "error": "device_id is required"
        }), 400


    reference = device_ref(
        device_id
    )

    document = reference.get()

    if not document.exists:

        return jsonify({
            "success": False,
            "error": "ESP device not registered"
        }), 404


    device = document.to_dict()

    owner_uid = device.get(
        "owner_uid"
    )

    if not owner_uid:

        return jsonify({
            "success": False,
            "error": "Device has no owner"
        }), 400


    old_fire = bool(
        device.get(
            "fire",
            False
        )
    )


    reference.set({

        "fire": fire,

        "online": True,

        "last_seen": now(),

        "last_status":
            "FIRE"
            if fire
            else "NORMAL"

    }, merge=True)


    # Notify only when the system changes
    # from NORMAL to FIRE.

    notification_sent = 0

    if fire and not old_fire:

        notification_sent = \
            send_fire_notification(
                owner_uid,
                device_id
            )


    return jsonify({

        "success": True,

        "device_id":
            device_id,

        "fire":
            fire,

        "notification_sent":
            notification_sent
    })


# ============================================================
# GET ESP STATUS
# ============================================================

@app.route(
    "/api/esp/status/<device_id>",
    methods=["GET"]
)
@authenticated
def get_esp_status(
    device_id
):

    uid = current_uid()

    document = device_ref(
        device_id
    ).get()

    if not document.exists:

        return jsonify({
            "success": False,
            "error": "Device not found"
        }), 404

    device = document.to_dict()

    if device.get(
        "owner_uid"
    ) != uid:

        return jsonify({
            "success": False,
            "error": "Access denied"
        }), 403

    return jsonify({
        "success": True,
        "device": device
    })


# ============================================================
# RESET FIRE STATUS
# ============================================================

@app.route(
    "/api/esp/reset/<device_id>",
    methods=["POST"]
)
@authenticated
def reset_fire(
    device_id
):

    uid = current_uid()

    reference = device_ref(
        device_id
    )

    document = reference.get()

    if not document.exists:

        return jsonify({
            "success": False,
            "error": "Device not found"
        }), 404


    device = document.to_dict()

    if device.get(
        "owner_uid"
    ) != uid:

        return jsonify({
            "success": False,
            "error": "Access denied"
        }), 403


    reference.set({

        "fire": False,

        "last_status":
            "NORMAL",

        "reset_at":
            now()

    }, merge=True)


    return jsonify({
        "success": True,
        "message": "Fire status reset"
    })


# ============================================================
# SERVER RUN
# ============================================================

if __name__ == "__main__":

    port = int(
        os.getenv(
            "PORT",
            "5000"
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=True
        )
