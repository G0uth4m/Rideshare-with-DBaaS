#!/bin/sh -e

if [ $# != 2 ]; then
    echo "usage: sudo $0 <public-port> <path-private-socket>"
    echo "example: sudo $0 4444 /var/run/docker.sock"
    exit 0
fi

PUBLIC_PORT=$1
PRIVATE_SOCKET=$2
SOCAT_LOG=/tmp/socat-$PUBLIC_PORT.log

echo "--> socat forwarding:\n\t- from port: $PUBLIC_PORT\n\t- to socket: $PRIVATE_SOCKET"
echo "--> allowed ips:\n\t$(cat socat-allow)"
echo "--> logs: $SOCAT_LOG"

socat -d -d -lf $SOCAT_LOG \
        TCP4-LISTEN:$PUBLIC_PORT,reuseaddr,fork,tcpwrap=socat,allow-table=socat-allow,deny-table=socat-deny \
        UNIX-CONNECT:$PRIVATE_SOCKET

# chmod +x start_docker_engine.sh
# sudo ./start_docker_engine.sh 4444 /var/run/docker.sock >/dev/null 2>&1 &