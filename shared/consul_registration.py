import requests


CONSUL_URL = "http://127.0.0.1:8500"


def register_with_consul(
    service_name,
    port,
    route,
    expose=True,
    health_path="/health/",
):
    service_id = f"{service_name}-{port}"

    payload = {
    "ID": service_id,
    "Name": service_name,
    "Address": "127.0.0.1",
    "Port": port,

    "Meta": {
        "route": route,
        "expose": str(expose).lower(),
    },

    "Check": {
        "HTTP": f"http://127.0.0.1:{port}{health_path}",
        "Interval": "10s",
        "Timeout": "5s",
    },
}

    response = requests.put(
        f"{CONSUL_URL}/v1/agent/service/register",
        json=payload,
        timeout=5,
    )

    response.raise_for_status()

    print(
        f"Registered {service_name} "
        f"ID={service_id} "
        f"port={port} "
        f"route={route} "
        f"expose={expose}"
    )