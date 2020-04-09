import os
from dbaas.worker.config import db, zookeeper_hostname
from datetime import datetime
from dbaas.worker.rpc_server import RpcServer
import sys
import logging
from kazoo.client import KazooClient
import subprocess


def writedb(request_data):
    if 'clear' in request_data:
        try:
            for i in request_data["collections"]:
                collection = db[i]
                collection.delete_many({})
            return "Response(status=200)"
        except Exception as e:
            print(e, file=sys.stdout)
            return "Response(status=400)"

    if 'delete' in request_data:
        try:
            delete = request_data['delete']
            column = request_data['column']
            collection = request_data['table']
        except KeyError as e:
            print(e, file=sys.stdout)
            return "Response(status=400)"

        try:
            query = {column: delete}
            collection = db[collection]
            x = collection.delete_one(query)
            if x.raw_result['n'] == 1:
                return "Response(status=200)"
            return "Response(status=400)"
        except Exception as e:
            print(e, file=sys.stdout)
            return "Response(status=400)"

    if 'update' in request_data:
        try:
            collection = request_data['table']
            where = request_data['where']
            array = request_data['update']
            data = request_data['data']
            operation = request_data['operation']
        except KeyError as e:
            print(e, file=sys.stdout)
            return "Response(status=400)"

        try:
            collection = db[collection]
            x = collection.update_one(where, {"$" + operation: {array: data}})
            if x.raw_result['n'] == 1:
                return "Response(status=200)"
            return "Response(status=400)"
        except Exception as e:
            print(e, file=sys.stdout)
            return "Response(status=400)"

    try:
        insert = request_data['insert']
        columns = request_data['columns']
        collection = request_data['table']
    except KeyError as e:
        print(e, file=sys.stdout)
        return "Response(status=400)"

    try:
        document = {}
        for i in range(len(columns)):
            if columns[i] == "timestamp":
                document[columns[i]] = convert_timestamp_to_datetime(insert[i])
            else:
                document[columns[i]] = insert[i]

        collection = db[collection]
        collection.insert_one(document)
        return "Response(status=201)"

    except Exception as e:
        print(e, file=sys.stdout)
        return "Response(status=400)"


def readdb(request_data):
    if 'count' in request_data:
        try:
            collection = db[request_data['table']]
            res = [collection.count_documents({})]
            return res
        except Exception as e:
            print(e, file=sys.stdout)
            return "Response(status=400)"

    try:
        table = request_data['table']
        columns = request_data['columns']
        where = request_data['where']
    except KeyError as e:
        print(e, file=sys.stdout)
        return "Response(status=400)"

    if "timestamp" in where:
        where["timestamp"]["$gt"] = convert_timestamp_to_datetime(where["timestamp"]["$gt"])

    filter = {}
    for i in columns:
        filter[i] = 1

    if 'many' in request_data:
        try:
            collection = db[table]
            res = []
            for i in collection.find(where, filter):
                if "timestamp" in i:
                    i["timestamp"] = convert_datetime_to_timestamp(i["timestamp"])
                res.append(i)

            return res
        except Exception as e:
            print(e, file=sys.stdout)
            return "Response(status=400)"

    try:
        collection = db[table]
        result = collection.find_one(where, filter)
        if "timestamp" in result:
            result["timestamp"] = convert_datetime_to_timestamp(result["timestamp"])
        return result
    except Exception as e:
        print(e, file=sys.stdout)
        return "Response(status=400)"


def convert_timestamp_to_datetime(time_stamp):
    day = int(time_stamp[0:2])
    month = int(time_stamp[3:5])
    year = int(time_stamp[6:10])
    seconds = int(time_stamp[11:13])
    minutes = int(time_stamp[14:16])
    hours = int(time_stamp[17:19])
    return datetime(year, month, day, hours, minutes, seconds)


def convert_datetime_to_timestamp(k):
    day = str(k.day) if len(str(k.day)) == 2 else "0" + str(k.day)
    month = str(k.month) if len(str(k.month)) == 2 else "0" + str(k.month)
    year = str(k.year)
    second = str(k.second) if len(str(k.second)) == 2 else "0" + str(k.second)
    minute = str(k.minute) if len(str(k.minute)) == 2 else "0" + str(k.minute)
    hour = str(k.hour) if len(str(k.hour)) == 2 else "0" + str(k.hour)
    return day + "-" + month + "-" + year + ":" + second + "-" + minute + "-" + hour


def delete_node(zk, node):
    zk.delete(node)


def main():
    logging.basicConfig()
    zk = KazooClient(hosts=zookeeper_hostname)
    zk.start()
    worker_type = "/" + os.environ["WORKER_TYPE"]
    zk.ensure_path(worker_type)
    node_name = worker_type + "/" + os.environ["NODE_NAME"]
    if not zk.exists(node_name):
        msg = "Creating node: " + node_name
        print(msg, file=sys.stdout)
        zk.create(node_name, msg.encode())
        f = open("node_name.txt", "w")
        f.write(node_name)
        f.close()

    data, stat = zk.get(node_name)
    print("Version: " + stat.version + "\nData: " + data.decode(), file=sys.stdout)

    try:
        subprocess.call(
            "mongodump --host mongomaster --port 27017 --db rideshare && mongorestore --host " + os.environ['DB_HOSTNAME'] + " --port 27017 --db rideshare",
            stdout=sys.stdout,
            stderr=sys.stdout,
            shell=True
        )
    except Exception as e:
        print(e, file=sys.stdout)

    if worker_type == "/master":
        rpc_server = RpcServer(queue_name='writeQ', func=writedb, is_master=True)
        print("[*] Listening on writeQ", file=sys.stdout)
        rpc_server.start()
    else:
        rpc_server = RpcServer(queue_name='readQ', func=readdb, is_master=False, func2=writedb)
        print("[*] Listening on readQ", file=sys.stdout)
        rpc_server.start()


if __name__ == "__main__":
    main()
