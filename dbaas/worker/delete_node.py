import logging
from kazoo.client import KazooClient
from dbaas.worker.config import zookeeper_hostname
import sys

logging.basicConfig()

f = open("node_name.txt")
node = f.read()

zk = KazooClient(hosts=zookeeper_hostname)
zk.start()

print("Deleting node: " + node, file=sys.stdout)
zk.delete(node)