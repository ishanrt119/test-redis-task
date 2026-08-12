consul {
  address = "127.0.0.1:8500"
}

template {
  source      = "/home/ishant@rhythm.local/Desktop/recon_service/infrastructure/nginx/nginx.conf.ctmpl"
  destination = "/home/ishant@rhythm.local/Desktop/recon_service/infrastructure/nginx/nginx.conf"

  command = "echo 'NGINX configuration changed'"

  error_on_missing_key = true
}
