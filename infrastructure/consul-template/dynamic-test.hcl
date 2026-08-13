consul {
  address = "127.0.0.1:8500"
}

template {
  source      = "infrastructure/consul-template/nginx-dynamic.ctmpl"
  destination = "/home/ishant@rhythm.local/Desktop/recon_service1/infrastructure/nginx/nginx.conf"
}