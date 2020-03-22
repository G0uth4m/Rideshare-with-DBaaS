from pymongo import MongoClient

client = MongoClient("mongodb://mongorides:27017/")
db = client["rideshare"]

rabbitmq_hostname = "rabbitmq"