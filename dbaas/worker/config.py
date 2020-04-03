from pymongo import MongoClient
import os

db_hostname = os.environ['DB_HOSTNAME']
client = MongoClient("mongodb://" + db_hostname + ":27017/")
db = client["rideshare"]

rabbitmq_hostname = "rabbitmq"
zookeeper_hostname = "zookeepeer"
