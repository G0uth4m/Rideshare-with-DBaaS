from kazoo.client import KazooClient
import logging
from dbaas.orchestrator.scaling import bring_up_new_worker_container
import time
import sys


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
            bring_up_new_worker_container(slave_name=self.temp[0], db_name="mongo" + self.temp[0])
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
                print("/slave/" + str(slaves), file=sys.stdout)

                master = self.zk.get_children("/master", watch=self.callback_master)
                print("/master/" + str(master), file=sys.stdout)

                time.sleep(5)
            except Exception as e:
                print(e, file=sys.stdout)
