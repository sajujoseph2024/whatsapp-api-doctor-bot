import os
import requests
import traceback
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
GUPSHUP_API_KEY = os.getenv("GUPSHUP_API_KEY")
GUPSHUP_SENDER = os.getenv("GUPSHUP_SENDER")


# Ask OpenRouter (ChatGPT) for a response
def ask_openai(message):
    url = f"{OPENAI_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://whatsapp-api-doctor-bot-1.onrender.com",  # Recommended by OpenRouter
        "X-Title": "Connectify WhatsApp Bot"
    }
    body = {
        "model": "openchat/openchat-7b",  # Free good model; you can change to another supported one
        "messages": [{"role": "user", "content": message}]
    }

    response = requests.post(url, headers=headers, json=body, timeout=10)

    # Debug log
    try:
        app.logger.error(f"OpenRouter response ({response.status_code}): {response.text}")
    except:
        pass

    if response.status_code == 200 and "choices" in response.json():
        return response.json()["choices"][0]["message"]["content"]
    else:
        error_msg = response.json().get("error", {}).get("message", "Unknown error")
        return f"⚠️ OpenRouter API error: {error_msg}"


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
        "src.name": "Connectify"  # Your Gupshup app name
    }
    response = requests.post(url, headers=headers, data=payload, timeout=10)
    return response.text


# Health check (for Render)
@app.route("/", methods=["GET"])
def home():
    return "Hello from Render!", 200


# Gupshup Webhook handler
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return jsonify({"status": "Webhook is live"}), 200

    try:
        data = request.get_json()
        app.logger.info(f"Incoming webhook data: {data}")

        # Validate Gupshup payload
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

            reply = ask_openai(user_message)
            send_whatsapp_reply(sender, reply)

            return jsonify({"status": "success", "reply": reply}), 200
        else:
            return jsonify({"status": "ignored", "reason": "Invalid message structure"}), 200

    except Exception as e:
        app.logger.error("Webhook error:\n" + traceback.format_exc())
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500


# Run the Flask app locally (Render uses gunicorn)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
