import schedule
from dbaas.orchestrator.config import client
from dbaas.orchestrator.db import get_requests_count
import math
import random
import string
import time
import sys


def bring_up_new_worker_container(self, slave_name, db_name):
    print("[+] Starting(S) container: " + db_name, file=sys.stdout)
    client.containers.run(
        image="mongo:3.6.3",
        network="ubuntu_backend",
        name=db_name,
        hostname=db_name,
        detach=True,
        remove=True
    )

    time.sleep(5)

    print("[+] Starting(S) container: " + slave_name, file=sys.stdout)
    client.containers.run(
        image="master:latest",
        command="python3 -u worker.py",
        environment={"DB_HOSTNAME": db_name, "WORKER_TYPE": "slave", "NODE_NAME": slave_name},
        entrypoint=["sh", "cleanup.sh"],
        hostname=slave_name,
        name=slave_name,
        network="ubuntu_backend",
        detach=True,
        remove=True
    )


def start_scaling():
    current_count = get_requests_count()
    containers = client.containers.list()
    current_slaves = 0
    for i in containers:
        if "slave" in i.name:
            current_slaves += 1

    if current_count == 0:
        no_of_slaves_to_be_present = 1
    else:
        no_of_slaves_to_be_present = (int(math.ceil(current_count/20.0))*20)//20

    if current_slaves//2 < no_of_slaves_to_be_present:
        # Scale out
        n = no_of_slaves_to_be_present - current_slaves//2
        for i in range(n):
            random_name = "".join(random.choices(string.ascii_uppercase + string.digits, k=7))
            slave_name = "slave" + random_name
            db_name = "mongo" + slave_name
            bring_up_new_worker_container(slave_name=slave_name, db_name=db_name)

    elif current_slaves//2 > no_of_slaves_to_be_present:
        # Scale in
        n = current_slaves//2 - no_of_slaves_to_be_present
        for i in range(n):
            random.choice(client.containers.list()).remove()

    f = open("requests_count.txt", "w")
    f.write("0")
    f.close()


schedule.every(2).minutes.do(start_scaling)

while 1:
    schedule.run_all()

