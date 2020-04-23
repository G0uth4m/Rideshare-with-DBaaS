from kazoo.client import KazooClient
import logging
import time
import sys


def start_listener(client, zookeeper_hostname):
    logging.basicConfig()
    zk = KazooClient(hosts=zookeeper_hostname)
    zk.start()

    while 1:
        killed_containers = client.containers.list(all=True, filters={"exited": "137"})
        for i in killed_containers:
            print("Removing killed container: " + i.name, file=sys.stdout)
            zk.delete("/worker/" + i.name)
            i.remove()
        time.sleep(3)
