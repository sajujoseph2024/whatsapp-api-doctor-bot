import os
import requests
import traceback
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Load from .env
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-8b-8192")
GUPSHUP_API_KEY = os.getenv("GUPSHUP_API_KEY")
GUPSHUP_SENDER = os.getenv("GUPSHUP_SENDER")


# Call Groq API for response
def ask_groq(message):
    url = f"{GROQ_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    body = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": message}]
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


# Send message via Gupshup
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
        "src.name": "Connectify"  # Your Gupshup bot name
    }
    response = requests.post(url, headers=headers, data=payload)
    return response.text


# Root health check
@app.route("/", methods=["GET"])
def home():
    return "Hello from Render!", 200


# Webhook endpoint
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return jsonify({"status": "Webhook is live"}), 200

    try:
        data = request.get_json()
        app.logger.info(f"Incoming webhook data: {data}")

        if (
            data.get("type") == "message"
            and isinstance(data.get("payload"), dict)
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


# Run the Flask app
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
