from kazoo.client import KazooClient, KazooState
import logging
from dbaas.orchestrator.config import zookeeper_hostname
from dbaas.orchestrator.db import bring_up_new_worker_container

logging.basicConfig()

zk = KazooClient(hosts=zookeeper_hostname)
zk.start()


def callback_slave(event):
    bring_up_new_worker_container(slave_name="slave", db_name="mongoslave")
    print(event)


def callback_master(event):
    # TODO: Master election
    bring_up_new_worker_container(slave_name="slave", db_name="mongoslave")
    print(event)


slaves = zk.get_children("/slave", watch=callback_slave)
master = zk.get_children("/master", watch=callback_master)