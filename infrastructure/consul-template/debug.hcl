consul {
  address = "127.0.0.1:8500"
}

template {
  source      = "infrastructure/consul-template/debug-service.ctmpl"
  destination = "/tmp/consul-debug.txt"
}
