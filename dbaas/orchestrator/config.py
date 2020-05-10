import docker

# docker inspect 8757b8f9a455 --format '{{ .NetworkSettings.Gateway }}'
rabbitmq_hostname = "rmq"
client = docker.DockerClient(base_url="tcp://172.17.0.1:4444")
zookeeper_hostname = "zoo:2181"
