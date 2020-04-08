#!/bin/bash

#Define cleanup procedure
cleanup() {
    python3 delete_node.py
}

#Trap SIGTERM
trap 'cleanup' TERM

#Execute a command
"${@}" &

#Wait
wait $!