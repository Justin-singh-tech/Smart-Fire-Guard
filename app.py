from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Prototype data: no SQL and no file handling.
owner = {
    "name": "",
    "phone": "",
    "email": "",
    "location": "",
    "device_id": ""
}

status = {
    "fire": False,
    "temperature": 32,
    "flame": "NORMAL",
    "extinguisher": "READY"
}

@app.route("/")
def home():
    return render_template("index.html", owner=owner, status=status)

@app.route("/register", methods=["POST"])
def register():
    data = request.form
    owner.update({
        "name": data.get("name", "").strip(),
        "phone": data.get("phone", "").strip(),
        "email": data.get("email", "").strip(),
        "location": data.get("location", "").strip(),
        "device_id": data.get("device_id", "").strip()
    })
    return jsonify({"ok": True, "message": "Owner registered successfully."})

@app.route("/status", methods=["GET"])
def get_status():
    return jsonify(status)

# Demo endpoint: your ESP32 can later send POST data here.
@app.route("/api/fire", methods=["POST"])
def fire_event():
    data = request.get_json(silent=True) or {}
    status["fire"] = bool(data.get("fire", True))
    status["temperature"] = data.get("temperature", 82 if status["fire"] else 32)
    status["flame"] = "DETECTED" if status["fire"] else "NORMAL"
    status["extinguisher"] = "ACTIVATED" if status["fire"] else "READY"
    return jsonify({"ok": True, "status": status})

@app.route("/api/test-fire", methods=["POST"])
def test_fire():
    status["fire"] = True
    status["temperature"] = 82
    status["flame"] = "DETECTED"
    status["extinguisher"] = "ACTIVATED"
    return jsonify({"ok": True, "status": status})

@app.route("/api/reset", methods=["POST"])
def reset():
    status["fire"] = False
    status["temperature"] = 32
    status["flame"] = "NORMAL"
    status["extinguisher"] = "READY"
    return jsonify({"ok": True, "status": status})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
