import os
import requests
from flask import Flask, jsonify

app = Flask(__name__)

PORT = int(os.getenv("SERVICE_PORT", "9002"))
CONSUL_URL = "http://127.0.0.1:8500"

SERVICE_NAME = "payment-service"
SERVICE_ID = f"{SERVICE_NAME}-{PORT}"


def register_with_consul():
    payload = {
        "ID": SERVICE_ID,
        "Name": SERVICE_NAME,
        "Address": "127.0.0.1",
        "Port": PORT,
        "Meta": {
            "expose": "true",
            "route": "/api/payment/"
        },
        "Check": {
            "HTTP": f"http://127.0.0.1:{PORT}/health/",
            "Interval": "10s",
            "Timeout": "5s"
        }
    }

    response = requests.put(
        f"{CONSUL_URL}/v1/agent/service/register",
        json=payload,
        timeout=5
    )

    response.raise_for_status()

    print(f"Registered {SERVICE_NAME} on port {PORT}")


@app.get("/health/")
def health():
    return jsonify(status="healthy")


@app.get("/api/payment/")
def payment():
    return jsonify(
        service="payment-service",
        message="Payment service reached successfully"
    )


if __name__ == "__main__":
    register_with_consul()
    app.run(host="127.0.0.1", port=PORT)
