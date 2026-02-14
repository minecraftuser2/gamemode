from flask import Flask, request, jsonify, render_template, send_from_directory
import json, os, base64

app = Flask(__name__)

USERS_FILE = os.path.join(os.path.dirname(__file__), "users.json")
SUGGESTIONS_FILE = os.path.join(os.path.dirname(__file__), "suggestions.json")

def load_json(file):
    if not os.path.exists(file): return {}
    with open(file,"r") as f: return json.load(f)

def save_json(file, data):
    with open(file,"w") as f: json.dump(data,f,indent=2)

def encode_pw(pw):
    return base64.b64encode(pw.encode()).decode()

# -------------------
# Routes
# -------------------

@app.route("/")
def index():
    return render_template("index.html")

# List games in folder
@app.route("/list-games/<tier>")
def list_games(tier):
    folder = tier.lower()
    if not os.path.exists(folder): return jsonify({"games":[]})
    files = [f.replace(".html","") for f in os.listdir(folder) if f.endswith(".html")]
    return jsonify({"games": files})

# -------------------
# User auth
# -------------------
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    if not username or not password: return jsonify({"success":False,"message":"Enter username & password"})
    
    users = load_json(USERS_FILE)
    if username in users: return jsonify({"success":False,"message":"User already exists"})
    
    users[username] = {"password": encode_pw(password), "tier":"demo"}
    save_json(USERS_FILE, users)
    return jsonify({"success":True,"message":"Registered! You are on demo tier."})

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    users = load_json(USERS_FILE)
    if username not in users: return jsonify({"success":False,"message":"User not found"})
    if users[username]["password"] != encode_pw(password):
        return jsonify({"success":False,"message":"Incorrect password"})
    return jsonify({"success":True,"plan":users[username]["tier"]})

# -------------------
# Fake PayPal webhook
# -------------------
@app.route("/paypal-webhook", methods=["POST"])
def paypal_webhook():
    data = request.get_json()
    username = data.get("username")
    tier = data.get("plan")
    users = load_json(USERS_FILE)
    if username not in users: return jsonify({"success":False,"message":"User not found"})
    users[username]["tier"] = tier
    save_json(USERS_FILE, users)
    return jsonify({"success":True,"message":"Subscription updated"})

# -------------------
# Game suggestions ($5)
# -------------------
@app.route("/suggestion", methods=["POST"])
def suggestion():
    data = request.get_json()
    user = data.get("username")
    idea = data.get("idea")
    email = data.get("email","")
    if not user or not idea: return jsonify({"success":False,"message":"Username & idea required"})
    
    users = load_json(USERS_FILE)
    if users[user]["tier"]=="demo":
        return jsonify({"success":False,"message":"Upgrade to submit a suggestion"})
    
    suggestions = load_json(SUGGESTIONS_FILE)
    if user not in suggestions: suggestions[user]=[]
    suggestions[user].append({"idea":idea,"email":email,"status":"pending"})
    save_json(SUGGESTIONS_FILE, suggestions)
    return jsonify({"success":True,"message":"Suggestion submitted!"})

# -------------------
# Serve games
# -------------------
@app.route("/games/<tier>/<filename>")
def serve_game(tier, filename):
    folder = tier.lower()
    return send_from_directory(folder, filename)

# -------------------
# Run
# -------------------
if __name__=="__main__":
    port = int(os.environ.get("PORT", 5000))  # Use Render's PORT, fallback to 5000 locally
app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)
