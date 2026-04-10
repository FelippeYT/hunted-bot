from flask import Flask, jsonify, render_template_string
import json

app = Flask(__name__)

FILE = "players.json"

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Bot Dashboard</title>
    <meta http-equiv="refresh" content="10">
    <style>
        body { background:#0f0f0f; color:white; font-family:Arial; }
        .box { padding:20px; }
        .player { padding:5px; border-bottom:1px solid #333; }
    </style>
</head>
<body>
    <div class="box">
        <h1>🔥 Tracker Dashboard</h1>
        <h3>Players monitorados:</h3>
        {% for p in players %}
            <div class="player">{{p}}</div>
        {% endfor %}
    </div>
</body>
</html>
"""

@app.route("/")
def home():
    try:
        with open(FILE, "r") as f:
            players = json.load(f)
    except:
        players = []

    return render_template_string(HTML, players=players)

@app.route("/api")
def api():
    try:
        with open(FILE, "r") as f:
            players = json.load(f)
    except:
        players = []

    return jsonify(players)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
