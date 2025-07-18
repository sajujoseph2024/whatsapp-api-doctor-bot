import os
import requests
import traceback
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Load environment variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-8b-8192")

GUPSHUP_API_KEY = os.getenv("GUPSHUP_API_KEY")
GUPSHUP_SENDER = os.getenv("GUPSHUP_SENDER")


# Ask Groq for a response with system prompt
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
                "content": (
                    "You are a friendly and knowledgeable virtual doctor assistant. "
                    "You help users with common health questions, symptoms, and wellness advice, "
                    "but always remind them to consult a real doctor for serious issues."
                )
            },
            {"role": "user", "content": message}
        ]
    }

    response = requests.post(url, headers=headers, json=body, timeout=10)

    # Debug response
    app.logger.error(f"Groq response ({response.status_code}): {response.text}")

    if response.status_code == 200 and "choices" in response.json():
        return response.json()["choices"][0]["message"]["content"]
    else:
        return f"⚠️ Groq API error: {response.json().get('error', {}).get('message', 'Unknown error')}"


# Send WhatsApp reply via Gupshup
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


# Health check
@app.route("/", methods=["GET"])
def home():
    return "Hello from Render!", 200


# Webhook handler
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return jsonify({"status": "Webhook is live"}), 200

    try:
        data = request.get_json()
        app.logger.info(f"Incoming webhook data: {data}")

        # Validate and extract message
        if (
            data.get("type") == "message"
            and "payload" in data
            and isinstance(data["payload"], dict)
            and "payload" in data["payload"]
            and "text" in data["payload"]["payload"]
            and "sender" in data["payload"]
            and "phone" in data["payload"]["sender"]
        ):
            user_message = data["payload"]["payload"]["text"]
            sender = data["payload"]["sender"]["phone"]

            reply = ask_groq(user_message)
            send_whatsapp_reply(sender, reply)

            return jsonify({"status": "success", "reply": reply}), 200
        else:
            return jsonify({"status": "ignored", "reason": "Invalid or unsupported message structure"}), 200

    except Exception as e:
        app.logger.error("Webhook error:\n" + traceback.format_exc())
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500


# Run locally (for dev only)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
