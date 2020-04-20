from kazoo.client import KazooClient
import logging
from dbaas.orchestrator.config import client
import time
import sys
import random
import string
import threading


# sudo docker rm $(sudo docker ps -a | awk '{print $1}')

class ZooWatch:
    def __init__(self, zookeeper_hostname):
        logging.basicConfig()
        self.zk = KazooClient(hosts=zookeeper_hostname)
        self.zk.start()
        self.temp = []
        self.lock = threading.Lock()

    def callback_worker(self, event):
        self.lock.acquire()
        print(event, file=sys.stdout)
        workers = self.zk.get_children("/worker")
        print(workers, self.temp)
        if len(workers) < len(self.temp):
            for i in workers:
                self.temp.remove(i)

            print("[-] Node deleted: " + self.temp[0], file=sys.stdout)
            print("[*] Current workers: " + str(workers), file=sys.stdout)
            if "slave" in self.temp[0]:
                random_name = "".join(random.choices(string.ascii_uppercase + string.digits, k=7))
                self.bring_up_new_worker_container(slave_name="slave" + random_name, db_name="mongoslave" + random_name)
            else:
                print("[-] Master failed", file=sys.stdout)
                # TODO: Master election and create new slave container
        else:
            temp = workers.copy()
            for i in self.temp:
                workers.remove(i)
            print("[+] Node added: " + workers[0], file=sys.stdout)
            print("[*] Current workers: " + str(temp), file=sys.stdout)
        self.lock.release()

    def start(self):
        while True:
            try:
                self.temp = self.zk.get_children("/worker")
                time.sleep(10)
                self.zk.get_children("/worker", watch=self.callback_worker)
            except Exception as e:
                pass

    def bring_up_new_worker_container(self, slave_name, db_name):
        print("[+] Starting(A) container: " + db_name, file=sys.stdout)
        client.containers.run(
            image="mongo:3.6.3",
            network="ubuntu_backend",
            name=db_name,
            hostname=db_name,
            detach=True,
            remove=True
        )

        time.sleep(5)

        print("[+] Starting(A) container: " + slave_name, file=sys.stdout)
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
