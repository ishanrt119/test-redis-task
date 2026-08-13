consul {
  address = "127.0.0.1:8500"
}

template {
  source      = "infrastructure/consul-template/metadata-test.ctmpl"
  destination = "/tmp/metadata-test.txt"
}
