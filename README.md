# RideShare 
Cloud Computing Project

## Cloud Deployment
Launch 3 EC2 instances - rides, users and dbaas\
Install docker in all of them
```
$ sudo apt update
$ sudo apt install docker docker.io docker-compose
```
### Users instance
```
$ cd users/
```
Edit config.py and give IP address of dbaas
```
$ nano config.py
```
Bring up container
```
$ sudo docker-compose up --build
```

### Rides instance
```
$ cd rides/
```
Edit config.py and give IP address of dbaas, load balancer and rides
```
$ nano config.py
```
Bring up container
```
$ sudo docker-compose up --build
```

### DBaaS instance
```
$ cd dbaas 
```
Make docker server a TCP service
```
$ sudo apt install socat
$ chmod +x start_docker_engine.sh
$ sudo ./start_docker_engine.sh 4444 /var/run/docker.sock >/dev/null 2>&1 &
```
Bring up containers
```
$ sudo docker-compose up --build
```
## Authors
* **Goutham** 
* **Monish Reddy**
* **Srujan**
* **Khamaroddin Sheikh**
