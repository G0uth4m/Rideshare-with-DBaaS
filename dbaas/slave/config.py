from pymongo import MongoClient

client = MongoClient("mongodb://mongoslave:27017/")
db = client["rideshare"]

rabbitmq_hostname = "rabbitmq"