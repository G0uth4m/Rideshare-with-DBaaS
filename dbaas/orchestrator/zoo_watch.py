from kazoo.client import KazooClient
import logging
from config import client
import time
import sys
import random
import string
import socket


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
        image="slave:latest",
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
        self.master_db_name = "mongomaster"

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
                    killed_containers = [i.name for i in client.containers.list(all=True, filters={"exited": "137"})]

                    if node in killed_containers:
                        slave_cnt = client.containers.get(node)
                        slave_db_cnt = client.containers.get("mongo" + node)
                        slave_cnt.remove()
                        slave_db_cnt.remove()
                        random_name = "".join(random.choices(string.ascii_lowercase + string.digits, k=7))
                        bring_up_new_worker_container(
                            slave_name="slave" + random_name,
                            db_name="mongoslave" + random_name
                        )
                    else:
                        print("[*] Scaling down - removing " + node)
                        print("[*] Or newly elected master is deleting its old node")
                else:
                    print("[-] Master failed", file=sys.stdout)
                    master_cnt = client.containers.get("master")
                    master_db_cnt = client.containers.get(self.master_db_name)
                    master_cnt.remove()
                    master_db_cnt.remove()
                    slave_pids = {}
                    for i in client.containers.list():
                        if "slave" in i.name and "mongo" not in i.name:
                            slave_pids[i.attrs["State"]["Pid"]] = i.name
                            new_leader = slave_pids[min(slave_pids.keys())]
                            s = socket.socket()
                            s.connect((new_leader, 23456))
                            s.send("You are now the master".encode())
                            s.close()
                            self.master_db_name = "mongo" + new_leader
                    time.sleep(5)
                    random_name = "".join(random.choices(string.ascii_lowercase + string.digits, k=7))
                    bring_up_new_worker_container(
                        slave_name="slave" + random_name,
                        db_name="mongoslave" + random_name
                    )

            elif len(workers) > len(self.temp):
                print("[+] Node added: " + listdiff(self.temp, workers), file=sys.stdout)
                print("[*] Current workers: " + str(workers), file=sys.stdout)

            else:
                pass

            self.temp = workers

        while True:
            pass
