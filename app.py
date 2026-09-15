import os
import json
from datetime import datetime, timezone
from functools import wraps

from flask import Flask, jsonify, request

import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from firebase_admin import auth
from firebase_admin import messaging


# ============================================================
# FLASK APP
# ============================================================

app = Flask(__name__)


# ============================================================
# FIREBASE INITIALIZATION
# ============================================================

def initialize_firebase():

    # Accept either Render variable name.
    firebase_json = (
        os.environ.get("FIREBASE_SERVICE_ACCOUNT")
        or
        os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
    )

    if not firebase_json:
        raise RuntimeError(
            "FIREBASE_SERVICE_ACCOUNT is missing "
            "from Render Environment Variables"
        )

    # Sometimes JSON is accidentally pasted with
    # surrounding spaces/new lines.
    firebase_json = firebase_json.strip()

    try:
        service_account = json.loads(firebase_json)

    except json.JSONDecodeError as error:

        raise RuntimeError(
            "Firebase service-account JSON is invalid"
        ) from error

    if not firebase_admin._apps:

        firebase_credential = credentials.Certificate(
            service_account
        )

        firebase_admin.initialize_app(
            firebase_credential
        )


initialize_firebase()

db = firestore.client()


# ============================================================
# ESP API KEY
# ============================================================

ESP_API_KEY = os.environ.get(
    "ESP_API_KEY",
    ""
).strip()

if not ESP_API_KEY:

    raise RuntimeError(
        "ESP_API_KEY is missing from Render "
        "Environment Variables"
    )


# ============================================================
# TIME
# ============================================================

def current_time():

    return datetime.now(
        timezone.utc
    )


# ============================================================
# FIREBASE AUTHENTICATION
# ============================================================

def get_bearer_token():

    authorization = request.headers.get(
        "Authorization",
        ""
    )

    if not authorization.startswith(
        "Bearer "
    ):
        return None

    return authorization[
        7:
    ].strip()


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

            decoded_token = auth.verify_id_token(
                token
            )

            request.firebase_user = decoded_token

            return function(
                *args,
                **kwargs
            )

        except Exception as error:

            print(
                "Authentication error:",
                error
            )

            return jsonify({
                "success": False,
                "error":
                    "Invalid or expired login"
            }), 401

    return wrapper


def get_current_uid():

    return request.firebase_user["uid"]


# ============================================================
# FIRESTORE REFERENCES
# ============================================================

def user_ref(uid):

    return db.collection(
        "users"
    ).document(uid)


def esp_ref(device_id):

    return db.collection(
        "esp_devices"
    ).document(device_id)


# ============================================================
# BASIC ROUTES
# ============================================================

@app.route("/")
def home():

    return jsonify({
        "success": True,
        "name": "Smart Fire Guard",
        "message":
            "Fire detection server is running",
        "status": "online"
    })


@app.route("/api/health")
def health():

    return jsonify({
        "success": True,
        "status": "online"
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

    uid = get_current_uid()

    reference = user_ref(uid)

    document = reference.get()

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

            "createdAt":
                current_time()
        }

        reference.set(
            profile
        )

        return jsonify({
            "success": True,
            "profile": profile
        })

    return jsonify({

        "success": True,

        "profile":
            document.to_dict()
    })


@app.route(
    "/api/profile",
    methods=["POST"]
)
@authenticated
def update_profile():

    uid = get_current_uid()

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

        "updatedAt":
            current_time()

    }, merge=True)

    return jsonify({

        "success": True,

        "message":
            "Profile saved successfully"
    })


# ============================================================
# FCM NOTIFICATION DEVICE TOKEN
# ============================================================

@app.route(
    "/api/notification-token",
    methods=["POST"]
)
@authenticated
def add_notification_token():

    uid = get_current_uid()

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
            "error":
                "FCM token is required"
        }), 400

    if len(token) > 5000:

        return jsonify({
            "success": False,
            "error":
                "Invalid FCM token"
        }), 400

    user_ref(uid).set({

        "notificationTokens":
            firestore.ArrayUnion([
                token
            ]),

        "updatedAt":
            current_time()

    }, merge=True)

    return jsonify({

        "success": True,

        "message":
            "This device is registered for notifications"
    })


@app.route(
    "/api/notification-token",
    methods=["DELETE"]
)
@authenticated
def remove_notification_token():

    uid = get_current_uid()

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
        "success": True,
        "message":
            "Notification device removed"
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

    uid = get_current_uid()

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
            "error":
                "device_id is required"
        }), 400

    if len(device_id) > 100:

        return jsonify({
            "success": False,
            "error":
                "Invalid device ID"
        }), 400

    reference = esp_ref(
        device_id
    )

    existing = reference.get()

    # Don't allow User B to take User A's ESP.
    if existing.exists:

        existing_data = existing.to_dict()

        old_owner = existing_data.get(
            "owner_uid"
        )

        if old_owner != uid:

            return jsonify({
                "success": False,
                "error":
                    "This ESP is already registered "
                    "to another user"
            }), 403

    reference.set({

        "device_id":
            device_id,

        "device_name":
            device_name,

        "owner_uid":
            uid,

        "fire":
            False,

        "online":
            True,

        "last_status":
            "NORMAL",

        "last_seen":
            current_time(),

        "updated_at":
            current_time()

    }, merge=True)

    return jsonify({

        "success": True,

        "message":
            "ESP registered successfully",

        "device_id":
            device_id
    })


# ============================================================
# GET USER'S ESP DEVICES
# ============================================================

@app.route(
    "/api/esp/devices",
    methods=["GET"]
)
@authenticated
def get_my_esp_devices():

    uid = get_current_uid()

    documents = db.collection(
        "esp_devices"
    ).where(
        "owner_uid",
        "==",
        uid
    ).stream()

    devices = []

    for document in documents:

        data = document.to_dict()

        data["id"] = document.id

        devices.append(
            data
        )

    return jsonify({

        "success": True,

        "devices":
            devices
    })


# ============================================================
# ESP AUTHENTICATION
# ============================================================

def authenticate_esp():

    received_key = request.headers.get(
        "X-ESP-KEY",
        ""
    ).strip()

    return received_key == ESP_API_KEY


# ============================================================
# SEND FIRE NOTIFICATION
# ============================================================

def send_fire_notification(
    owner_uid,
    device_id
):

    reference = user_ref(
        owner_uid
    )

    document = reference.get()

    if not document.exists:

        print(
            "Notification user not found:",
            owner_uid
        )

        return 0

    user_data = document.to_dict()

    tokens = user_data.get(
        "notificationTokens",
        []
    )

    if not isinstance(
        tokens,
        list
    ):

        return 0

    if not tokens:

        print(
            "No registered notification devices"
        )

        return 0

    sent = 0

    invalid_tokens = []

    for token in tokens:

        try:

            message = messaging.Message(

                notification=
                    messaging.Notification(

                        title:
                            "🔥 FIRE DETECTED!",

                        body:
                            "Your Smart Fire Guard "
                            "detected a possible fire."
                    ),

                data={

                    "type":
                        "fire",

                    "status":
                        "detected",

                    "device_id":
                        str(device_id)
                },

                token=token
            )

            messaging.send(
                message
            )

            sent += 1

        except messaging.UnregisteredError:

            invalid_tokens.append(
                token
            )

        except messaging.SenderIdMismatchError:

            invalid_tokens.append(
                token
            )

        except Exception as error:

            print(
                "FCM notification error:",
                error
            )


    # Remove tokens that Firebase says
    # are no longer usable.

    if invalid_tokens:

        reference.set({

            "notificationTokens":
                firestore.ArrayRemove(
                    invalid_tokens
                )

        }, merge=True)


    print(
        "Notifications sent:",
        sent
    )

    return sent


# ============================================================
# ESP FIRE STATUS
# ============================================================

@app.route(
    "/api/esp/status",
    methods=["POST"]
)
def receive_esp_status():

    if not authenticate_esp():

        return jsonify({

            "success": False,

            "error":
                "Unauthorized ESP"
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


    fire_value = data.get(
        "fire",
        False
    )


    # Handle both JSON boolean and
    # simple "true"/"false" strings.

    if isinstance(
        fire_value,
        str
    ):

        fire = (
            fire_value.lower()
            in [
                "true",
                "1",
                "yes",
                "fire"
            ]
        )

    else:

        fire = bool(
            fire_value
        )


    if not device_id:

        return jsonify({

            "success": False,

            "error":
                "device_id is required"
        }), 400


    reference = esp_ref(
        device_id
    )

    document = reference.get()


    if not document.exists:

        return jsonify({

            "success": False,

            "error":
                "ESP is not registered"
        }), 404


    device = document.to_dict()


    owner_uid = device.get(
        "owner_uid"
    )


    if not owner_uid:

        return jsonify({

            "success": False,

            "error":
                "ESP has no owner"
        }), 400


    old_fire = bool(
        device.get(
            "fire",
            False
        )
    )


    reference.set({

        "fire":
            fire,

        "online":
            True,

        "last_seen":
            current_time(),

        "last_status":
            "FIRE"
            if fire
            else
            "NORMAL",

        "updated_at":
            current_time()

    }, merge=True)


    notification_count = 0


    # Send notification only when the state
    # changes from NORMAL to FIRE.

    if fire and not old_fire:

        notification_count = \
            send_fire_notification(
                owner_uid,
                device_id
            )


    return jsonify({

        "success":
            True,

        "device_id":
            device_id,

        "fire":
            fire,

        "notification_sent":
            notification_count
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

    uid = get_current_uid()

    document = esp_ref(
        device_id
    ).get()


    if not document.exists:

        return jsonify({

            "success": False,

            "error":
                "Device not found"
        }), 404


    device = document.to_dict()


    if device.get(
        "owner_uid"
    ) != uid:

        return jsonify({

            "success": False,

            "error":
                "You do not own this ESP"
        }), 403


    return jsonify({

        "success":
            True,

        "device":
            device
    })


# ============================================================
# RESET FIRE STATUS
# ============================================================

@app.route(
    "/api/esp/reset/<device_id>",
    methods=["POST"]
)
@authenticated
def reset_fire_status(
    device_id
):

    uid = get_current_uid()

    reference = esp_ref(
        device_id
    )

    document = reference.get()


    if not document.exists:

        return jsonify({

            "success": False,

            "error":
                "Device not found"
        }), 404


    device = document.to_dict()


    if device.get(
        "owner_uid"
    ) != uid:

        return jsonify({

            "success": False,

            "error":
                "You do not own this ESP"
        }), 403


    reference.set({

        "fire":
            False,

        "last_status":
            "NORMAL",

        "reset_at":
            current_time(),

        "updated_at":
            current_time()

    }, merge=True)


    return jsonify({

        "success":
            True,

        "message":
            "Fire status reset"
    })


# ============================================================
# DELETE ESP DEVICE
# ============================================================

@app.route(
    "/api/esp/<device_id>",
    methods=["DELETE"]
)
@authenticated
def delete_esp(
    device_id
):

    uid = get_current_uid()

    reference = esp_ref(
        device_id
    )

    document = reference.get()


    if not document.exists:

        return jsonify({

            "success": False,

            "error":
                "Device not found"
        }), 404


    device = document.to_dict()


    if device.get(
        "owner_uid"
    ) != uid:

        return jsonify({

            "success": False,

            "error":
                "You do not own this ESP"
        }), 403


    reference.delete()


    return jsonify({

        "success":
            True,

        "message":
            "ESP removed successfully"
    })


# ============================================================
# RENDER SERVER
# ============================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            "5000"
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
