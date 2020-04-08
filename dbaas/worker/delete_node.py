import logging
from kazoo.client import KazooClient

logging.basicConfig()

f = open("node_name.txt")
node = f.read()

zk = KazooClient(hosts='zoo:2181')
zk.start()

zk.delete(node)