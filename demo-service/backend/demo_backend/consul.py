import os
import sys

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../")
)

print("DEBUG PROJECT_ROOT =", PROJECT_ROOT)
print("DEBUG EXISTS =", os.path.exists(PROJECT_ROOT))
print("DEBUG SHARED EXISTS =", os.path.exists(
    os.path.join(PROJECT_ROOT, "shared")
))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from shared.consul_registration import (
    register_with_consul as register_service
)


def register_with_consul():
    port = int(os.getenv("SERVICE_PORT", "8001"))

    register_service(
        service_name="home-service",
        port=port,
        route="/api/home/",
        expose=True,
    )