from flask import Flask, request, jsonify, render_template, send_from_directory
import os, psycopg2, base64

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise Exception("DATABASE_URL environment variable not set!")

def encode_pw(pw):
    return base64.b64encode(pw.encode()).decode()

# -------------------
# Initialize DB
# -------------------
def init_db():
    conn = psycopg2.connect(DATABASE_URL)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            tier TEXT NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS suggestions (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL,
            idea TEXT NOT NULL,
            email TEXT,
            status TEXT NOT NULL DEFAULT 'pending'
        )
    """)
    conn.commit()
    conn.close()
    print("Database initialized!")

init_db()

# -------------------
# Routes
# -------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/list-games/<tier>")
def list_games(tier):
    folder = tier.lower()
    if not os.path.exists(folder):
        return jsonify({"games": []})
    files = [f.replace(".html","") for f in os.listdir(folder) if f.endswith(".html")]
    return jsonify({"games": files})

# -------------------
# Auth
# -------------------
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"success": False, "message": "Enter username & password"})

    conn = psycopg2.connect(DATABASE_URL)
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE username=%s", (username,))
    if c.fetchone():
        conn.close()
        return jsonify({"success": False, "message": "User already exists"})

    c.execute("INSERT INTO users (username, password, tier) VALUES (%s, %s, %s)",
              (username, encode_pw(password), "demo"))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Registered! You are on demo tier."})

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    conn = psycopg2.connect(DATABASE_URL)
    c = conn.cursor()
    c.execute("SELECT password, tier FROM users WHERE username=%s", (username,))
    row = c.fetchone()
    conn.close()
    if not row:
        return jsonify({"success": False, "message": "User not found"})
    stored_pw, tier = row
    if stored_pw != encode_pw(password):
        return jsonify({"success": False, "message": "Incorrect password"})
    return jsonify({"success": True, "plan": tier})

# -------------------
# PayPal webhook
# -------------------
@app.route("/paypal-webhook", methods=["POST"])
def paypal_webhook():
    data = request.get_json()
    username = data.get("username")
    tier = data.get("plan")
    conn = psycopg2.connect(DATABASE_URL)
    c = conn.cursor()
    c.execute("UPDATE users SET tier=%s WHERE username=%s", (tier, username))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Subscription updated"})

# -------------------
# Game suggestions
# -------------------
@app.route("/suggestion", methods=["POST"])
def suggestion():
    data = request.get_json()
    user = data.get("username")
    idea = data.get("idea")
    email = data.get("email","")
    if not user or not idea:
        return jsonify({"success": False, "message": "Username & idea required"})

    conn = psycopg2.connect(DATABASE_URL)
    c = conn.cursor()
    c.execute("SELECT tier FROM users WHERE username=%s", (user,))
    row = c.fetchone()
    if not row or row[0]=="demo":
        conn.close()
        return jsonify({"success": False, "message": "Upgrade to submit a suggestion"})

    c.execute("INSERT INTO suggestions (username, idea, email) VALUES (%s,%s,%s)",
              (user, idea, email))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Suggestion submitted!"})

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
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
