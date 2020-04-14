from kazoo.client import KazooClient
import logging
from dbaas.orchestrator.config import client
import time
import sys


# sudo docker rm $(sudo docker ps -a | grep "zoo\|rabb\|slave" | awk '{print $1}')

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
            self.bring_up_new_worker_container(slave_name=self.temp[0], db_name="mongo" + self.temp[0])
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
                time.sleep(1)
                master = self.zk.get_children("/master", watch=self.callback_master)
                time.sleep(5)
            except Exception as e:
                pass

    def bring_up_new_worker_container(self, slave_name, db_name):
        try:
            slave = client.containers.get(slave_name)
            db = client.containers.get(db_name)
            while slave in client.containers.list() and db in client.containers.list():
                print("[*] Waiting for containers to stop", file=sys.stdout)
                time.sleep(1)
            slave.remove()
            db.remove()
        except Exception as e:
            print(e, file=sys.stdout)

        client.containers.run(
            image="master:latest",
            command="python3 -u worker.py",
            environment={"DB_HOSTNAME": db_name, "WORKER_TYPE": "slave", "NODE_NAME": slave_name},
            entrypoint=["sh", "cleanup.sh"],
            hostname=slave_name,
            name=slave_name,
            network="ubuntu_backend",
            detach=True
        )

        client.containers.run(
            image="mongo:latest",
            network="ubuntu_backend",
            name=db_name,
            hostname=db_name,
            detach=True
        )
