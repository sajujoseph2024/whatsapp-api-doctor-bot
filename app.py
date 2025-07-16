import os
import requests
import traceback
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

    response = requests.post(url, headers=headers, json=body, timeout=10)

    # Debug log
    try:
        app.logger.error(f"OpenAI response ({response.status_code}): {response.text}")
    except:
        pass

    if response.status_code == 200 and "choices" in response.json():
        return response.json()["choices"][0]["message"]["content"]
    else:
        error_msg = response.json().get("error", {}).get("message", "Unknown OpenAI API error")
        return f"⚠️ OpenAI API error: {error_msg}"

# Send WhatsApp reply using Gupshup
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
        "src.name": "Connectify"  # Replace with your Gupshup bot name
    }
    response = requests.post(url, headers=headers, data=payload, timeout=10)
    return response.text

# Render health check endpoint
@app.route("/", methods=["GET"])
def home():
    return "Hello from Render!", 200

# Gupshup webhook
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
            "payload" in data and
            isinstance(data["payload"], dict) and
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
            return jsonify({"status": "ignored", "reason": "Invalid or unsupported message structure"}), 200

    except Exception as e:
        app.logger.error("Webhook error:\n" + traceback.format_exc())
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

# Run app
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
