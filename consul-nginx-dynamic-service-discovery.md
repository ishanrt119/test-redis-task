# Consul + NGINX Dynamic Service Discovery

## Overview

This document records the local proof-of-concept for dynamic service
discovery and NGINX routing using Consul, Consul Template, NGINX, and
self-registering services.

## Architecture

``` text
Application Services
        |
        | self-register
        v
      Consul
        |
        | discover healthy services + metadata
        v
 Consul Template
        |
        | {{ range services }}
        | expose=true -> generate route
        | expose=false -> ignore
        v
    nginx.conf
        |
        | nginx -t
        | reload
        v
      NGINX :8080
        |
        v
   Backend services
```

## Service Registration Convention

Each backend registers:

-   `Name`
-   unique `ID`
-   `Address`
-   `Port`
-   HTTP health check
-   `Meta.expose`
-   `Meta.route`

Example:

``` python
payload = {
    "ID": service_id,
    "Name": service_name,
    "Address": "127.0.0.1",
    "Port": port,
    "Meta": {
        "expose": str(expose).lower(),
        "route": route,
    },
    "Check": {
        "HTTP": f"http://127.0.0.1:{port}/health/",
        "Interval": "10s",
        "Timeout": "5s",
    },
}
```

Registration endpoint used in the POC:

``` text
http://127.0.0.1:8500/v1/agent/service/register
```

## Service IDs and Multiple Instances

Use a unique ID per instance:

``` text
auth-service-8001
auth-service-9000
auth-service-9005
```

The logical service name remains:

``` text
auth-service
```

Consul can therefore contain:

``` text
auth-service
├── 127.0.0.1:8001
├── 127.0.0.1:9000
└── 127.0.0.1:9005
```

The generic template adds healthy instances to one NGINX upstream.

## Exposure Policy

`Meta.expose=true` means the service can be exposed through NGINX.

Example:

``` text
auth-service
expose=true
route=/api/auth/
```

generates:

``` nginx
upstream auth_service {
    server 127.0.0.1:9000;
}

location /api/auth/ {
    proxy_pass http://auth_service;
}
```

`Meta.expose=false` means the service remains registered and
health-checked in Consul but is not exposed through NGINX.

Example:

``` text
email-service
expose=false
```

should produce no `email_service` upstream and no `/api/email/`
location.

## Routing Convention

Store the external route in:

``` text
Meta.route
```

Examples:

``` text
auth-service    -> /api/auth/
home-service    -> /api/home/
payment-service -> /api/payment/
```

The template reads the metadata and creates the NGINX `location`.

## Health Checks

Every service should expose:

``` text
GET /health/
```

Example response:

``` json
{"status": "healthy"}
```

Consul health check:

``` python
"Check": {
    "HTTP": f"http://127.0.0.1:{port}/health/",
    "Interval": "10s",
    "Timeout": "5s",
}
```

When an instance becomes unhealthy, it stops being returned as a healthy
service instance and the generated upstream can change.

## Generic Consul Template

The important design decision is that the template is written once.

It does **not** contain a hard-coded list such as:

``` text
auth-service
home-service
payment-service
```

Instead it uses:

``` gotemplate
{{ range services }}
```

The logic is:

``` text
for every service
    |
    v
read healthy instances
    |
    v
read ServiceMeta.expose
    |
    +-- false --> ignore
    |
    +-- true --> read ServiceMeta.route
                   |
                   +--> generate upstream
                   |
                   +--> generate location
```

The correct field discovered during testing with Consul Template v0.42.1
is:

``` gotemplate
.ServiceMeta
```

not:

``` gotemplate
.Meta
.Service.Meta
```

The debug output showed the returned object is a
`dependency.HealthService` with fields including:

``` text
Name
Address
Port
ServiceMeta
Tags
Status
```

## NGINX Variables

The generated configuration intentionally contains:

``` nginx
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
```

These are NGINX variables.

Consul Template evaluates:

``` gotemplate
{{ ... }}
```

while NGINX evaluates:

``` text
$host
$remote_addr
$proxy_add_x_forwarded_for
```

They should remain in the generated NGINX configuration.

## NGINX Port

The API gateway listens on:

``` text
8080
```

Example:

``` nginx
server {
    listen 8080;
    server_name localhost;
}
```

Example API URLs:

``` text
http://localhost:8080/api/auth/
http://localhost:8080/api/home/
http://localhost:8080/api/payment/
```

## Project Structure

The new project should be the source of truth:

``` text
recon_service1/
├── authentication-service/
│   └── backend/
├── home-service/
│   └── backend/
├── payment-service/
│   └── app.py
└── infrastructure/
    ├── nginx/
    │   └── nginx.conf
    └── consul-template/
        ├── nginx-dynamic.ctmpl
        └── dynamic-test.hcl
```

Do not make the new setup depend on the old `recon_service` directory.

## Testing Workflow

### Check Consul

``` bash
consul members
consul catalog services
```

### Check a service

``` bash
curl -s http://127.0.0.1:8500/v1/health/service/auth-service | python3 -m json.tool
```

Verify:

``` text
Port
Status
Meta.expose
Meta.route
```

### Run Consul Template during development

``` bash
cd ~/Desktop/recon_service1

consul-template -config infrastructure/consul-template/dynamic-test.hcl
```

In production this should be managed by systemd or another supervisor,
not left running manually in a terminal.

### Inspect generated NGINX

``` bash
cat ~/Desktop/recon_service1/infrastructure/nginx/nginx.conf
```

### Validate NGINX

``` bash
sudo nginx -t
```

### Inspect active configuration

``` bash
sudo nginx -T
```

### Start/reload NGINX

``` bash
sudo systemctl start nginx
sudo systemctl reload nginx
```

## Dynamic Instance Test

Suppose:

``` text
auth-service
├── 9000
└── 8001
```

When the `8001` instance is stopped:

``` text
8001 stops
   |
   v
Consul health check changes
   |
   v
Consul Template detects change
   |
   v
generated nginx.conf changes
```

Expected upstream:

``` nginx
upstream auth_service {
    server 127.0.0.1:9000;
}
```

This behavior was successfully observed in the POC: stopping an Auth
instance caused the generated NGINX configuration to change.

## New Service Test: Payment

A minimal Flask payment service was used to prove that a completely new
service can be added without editing the generic template.

Registration metadata:

``` text
Name   = payment-service
Port   = 9002
expose = true
route  = /api/payment/
```

Start:

``` bash
SERVICE_PORT=9002 python3 app.py
```

Expected generated configuration:

``` nginx
upstream payment_service {
    server 127.0.0.1:9002;
}

location /api/payment/ {
    proxy_pass http://payment_service;
}
```

No service-specific change to `nginx-dynamic.ctmpl` is required.

## Internal Email Service Test

An email service was tested with:

``` text
expose=false
```

Expected:

``` text
Consul:
    email-service exists

NGINX:
    no email_service upstream
    no /api/email/ location
```

This demonstrates that registration and external exposure are separate
concerns.

## Production Flow

The intended production flow is:

``` text
Service starts
      |
      v
Service self-registers with Consul
      |
      v
Consul stores address/port/health/metadata
      |
      v
Consul Template continuously watches Consul
      |
      v
Generic template renders nginx.conf
      |
      v
nginx -t
      |
      v
systemctl reload nginx
```

Consul Template should run as a long-running managed service, for
example through systemd.

The current command:

``` bash
consul-template -config ...
```

was only used for development/testing.

## Automatic NGINX Reload

The remaining production automation is to configure Consul Template to
run a controlled post-render command such as:

``` hcl
template {
    source      = "/etc/consul-template/nginx-dynamic.ctmpl"
    destination = "/etc/nginx/conf.d/recon-generated.conf"

    command = "nginx -t && systemctl reload nginx"
}
```

The exact production paths, service account, and permissions must be
configured securely.

Do not grant unrestricted privileged command execution to Consul
Template.

## Failure Scenarios

### Service stops

``` text
service stops
   |
   v
Consul health check fails
   |
   v
service is removed from healthy results
   |
   v
Consul Template regenerates
   |
   v
NGINX upstream loses that instance
```

### Service changes port and re-registers

``` text
old: 8001
new: 1000
```

The new service instance registers:

``` text
auth-service-1000
Port=1000
```

Consul becomes the source of truth and the generic template uses the new
port.

### Service changes port but fails to re-register

This cannot be solved by Consul Template.

If Consul still says:

``` text
auth-service -> 8001
```

Consul Template will use the information Consul has.

Therefore service registration must be part of the application's
startup/deployment lifecycle.

## Responsibility Model

### Application/service

Responsible for:

-   self-registration
-   correct address/port
-   health endpoint
-   `expose` metadata
-   `route` metadata
-   lifecycle/deregistration behavior

### Consul

Responsible for:

-   service catalog
-   health state
-   address/port
-   service metadata
-   discovery

### Consul Template

Responsible for:

-   watching Consul
-   iterating over services
-   applying generic routing rules
-   rendering NGINX configuration
-   triggering a controlled reload

### NGINX

Responsible for:

-   API gateway/reverse proxy
-   routing
-   upstream load balancing
-   forwarding headers

## Frontend Consideration

For this architecture, the API gateway mainly needs backend/API service
discovery.

The frontend can call:

``` text
/api/auth/
/api/home/
/api/payment/
```

through NGINX.

The frontend itself does not need to be registered in Consul simply
because it makes API calls.

## Production Checklist

-   [ ] Consul runs under systemd/container supervision
-   [ ] Backend services self-register
-   [ ] Unique service IDs are used
-   [ ] Health checks are configured
-   [ ] `Meta.expose` convention is standardized
-   [ ] `Meta.route` convention is standardized
-   [ ] One generic Consul Template is version controlled
-   [ ] Consul Template runs continuously under a supervisor
-   [ ] Generated NGINX configuration has controlled
    ownership/permissions
-   [ ] `nginx -t` runs before reload
-   [ ] NGINX reload is automatic after valid changes
-   [ ] Consul Template does not receive unrestricted root privileges
-   [ ] Service registration failures are observable
-   [ ] Deregistration behavior is defined
-   [ ] Logging and monitoring are configured
-   [ ] Rollback procedure exists

## Final Design

The target architecture is:

``` text
New Service
    |
    | self-register
    v
  Consul
    |
    | discover service + health + metadata
    v
Consul Template
    |
    | one generic template
    | no service-specific entries
    v
nginx.conf
    |
    | nginx -t
    v
NGINX reload
    |
    v
API Gateway
```

The key principle is:

> The template is created once. Services are added dynamically through
> self-registration; the generic template discovers them automatically.

The POC has successfully demonstrated self-registration, Consul
discovery, health checks, multiple instances, `expose=true/false`,
dynamic route metadata, and automatic regeneration of the NGINX
configuration when service instances change.
