import logging
from kazoo.client import KazooClient
from dbaas.worker.config import zookeeper_hostname
import sys
import os

logging.basicConfig()
node = "/worker/" + os.environ["NODE_NAME"]
zk = KazooClient(hosts=zookeeper_hostname)
zk.start()

print("Deleting node: " + node, file=sys.stdout)
zk.delete(node)