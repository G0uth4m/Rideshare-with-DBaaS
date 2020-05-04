docker stop $(sudo docker ps | awk '{print $1}')
docker rm $(sudo docker ps -a | awk '{print $1}')
docker volume rm $(docker volume ls -q)
