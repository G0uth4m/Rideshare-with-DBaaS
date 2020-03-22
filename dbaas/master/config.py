from pymongo import MongoClient

client = MongoClient("mongodb://mongomaster:27017/")
db = client["rideshare"]

rabbitmq_hostname = "rabbitmq"