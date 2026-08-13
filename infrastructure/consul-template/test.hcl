consul {
  address = "127.0.0.1:8500"
}

template {
  source      = "infrastructure/consul-template/services-test.ctmpl"
  destination = "/tmp/services-test.txt"
}
