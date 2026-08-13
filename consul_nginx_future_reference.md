# Consul + NGINX + Consul Template --- Setup and Operations Guide

## 1. Purpose

This document describes the local/on-prem-style demo architecture:

``` text
                    Browser / External Client
                              |
                              v
                         NGINX :8080
                              |
                 +------------+------------+
                 |                         |
                 v                         v
           auth-service               home-service
             :8001                    :8000
             :8002
                 ^                         ^
                 |                         |
                 +-----------+-------------+
                             |
                           Consul
                             ^
                             |
                    Service self-registration
                             |
                       Django services

                    Consul Template
                         watches
                           Consul
                             |
                             v
                     generates nginx.conf
                             |
                             v
                         NGINX reload
```

Consul is the service registry and health source. NGINX is the reverse
proxy/API gateway. Consul Template watches Consul and renders NGINX
configuration from the service information.

------------------------------------------------------------------------

# 2. Main responsibilities

## Consul

Consul maintains the service catalog:

``` text
service name
instance ID
address
port
health status
metadata/tags
```

Example:

``` text
auth-service
├── auth-service-8001 -> 127.0.0.1:8001 -> passing
└── auth-service-8002 -> 127.0.0.1:8002 -> passing

home-service
└── home-service-8000 -> 127.0.0.1:8000 -> passing
```

Consul health checks determine whether an instance is healthy.

## Application

Each service can self-register with Consul when it starts.

Example:

``` text
Auth starts on :8001
        |
        v
PUT registration to Consul
        |
        v
auth-service-8001
```

## Consul Template

Consul Template continuously watches Consul and renders a template
whenever relevant service data changes.

Example:

``` text
Consul:
auth-service -> 8001, 8002

        |

Consul Template

        |

nginx.conf:
upstream auth_service {
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
}
```

## NGINX

NGINX receives client traffic and proxies it to the upstream groups
generated from Consul data.

NGINX's `upstream` directive defines groups of backend servers, and
`proxy_pass` sends requests to the selected upstream. NGINX uses
round-robin load balancing by default for multiple upstream servers.

------------------------------------------------------------------------

# 3. Directory structure used by the demo

A recommended structure:

``` text
recon_service/
├── authentication-service/
│   └── backend/
│       ├── manage.py
│       └── auth_backend/
│
├── home-service/
│   └── backend/
│       ├── manage.py
│       └── home_backend/
│
├── infrastructure/
│   ├── nginx/
│   │   ├── nginx.conf
│   │   └── nginx.conf.ctmpl
│   │
│   └── consul-template/
│       └── consul-template.hcl
│
└── ...
```

Your exact Django project/app names can differ.

------------------------------------------------------------------------

# 4. Install Consul

On Ubuntu/Debian, HashiCorp provides an official APT repository.

After installation verify:

``` bash
consul version
```

Also verify the agent configuration if you are running Consul as a
service:

``` bash
sudo systemctl status consul
```

Start it with:

``` bash
sudo systemctl start consul
```

Enable it at boot:

``` bash
sudo systemctl enable consul
```

Verify the cluster:

``` bash
consul members
```

For the local demo, a single local agent is enough.

------------------------------------------------------------------------

# 5. Important Consul distinction: server process vs systemd service

During testing it is possible to have Consul running manually while:

``` bash
sudo systemctl status consul
```

shows:

``` text
inactive (dead)
```

Check the actual process:

``` bash
ps aux | grep '[c]onsul'
```

Check the HTTP API:

``` bash
curl -s http://127.0.0.1:8500/v1/status/leader
```

Do not start a second Consul agent blindly if one is already running.

For a cleaner long-term setup, prefer one clearly managed Consul
instance.

------------------------------------------------------------------------

# 6. Important Consul ports

Typical Consul ports include:

``` text
8500  HTTP API / UI
8600  DNS
8300  Server RPC
8301  LAN gossip
8302  WAN gossip
```

For this demo, the application registration code communicates with:

``` text
Consul HTTP API -> 127.0.0.1:8500
```

------------------------------------------------------------------------

# 7. Install Consul Template

Verify:

``` bash
consul-template -version
```

The template process needs access to the Consul HTTP API.

A basic config file can point to the Consul agent:

``` hcl
consul {
  address = "127.0.0.1:8500"
}

template {
  source      = "infrastructure/nginx/nginx.conf.ctmpl"
  destination = "infrastructure/nginx/nginx.conf"

  command = "sudo nginx -t && sudo systemctl reload nginx"
}
```

The exact command/path can be adapted to your permissions and deployment
layout.

------------------------------------------------------------------------

# 8. NGINX installation

Verify:

``` bash
nginx -v
```

Check configuration:

``` bash
sudo nginx -t
```

Start:

``` bash
sudo systemctl start nginx
```

Enable at boot:

``` bash
sudo systemctl enable nginx
```

Check:

``` bash
sudo systemctl status nginx
```

------------------------------------------------------------------------

# 9. NGINX port in this demo

Our gateway listens on:

``` text
8080
```

Check:

``` bash
sudo ss -lntp | grep :8080
```

The important point is:

``` text
Browser
   |
   v
localhost:8080
   |
   v
NGINX
```

------------------------------------------------------------------------

# 10. NGINX configuration

Current template pattern:

``` nginx
upstream auth_service {
{{ range service "auth-service" }}
server {{ .Address }}:{{ .Port }};
{{ end }}
}

upstream home_service {
{{ range service "home-service" }}
server {{ .Address }}:{{ .Port }};
{{ end }}
}

server {
    listen 8080;
    server_name localhost;

    location /api/auth/ {
        proxy_pass http://auth_service;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /api/home/ {
        proxy_pass http://home_service;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /api/contact/ {
        proxy_pass http://home_service;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

This means:

``` text
/api/auth/    -> auth-service
/api/home/    -> home-service
/api/contact/ -> home-service
```

The ports are NOT manually written in the template. Consul provides the
healthy instances and their ports.

------------------------------------------------------------------------

# 11. Service registration model

Each service should have:

``` text
Name
ID
Address
Port
Health Check
```

Example:

``` python
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
```

Install the Python dependency if necessary:

``` bash
python3 -m pip install requests
```

------------------------------------------------------------------------

# 12. Why service ID is important

Do NOT register multiple instances only as:

``` text
auth-service
```

Use unique instance IDs:

``` text
auth-service-8001
auth-service-8002
```

The distinction is:

``` text
Name = logical service
ID   = specific instance
```

Therefore:

``` text
auth-service
├── auth-service-8001
└── auth-service-8002
```

This allows multiple instances of the same logical service to coexist.

------------------------------------------------------------------------

# 13. Starting multiple Auth instances

Terminal 1:

``` bash
cd ~/Desktop/recon_service/authentication-service/backend

SERVICE_PORT=8001 \
python3 manage.py runserver 8001 --noreload
```

Terminal 2:

``` bash
cd ~/Desktop/recon_service/authentication-service/backend

SERVICE_PORT=8002 \
python3 manage.py runserver 8002 --noreload
```

The service registration should result in:

``` text
auth-service-8001 -> 8001
auth-service-8002 -> 8002
```

------------------------------------------------------------------------

# 14. Start Home

Example:

``` bash
cd ~/Desktop/recon_service/home-service/backend

SERVICE_PORT=8000 \
python3 manage.py runserver 8000 --noreload
```

Expected registration:

``` text
home-service-8000 -> 8000
```

------------------------------------------------------------------------

# 15. Verify Consul registration

List all services:

``` bash
consul catalog services
```

Check Auth:

``` bash
consul catalog service auth-service
```

Check Home:

``` bash
consul catalog service home-service
```

Check health:

``` bash
curl -s \
http://127.0.0.1:8500/v1/health/service/auth-service
```

And:

``` bash
curl -s \
http://127.0.0.1:8500/v1/health/service/home-service
```

Look for:

``` text
Status = passing
```

------------------------------------------------------------------------

# 16. Test the Django health endpoints directly

Auth:

``` bash
curl -i http://127.0.0.1:8001/health/
```

Second Auth:

``` bash
curl -i http://127.0.0.1:8002/health/
```

Home:

``` bash
curl -i http://127.0.0.1:8000/health/
```

All should return HTTP 200 with the expected health response.

------------------------------------------------------------------------

# 17. Start Consul Template

From the project root:

``` bash
cd ~/Desktop/recon_service
```

Start:

``` bash
consul-template \
-config infrastructure/consul-template/consul-template.hcl
```

Keep this process running during the demo.

It watches Consul and updates the generated NGINX configuration when
service information changes.

------------------------------------------------------------------------

# 18. Verify generated NGINX configuration

Look at:

``` bash
cat infrastructure/nginx/nginx.conf
```

For two Auth instances you should see:

``` nginx
upstream auth_service {
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
}
```

Home:

``` nginx
upstream home_service {
    server 127.0.0.1:8000;
}
```

------------------------------------------------------------------------

# 19. Validate NGINX

Always test before reload:

``` bash
sudo nginx -t
```

Expected:

``` text
syntax is ok
test is successful
```

Then:

``` bash
sudo systemctl reload nginx
```

If Consul Template is configured with a reload command, it can perform
this automatically after rendering.

------------------------------------------------------------------------

# 20. Test complete routing

Auth:

``` bash
curl -i -X POST \
http://127.0.0.1:8080/api/auth/login/ \
-H "Content-Type: application/json" \
-d '{"username":"user","password":"user123"}'
```

Home:

``` bash
curl -i http://127.0.0.1:8080/api/home/
```

Contact:

``` bash
curl -i http://127.0.0.1:8080/api/contact/
```

The flow is:

``` text
Client
  |
  v
NGINX :8080
  |
  +-- /api/auth/ ----> auth-service
  |                       |
  |                       +--> 8001
  |                       +--> 8002
  |
  +-- /api/home/ ----> home-service
                          |
                          +--> 8000
```

------------------------------------------------------------------------

# 21. Test dynamic instance addition

Start Auth on another port:

``` bash
SERVICE_PORT=9001 \
python3 manage.py runserver 9001 --noreload
```

The service registers:

``` text
auth-service-9001 -> 9001
```

Consul Template should detect the new instance.

Generated NGINX should eventually become:

``` nginx
upstream auth_service {
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
    server 127.0.0.1:9001;
}
```

No NGINX port needs to be manually edited.

------------------------------------------------------------------------

# 22. Test failure/removal

Stop one Auth instance:

``` text
Ctrl+C
```

For example, stop 8001.

Consul's health check should eventually fail.

Check:

``` bash
curl -s \
http://127.0.0.1:8500/v1/health/service/auth-service
```

The 8001 instance should no longer be passing.

Consul Template should update the generated NGINX configuration so only
healthy instances remain in the generated upstream.

------------------------------------------------------------------------

# 23. Important limitation of the current template

The current template explicitly contains:

``` text
auth-service
home-service
```

Therefore adding a completely new service such as:

``` text
payment-service
```

does NOT automatically create an NGINX route.

You would currently need to add its upstream and location.

This is because service discovery and gateway routing are different
concerns:

``` text
Consul:
"Where is payment-service?"

NGINX:
"What URL should map to payment-service?"
```

------------------------------------------------------------------------

# 24. Future target: fully dynamic service discovery

The desired architecture is:

``` text
New service
    |
    | self-register
    v
Consul
    |
    | all registered services
    v
Consul Template
    |
    | iterate over services
    | check exposure metadata
    | read route metadata
    v
Generated NGINX configuration
    |
    v
NGINX
```

A service can register metadata such as:

``` text
Name   = payment-service
Port   = 9000
Health = /health/
Route  = /api/payment/
Expose = true
```

Then the generic template can use that metadata.

For an internal service:

``` text
Name   = email-service
Port   = 9100
Health = /health/
Expose = false
```

Consul still knows the service, but the external NGINX gateway does not
expose it.

------------------------------------------------------------------------

# 25. External vs internal services

## External/API service

Example:

``` text
auth-service
Expose = true
Route = /api/auth/
```

Traffic:

``` text
Browser
   |
   v
NGINX
   |
   v
auth-service
```

## Internal service

Example:

``` text
email-service
Expose = false
```

Traffic:

``` text
auth-service
   |
   | discover email-service through Consul
   v
email-service
```

NGINX does not need to expose the email service.

------------------------------------------------------------------------

# 26. Troubleshooting checklist

## NGINX not running

Run:

``` bash
sudo nginx -t
```

Then:

``` bash
sudo systemctl status nginx --no-pager -l
```

Then:

``` bash
sudo journalctl -xeu nginx.service --no-pager | tail -50
```

Check port:

``` bash
sudo ss -lntp | grep :8080
```

------------------------------------------------------------------------

## Consul service not visible

Check:

``` bash
consul catalog services
```

Then:

``` bash
consul catalog service auth-service
```

Check API:

``` bash
curl -s \
http://127.0.0.1:8500/v1/health/service/auth-service
```

------------------------------------------------------------------------

## Service is registered but unhealthy

Test its health endpoint directly:

``` bash
curl -i http://127.0.0.1:<PORT>/health/
```

Common causes:

``` text
Wrong port
Wrong health URL
Django not running
Health endpoint returns non-200
Service registered with stale address
```

------------------------------------------------------------------------

## Duplicate service instance

List the registrations:

``` bash
consul catalog service auth-service
```

Remember:

``` text
Name = logical service
ID   = instance
```

If stale registrations exist, deregister using the actual ID:

``` bash
consul services deregister -id=<ACTUAL_SERVICE_ID>
```

Do not assume the service name is the ID.

------------------------------------------------------------------------

## Consul Template is not updating NGINX

Check:

``` bash
consul-template \
-config infrastructure/consul-template/consul-template.hcl
```

Look for template/render errors.

Then inspect:

``` bash
cat infrastructure/nginx/nginx.conf
```

Validate:

``` bash
sudo nginx -t
```

------------------------------------------------------------------------

# 27. Standard startup sequence

For a fresh local test, use this order:

### Terminal 1 --- Consul

``` bash
sudo systemctl start consul
```

Verify:

``` bash
consul members
```

### Terminal 2 --- Auth instance 1

``` bash
cd ~/Desktop/recon_service/authentication-service/backend

SERVICE_PORT=8001 \
python3 manage.py runserver 8001 --noreload
```

### Terminal 3 --- Auth instance 2

``` bash
cd ~/Desktop/recon_service/authentication-service/backend

SERVICE_PORT=8002 \
python3 manage.py runserver 8002 --noreload
```

### Terminal 4 --- Home

``` bash
cd ~/Desktop/recon_service/home-service/backend

SERVICE_PORT=8000 \
python3 manage.py runserver 8000 --noreload
```

### Terminal 5 --- Consul Template

``` bash
cd ~/Desktop/recon_service

consul-template \
-config infrastructure/consul-template/consul-template.hcl
```

### Terminal 6 --- NGINX

If not already running:

``` bash
sudo nginx -t
sudo systemctl start nginx
```

Otherwise:

``` bash
sudo nginx -t
sudo systemctl reload nginx
```

------------------------------------------------------------------------

# 28. Quick verification sequence

Run:

``` bash
consul members
```

``` bash
consul catalog services
```

``` bash
consul catalog service auth-service
```

``` bash
consul catalog service home-service
```

``` bash
sudo nginx -t
```

``` bash
sudo ss -lntp | grep :8080
```

Then:

``` bash
curl -i http://127.0.0.1:8080/api/home/
```

and:

``` bash
curl -i http://127.0.0.1:8080/api/contact/
```

Finally test login:

``` bash
curl -i -X POST \
http://127.0.0.1:8080/api/auth/login/ \
-H "Content-Type: application/json" \
-d '{"username":"user","password":"user123"}'
```

------------------------------------------------------------------------

# 29. Production considerations

The local demo uses:

``` text
127.0.0.1
Consul HTTP API
Django runserver
```

Do not treat these as production defaults.

For production:

-   Use a production Django application server such as
    Gunicorn/uWSGI/ASGI server as appropriate.
-   Use proper service addresses rather than localhost when services run
    on different hosts.
-   Run Consul in a highly available configuration rather than relying
    on one local server.
-   Prefer Consul client agents on workloads/VMs where appropriate.
-   Secure Consul API access with the organization's
    authentication/ACL/TLS design.
-   Use stable, unique service IDs.
-   Define proper health checks and deregistration behavior.
-   Secure NGINX and expose only intended routes.
-   Keep internal services separate from externally exposed services.
-   Automate registration through deployment/service startup rather than
    manual registration.

------------------------------------------------------------------------

# 30. Final architecture

``` text
                         EXTERNAL
                            |
                            v
                     +-------------+
                     |    NGINX    |
                     |   :8080     |
                     +------+------+
                            |
             +--------------+--------------+
             |                             |
             v                             v
       /api/auth/                    /api/home/
             |                             |
             v                             v
       auth-service                 home-service
        /       \                         |
       v         v                        v
    :8001      :8002                    :8000


                 SERVICE DISCOVERY
                         |
                         v
                    +---------+
                    | Consul  |
                    +----+----+
                         ^
                         |
              self-registration
                         |
             +-----------+-----------+
             |                       |
        Auth service            Home service


                 CONFIGURATION
                         |
                         v
                +----------------+
                | Consul Template|
                +-------+--------+
                        |
                        v
                  nginx.conf
                        |
                        v
                     NGINX
```

## Core rule to remember

``` text
Service registration:
"I am service X and I am running at address Y:port Z."

Consul:
"I store that information and track health."

Consul Template:
"I watch Consul and render configuration from that information."

NGINX:
"I receive gateway traffic and proxy it to the configured upstream."

Application:
"Internal services can use service discovery to find other internal services."
```

## Useful official references

-   Consul service discovery:
    https://developer.hashicorp.com/consul/docs/discover
-   Consul installation: https://developer.hashicorp.com/consul/install
-   Consul catalog:
    https://developer.hashicorp.com/consul/docs/concept/catalog
-   NGINX upstream/load balancing:
    https://nginx.org/en/docs/http/upstream.html
-   NGINX proxy module:
    https://nginx.org/en/docs/http/ngx_http_proxy_module.html
