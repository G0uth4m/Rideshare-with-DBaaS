from kazoo.client import KazooClient
import logging
from dbaas.orchestrator.config import client
import time
import sys
import random
import string


def bring_up_new_worker_container(slave_name, db_name):
    print("[+] Starting(A) container: " + db_name, file=sys.stdout)
    client.containers.run(
        image="mongo:3.6.3",
        network="ubuntu_backend",
        name=db_name,
        hostname=db_name,
        detach=True,
        remove=False
    )

    time.sleep(5)

    print("[+] Starting(A) container: " + slave_name, file=sys.stdout)
    client.containers.run(
        image="master:latest",
        command="python3 -u worker.py",
        environment={"DB_HOSTNAME": db_name, "WORKER_TYPE": "slave", "NODE_NAME": slave_name},
        entrypoint=["sh", "trap.sh"],
        hostname=slave_name,
        name=slave_name,
        network="ubuntu_backend",
        detach=True,
        remove=False
    )


def listdiff(l1, l2):
    if len(l1) > len(l2):
        for i in l1:
            if i not in l2:
                return i
    else:
        for i in l2:
            if i not in l1:
                return i


class ZooWatch:
    def __init__(self, zookeeper_hostname):
        logging.basicConfig()
        self.zk = KazooClient(hosts=zookeeper_hostname)
        self.zk.start()
        self.temp = []

    def start(self):
        print("[*] Starting zoo watch", file=sys.stdout)
        self.zk.ensure_path("/worker")

        @self.zk.ChildrenWatch("/worker")
        def callback_worker(workers):
            print("[*] Changes detected", file=sys.stdout)
            print(workers, self.temp)
            if len(workers) < len(self.temp):
                node = listdiff(self.temp, workers)
                print("[-] Node deleted: " + node, file=sys.stdout)
                print("[*] Current workers: " + str(workers), file=sys.stdout)
                if "slave" in node:
                    random_name = "".join(random.choices(string.ascii_uppercase + string.digits, k=7))
                    bring_up_new_worker_container(slave_name="slave" + random_name,
                                                  db_name="mongoslave" + random_name)
                else:
                    print("[-] Master failed", file=sys.stdout)
                    # TODO: Master election and create new slave container

            elif len(workers) > len(self.temp):
                print("[+] Node added: " + listdiff(self.temp, workers), file=sys.stdout)
                print("[*] Current workers: " + str(workers), file=sys.stdout)

            else:
                pass

            self.temp = workers

        while True:
            pass
