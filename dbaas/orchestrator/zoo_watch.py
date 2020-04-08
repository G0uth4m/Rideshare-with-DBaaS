from kazoo.client import KazooClient
import logging
from dbaas.orchestrator.config import zookeeper_hostname
from dbaas.orchestrator.scaling import bring_up_new_worker_container
import threading
import time

logging.basicConfig()

zk = KazooClient(hosts=zookeeper_hostname)
zk.start()

temp = []


def callback_slave(event):
    slaves = zk.get_children("/slave")
    for i in slaves:
        temp.remove(i)

    print("Node deleted: " + temp[0])
    print("A Slave failed")
    print(event)
    bring_up_new_worker_container(slave_name=temp[0], db_name="mongo" + temp[0])


def callback_master(event):
    print("Master failed")
    print(event)
    # TODO: Master election


def f1():
    while True:
        temp = zk.get_children("/slave")
        slaves = zk.get_children("/slave", watch=callback_slave)
        print(slaves)
        time.sleep(5)


def f2():
    while True:
        master = zk.get_children("/master", watch=callback_master)
        print(master)
        time.sleep(5)


t1 = threading.Thread(target=f1)
t2 = threading.Thread(target=f2)
t1.start()
t2.start()


