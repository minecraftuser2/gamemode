from flask import Flask, request, jsonify, render_template, send_from_directory
import sqlite3, os, base64, smtplib
from email.message import EmailMessage

app = Flask(__name__)

# -------------------
# Config
# -------------------
DB_FILE = "gamemode.db"  # SQLite database file

# Email settings (update with your info)
EMAIL_ADDRESS = "suggestionbot@gmail.com"  # sender email
EMAIL_PASSWORD = "bot123456"     # app-specific password or SMTP password
EMAIL_RECEIVER = "suggestionbox@gmail.com" # where suggestions go

def encode_pw(pw):
    return base64.b64encode(pw.encode()).decode()

# -------------------
# Database setup
# -------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            tier TEXT NOT NULL
        )
    """)
    # Suggestions table
    c.execute("""
        CREATE TABLE IF NOT EXISTS suggestions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            idea TEXT NOT NULL,
            email TEXT,
            status TEXT NOT NULL DEFAULT 'pending'
        )
    """)
    conn.commit()
    conn.close()

init_db()

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
    if not os.path.exists(folder):
        return jsonify({"games":[]})
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
    if not username or not password:
        return jsonify({"success": False, "message": "Enter username & password"})

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE username = ?", (username,))
    if c.fetchone():
        conn.close()
        return jsonify({"success": False, "message": "User already exists"})

    c.execute("INSERT INTO users (username, password, tier) VALUES (?, ?, ?)",
              (username, encode_pw(password), "demo"))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Registered! You are on demo tier."})

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT password, tier FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()
    if not row:
        return jsonify({"success": False, "message": "User not found"})
    pw, tier = row
    if pw != encode_pw(password):
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
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET tier=? WHERE username=?", (tier, username))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Subscription updated"})

# -------------------
# Game suggestions ($5)
# -------------------
@app.route("/suggestion", methods=["POST"])
def suggestion():
    data = request.get_json()
    username = data.get("username")
    idea = data.get("idea")
    email = data.get("email","")
    if not username or not idea:
        return jsonify({"success": False, "message": "Username & idea required"})

    # Check user tier
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT tier FROM users WHERE username=?", (username,))
    row = c.fetchone()
    if not row:
        conn.close()
        return jsonify({"success": False, "message": "User not found"})
    tier = row[0]
    if tier == "demo":
        conn.close()
        return jsonify({"success": False, "message": "Upgrade to submit a suggestion"})

    # Save suggestion in DB
    c.execute("INSERT INTO suggestions (username, idea, email) VALUES (?, ?, ?)",
              (username, idea, email))
    conn.commit()
    conn.close()

    # Send email notification
    try:
        msg = EmailMessage()
        msg['Subject'] = f'New Game Suggestion from {username}'
        msg['From'] = "SuggestionBot@gmail.com"
        msg['To'] = "gamemodeSuggestions@gmail.com"
        msg.set_content(f"Username: {username}\nEmail: {email}\nIdea: {idea}")

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
    except Exception as e:
        print("Error sending email:", e)

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
    port = int(os.environ.get("PORT", 5000))  # Render uses PORT, fallback 5000 locally
    app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)
