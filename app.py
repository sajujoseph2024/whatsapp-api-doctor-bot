import os
import requests
import traceback
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Environment variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-8b-8192")

GUPSHUP_API_KEY = os.getenv("GUPSHUP_API_KEY")
GUPSHUP_SENDER = os.getenv("GUPSHUP_SENDER")


# Function to get response from Groq (doctor assistant prompt)
def ask_groq(message):
    url = f"{GROQ_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    body = {
        "model": GROQ_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful and friendly virtual doctor assistant. You can offer general health advice, symptom suggestions, and wellness tips, but always remind the user to consult a real doctor for serious conditions."
            },
            {
                "role": "user",
                "content": message
            }
        ]
    }

    response = requests.post(url, headers=headers, json=body, timeout=10)

    # Improved logging clarity
    if response.status_code != 200:
        app.logger.error(f"Groq error ({response.status_code}): {response.text}")
        return f"⚠️ Groq API error ({response.status_code}): {response.json().get('error', {}).get('message', 'Unknown error')}"
    else:
        app.logger.info(f"Groq success ({response.status_code}): {response.text}")
        return response.json()["choices"][0]["message"]["content"]


# Function to send reply on WhatsApp via Gupshup
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
        "src.name": "Connectify"
    }
    response = requests.post(url, headers=headers, data=payload, timeout=10)
    return response.text


# Health check endpoint
@app.route("/", methods=["GET"])
def home():
    return "Hello from Render!", 200


# Webhook endpoint for Gupshup
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return jsonify({"status": "Webhook is live"}), 200

    try:
        data = request.get_json()
        app.logger.info(f"Incoming webhook data: {data}")

        # Validate Gupshup message
        if (
            data.get("type") == "message" and
            isinstance(data.get("payload"), dict) and
            "payload" in data["payload"] and
            "text" in data["payload"]["payload"] and
            "sender" in data["payload"] and
            "phone" in data["payload"]["sender"]
        ):
            user_message = data["payload"]["payload"]["text"]
            sender = data["payload"]["sender"]["phone"]

            reply = ask_groq(user_message)
            send_whatsapp_reply(sender, reply)

            return jsonify({"status": "success", "reply": reply}), 200
        else:
            return jsonify({"status": "ignored", "reason": "Invalid message structure"}), 200

    except Exception as e:
        app.logger.error("Webhook error:\n" + traceback.format_exc())
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500


# Start app on Render or local port
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
