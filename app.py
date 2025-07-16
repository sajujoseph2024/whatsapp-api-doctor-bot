import os
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GUPSHUP_API_KEY = os.getenv("GUPSHUP_API_KEY")
GUPSHUP_SENDER = os.getenv("GUPSHUP_SENDER")

# Ask OpenAI for a response
def ask_openai(message):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    body = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": message}]
    }
    response = requests.post(url, headers=headers, json=body)
    return response.json()["choices"][0]["message"]["content"]

# Send reply via Gupshup WhatsApp API
def send_whatsapp_reply(to, message):
    url = "https://api.gupshup.io/sm/api/v1/msg"
    headers = {
        "apikey": GUPSHUP_API_KEY,
        "Content-Type": "application/x-www-form-urlencoded"
    }
    payload = {
        "channel": "whatsapp",
        "source": GUPSHUP_SENDER,
        "destination": to,
        "message": message,
        "src.name": "Connectify"  # your Gupshup bot name
    }
    response = requests.post(url, headers=headers, data=payload)
    return response.text

# ➕ Required root endpoint for Gupshup validation
@app.route("/", methods=["GET"])
def home():
    return "Hello from Render!", 200

# Webhook to receive messages from Gupshup
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return jsonify({"status": "Webhook is live"}), 200

    data = request.get_json()
    try:
        user_message = data["payload"]["payload"]["text"]
        sender = data["payload"]["sender"]["phone"]
    except (KeyError, TypeError):
        return jsonify({"error": "Invalid Gupshup payload"}), 400

    reply = ask_openai(user_message)
    send_whatsapp_reply(sender, reply)

    return jsonify({"status": "success", "reply": reply}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
