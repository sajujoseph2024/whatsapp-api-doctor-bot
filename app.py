import os
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GUPSHUP_API_KEY = os.getenv("GUPSHUP_API_KEY")
GUPSHUP_SENDER = os.getenv("GUPSHUP_SENDER")

# Step 1: Ask OpenAI
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

# Step 2: Send reply via Gupshup
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

# Step 3: Webhook to receive messages
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    user_message = data.get("message")
    sender = data.get("sender")
    
    if not user_message or not sender:
        return jsonify({"error": "Invalid request"}), 400

    reply = ask_openai(user_message)
    send_whatsapp_reply(sender, reply)

    return jsonify({"status": "success", "reply": reply})

if __name__ == "__main__":
    app.run(port=5000)