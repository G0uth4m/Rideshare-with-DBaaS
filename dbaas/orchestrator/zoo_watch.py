from kazoo.client import KazooClient
import logging
from dbaas.orchestrator.config import client
import time
import sys
import random
import string


# sudo docker rm $(sudo docker ps -a | awk '{print $1}')

class ZooWatch:
    def __init__(self, zookeeper_hostname):
        logging.basicConfig()
        self.zk = KazooClient(hosts=zookeeper_hostname)
        self.zk.start()
        self.temp = []

    def callback_slave(self, event):
        print(event, file=sys.stdout)
        slaves = self.zk.get_children("/slave")
        print(slaves, self.temp)
        if len(slaves) < len(self.temp):
            for i in slaves:
                self.temp.remove(i)

            print("Node deleted: " + self.temp[0], file=sys.stdout)
            print("Current slaves: " + str(slaves), file=sys.stdout)
            random_name = "".join(random.choices(string.ascii_uppercase + string.digits, k=7))
            self.bring_up_new_worker_container(slave_name="slave" + random_name, db_name="mongoslave" + random_name)
        else:
            for i in self.temp:
                slaves.remove(i)
            print("Node added: " + slaves[0], file=sys.stdout)
            print("Current slaves: " + str(slaves), file=sys.stdout)

    def callback_master(self, event):
        print(event, file=sys.stdout)
        master = self.zk.get_children("/master")
        if master:
            print("Master added: " + master[0], file=sys.stdout)
        else:
            print("Master failed", file=sys.stdout)
            print(event)
        # TODO: Master election and create new slave container

    def start(self):
        while True:
            try:
                self.temp = self.zk.get_children("/slave")
                slaves = self.zk.get_children("/slave", watch=self.callback_slave)
                time.sleep(10)
                master = self.zk.get_children("/master", watch=self.callback_master)
                time.sleep(10)
            except Exception as e:
                pass

    def bring_up_new_worker_container(self, slave_name, db_name):
        print("[+] Starting container: " + db_name)
        client.containers.run(
            image="mongo:3.6.3",
            network="ubuntu_backend",
            name=db_name,
            hostname=db_name,
            detach=True,
            remove=True
        )

        time.sleep(5)

        print("[+] Starting container: " + slave_name)
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
