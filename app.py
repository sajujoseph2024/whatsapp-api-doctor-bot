import os
import json
import logging
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Load environment variables
GUPSHUP_API_KEY = os.getenv("GUPSHUP_API_KEY")
GUPSHUP_SENDER = os.getenv("GUPSHUP_SENDER")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL")
GROQ_MODEL = os.getenv("GROQ_MODEL")

# Prompt to guide the AI as a friendly doctor
SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "You are a compassionate and knowledgeable virtual doctor assistant. "
        "Greet the user politely. Offer helpful health guidance, suggest home remedies "
        "for mild issues, and always remind the user to consult a real doctor for serious concerns. "
        "Respond clearly and concisely, like a helpful doctor friend."
    )
}

def ask_groq(message):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            SYSTEM_PROMPT,
            {"role": "user", "content": message}
        ]
    }

    try:
        response = requests.post(
            f"{GROQ_BASE_URL}/chat/completions",
            headers=headers,
            json=payload
        )
        logging.info("Groq response (%s): %s", response.status_code, response.text)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return "Sorry, I'm currently unavailable. Please try again later."
    except Exception as e:
        logging.exception("Groq API error:")
        return "An error occurred while processing your request."

def send_whatsapp_message(to, message):
    payload = {
        "channel": "whatsapp",
        "source": GUPSHUP_SENDER,
        "destination": to,
        "message": message,
        "src.name": "Connectify"
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "apikey": GUPSHUP_API_KEY
    }

    response = requests.post(
        "https://api.gupshup.io/wa/api/v1/msg",
        data=payload,
        headers=headers
    )

    logging.info("Gupshup send message response: %s", response.text)

@app.route("/", methods=["GET"])
def home():
    return "Doctor Bot is alive", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    logging.info("Received webhook payload: %s", json.dumps(data))

    # Meta Format v3 structure
    try:
        message = data["entry"][0]["changes"][0]["value"]["messages"][0]
        user_message = message["text"]["body"]
        phone_number = message["from"]
    except (KeyError, IndexError) as e:
        logging.error("Malformed webhook payload: %s", e)
        return jsonify({"status": "ignored"}), 200

    logging.info(f"Received message: {user_message} from {phone_number}")

    # Get AI response
    ai_reply = ask_groq(user_message)

    # Send reply back
    send_whatsapp_message(phone_number, ai_reply)
    return jsonify({"status": "success"}), 200

if __name__ == "__main__":
    app.run(debug=True)
