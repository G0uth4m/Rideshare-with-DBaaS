# docker commit --message="up scaling" slave slave_snapshot
# docker run --name=slave1 slave_snapshot
import schedule
from dbaas.orchestrator.config import client
from dbaas.orchestrator.db import get_requests_count
import math


def bring_up_new_worker_container(slave_name, db_name):
    client.containers.run(
        image="master:latest",
        command="python3 -u worker.py",
        environment={"DB_HOSTNAME": db_name, "WORKER_TYPE": "slave", "NODE_NAME": slave_name},
        hostname=slave_name,
        name=slave_name,
        network="backend",
        detach=True
    )

    client.containers.run(
        image="mongo:latest",
        network="backend",
        name=db_name,
        hostname=db_name,
        detach=True
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
            slave_name = "slave" + str((current_slaves//2) + i + 1)
            db_name = "mongo" + slave_name
            bring_up_new_worker_container(slave_name=slave_name, db_name=db_name)

    elif current_slaves//2 > no_of_slaves_to_be_present:
        # Scale in
        n = current_slaves//2 - no_of_slaves_to_be_present
        for i in range(n, 0, -1):
            client.containers.get("slave" + str(i)).stop()

    f = open("requests_count.txt", "w")
    f.write("0")
    f.close()


schedule.every(2).minutes.do(start_scaling)

