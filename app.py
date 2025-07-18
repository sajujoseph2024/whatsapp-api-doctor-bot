import os
import requests
import traceback
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GUPSHUP_API_KEY = os.getenv("GUPSHUP_API_KEY")
GUPSHUP_SENDER = os.getenv("GUPSHUP_SENDER")


# Ask Groq (Mixtral) for a response
def ask_groq(message):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    body = {
        "model": "mixtral-8x7b-32768",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a helpful and knowledgeable AI health assistant. "
                    "You are friendly, empathetic, and explain things clearly. "
                    "Always provide safe, general health guidance. "
                    "If the user asks anything urgent, dangerous, or needing diagnosis, remind them "
                    "to consult a licensed medical professional. You are not a doctor."
                )
            },
            {
                "role": "user",
                "content": message
            }
        ]
    }

    response = requests.post(url, headers=headers, json=body, timeout=10)

    try:
        app.logger.error(f"Groq response ({response.status_code}): {response.text}")
    except:
        pass

    if response.status_code == 200 and "choices" in response.json():
        return response.json()["choices"][0]["message"]["content"]
    else:
        error_msg = response.json().get("error", {}).get("message", "Unknown Groq API error")
        return f"⚠️ Groq API error: {error_msg}"


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
        "src.name": "Connectify"  # your bot name
    }
    response = requests.post(url, headers=headers, data=payload, timeout=10)
    return response.text


# Home route (health check)
@app.route("/", methods=["GET"])
def home():
    return "Hello from Render!", 200


# Gupshup Webhook
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return jsonify({"status": "Webhook is live"}), 200

    try:
        data = request.get_json()
        app.logger.info(f"Incoming webhook data: {data}")

        # Validate and extract message
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
            return jsonify({"status": "ignored", "reason": "Invalid or unsupported message structure"}), 200

    except Exception as e:
        app.logger.error("Webhook error:\n" + traceback.format_exc())
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500


# Run the Flask app
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
