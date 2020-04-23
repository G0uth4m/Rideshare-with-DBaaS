#!/bin/bash

#Define cleanup procedure
cleanup() {
    python3 cleanup.py
}

#Trap SIGTERM
trap 'cleanup' TERM

#Execute a command
"${@}" &

#Wait
wait $!