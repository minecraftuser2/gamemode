from flask import Flask, render_template, request, jsonify, send_from_directory
import os, json, base64

app = Flask(__name__)

USERS_FILE = "users.json"
SUGGESTIONS_FILE = "suggestions.json"

DEMO_FOLDER = "demo"
GENERAL_FOLDER = "general"
VIP_FOLDER = "VIP"

def load_json(file):
    if not os.path.exists(file):
        return {}
    with open(file,"r") as f:
        return json.load(f)

def save_json(file, data):
    with open(file,"w") as f:
        json.dump(data,f,indent=2)

def encode_pw(pw):
    return base64.b64encode(pw.encode()).decode()

# -------------------
# Main page
# -------------------
@app.route("/")
def index():
    return render_template("index.html")

# -------------------
# Serve games dynamically
# -------------------
@app.route("/games/<tier>/<filename>")
def serve_game(tier, filename):
    folder = tier.lower()
    if folder not in [DEMO_FOLDER, GENERAL_FOLDER, VIP_FOLDER]:
        return "Invalid tier", 404
    if not os.path.exists(os.path.join(folder, filename)):
        return "Game not found", 404
    return send_from_directory(folder, filename)

# -------------------
# List games API
# -------------------
@app.route("/list-games/<tier>")
def list_games(tier):
    folder = tier.lower()
    if folder not in [DEMO_FOLDER, GENERAL_FOLDER, VIP_FOLDER]:
        return jsonify({"success": False, "games":[]})
    files = [f for f in os.listdir(folder) if f.endswith(".html")]
    games = [os.path.splitext(f)[0] for f in files]
    return jsonify({"success": True, "games": games})

# -------------------
# Register/Login
# -------------------
@app.route("/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    plan = data.get("plan","demo")
    users = load_json(USERS_FILE)

    if username in users:
        return jsonify({"success": False, "message": "User exists"})
    users[username] = {"password": encode_pw(password), "tier": plan}
    save_json(USERS_FILE, users)
    return jsonify({"success": True, "plan": plan})

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    users = load_json(USERS_FILE)
    if username not in users:
        return jsonify({"success": False, "message": "User not found"})
    if users[username]["password"] != encode_pw(password):
        return jsonify({"success": False, "message": "Incorrect password"})
    return jsonify({"success": True, "plan": users[username]["tier"]})

@app.route("/get-plan/<username>")
def get_plan(username):
    users = load_json(USERS_FILE)
    if username not in users:
        return jsonify({"success": False})
    return jsonify({"success": True, "plan": users[username]["tier"]})

# -------------------
# Fake PayPal webhook for subscriptions
# -------------------
@app.route("/paypal-webhook", methods=["POST"])
def paypal_webhook():
    data = request.json
    username = data.get("username")
    new_plan = data.get("plan")
    users = load_json(USERS_FILE)
    if username not in users:
        return jsonify({"success": False})
    users[username]["tier"] = new_plan
    save_json(USERS_FILE, users)
    return jsonify({"success": True})

# -------------------
# Game suggestion ($5)
# -------------------
@app.route("/suggestion", methods=["POST"])
def suggestion():
    data = request.json
    username = data.get("username")
    idea = data.get("idea")
    users = load_json(USERS_FILE)
    if username not in users or users[username]["tier"]=="demo":
        return jsonify({"success": False})
    suggestions = load_json(SUGGESTIONS_FILE)
    suggestions[username] = suggestions.get(username, [])
    suggestions[username].append({"idea": idea, "status":"pending"})
    save_json(SUGGESTIONS_FILE, suggestions)
    return jsonify({"success": True})

# -------------------
# Run server
# -------------------
if __name__=="__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
