import os
import requests


def register_with_consul():
    port = int(os.getenv("SERVICE_PORT", "8000"))

    service_id = f"auth-service-{port}"

    consul_url = "http://127.0.0.1:8500/v1/agent/service/register"

    payload = {
        "ID": service_id,
        "Name": "auth-service",
        "Address": "127.0.0.1",
        "Port": port,
        "Check": {
            "HTTP": f"http://127.0.0.1:{port}/health/",
            "Interval": "10s",
            "Timeout": "5s"
        }
    }

    response = requests.put(
        consul_url,
        json=payload,
        timeout=5
    )

    response.raise_for_status()

    print(
        f"Auth service registered: {service_id} on port {port}"
    )