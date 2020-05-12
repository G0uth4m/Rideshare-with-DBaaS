import json
from flask import Flask, request, Response, jsonify
from rpc_client import RpcClient
from config import client, zookeeper_hostname
import sys
import multiprocessing
from zoo_watch import ZooWatch
import subprocess
from kazoo.client import KazooClient
import logging

app = Flask(__name__)


@app.route('/api/v1/db/write', methods=["POST"])
def write_to_db():
    request_data = request.get_json(force=True)
    rpc_client = RpcClient(routing_key='writeQ')
    res = rpc_client.call(json_msg=request_data)
    res = json.loads(res)
    print("Received response: " + str(res), file=sys.stdout)
    if res == "Response(status=400)":
        return Response(status=400)
    return Response(status=200)


@app.route('/api/v1/db/read', methods=["POST"])
def read_from_db():
    increment_requests_count()
    global c
    c += 1
    if c == 1:
        subprocess.Popen("python3 scaling.py", shell=True)

    request_data = request.get_json(force=True)

    rpc_client = RpcClient(routing_key='readQ')
    res = rpc_client.call(json_msg=request_data)
    res = json.loads(res)

    print("Received response: " + str(res), file=sys.stdout)
    if res == "Response(status=400)":
        return Response(status=400)
    return jsonify(res)


@app.route('/api/v1/db/clear', methods=["POST"])
def clear_db():
    query = {"clear": 1, "collections": ["rides", "users"]}
    rpc_client = RpcClient(routing_key='writeQ')
    res = rpc_client.call(json_msg=query)
    res = json.loads(res)
    print("Received response: " + str(res), file=sys.stdout)
    if res == "Response(status=400)":
        return Response(status=500)
    f = open("seq.txt", "w")
    f.write("0")
    f.close()
    return Response(status=200)


@app.route('/api/v1/file/read', methods=["POST"])
def read_file():
    try:
        file = request.get_json(force=True)["file"]
    except:
        return Response(status=400)

    try:
        f = open(file, "r")
        c = {"latest_ride_id": int(f.read())}
        f.close()
        return jsonify(c)
    except:
        return Response(status=400)


@app.route('/api/v1/file/write', methods=["POST"])
def write_file():
    request_data = request.get_json(force=True)
    try:
        file = request_data["file"]
        data = int(request_data["data"])
    except:
        return Response(status=400)

    try:
        f = open(file, "w")
        f.write(str(data))
        f.close()
        return jsonify({})
    except:
        return Response(status=400)


@app.route('/api/v1/crash/master', methods=["POST"])
def kill_master():
    try:
        master_pid = client.containers.get("master").attrs["State"]["Pid"]
        master = client.containers.get("master")
        master.kill()
        master_db_name = zk.get("/worker/master")[0].decode()
        master_db = client.containers.get(master_db_name)
        master_db.kill()
        res = [master_pid]
        return jsonify(res)
    except:
        return Response(status=500)


@app.route('/api/v1/crash/slave', methods=["POST"])
def kill_slave():
    try:
        containers = client.containers.list()
        res = get_pid_of_all_slaves(containers)
        max_pid = max(res)

        selected_slave = ""

        for i in containers:
            if i.attrs["State"]["Pid"] == max_pid:
                selected_slave = i.name
                i.kill()
                break

        slave_db = client.containers.get("mongo" + selected_slave)
        slave_db.kill()
        res = [max_pid]
        return jsonify(res)

    except Exception as e:
        return Response(status=500)


@app.route('/api/v1/worker/list', methods=["GET"])
def list_workers():
    containers = client.containers.list()
    res = get_pid_of_all_workers(containers)
    if not res:
        return Response(status=204)
    res.sort()
    return jsonify(res)


def increment_requests_count():
    f = open("requests_count.txt", "r")
    count = int(f.read())
    f.close()
    f2 = open("requests_count.txt", "w")
    f2.write(str(count + 1))
    f2.close()


def get_requests_count():
    f = open("requests_count.txt", "r")
    count = int(f.read())
    f.close()
    return count


def get_pid_of_all_workers(containers):
    res = []
    for i in containers:
        if "mongo" not in i.name and ("slave" in i.name or "master" in i.name):
            print(i.name, file=sys.stdout)
            pid = i.attrs["State"]["Pid"]
            res.append(pid)
    return res


def get_pid_of_all_slaves(containers):
    res = []
    for i in containers:
        if "mongo" not in i.name and "slave" in i.name:
            print(i.name, file=sys.stdout)
            pid = i.attrs["State"]["Pid"]
            res.append(pid)
    return res


def start_zoo_watch():
    watch = ZooWatch(zookeeper_hostname)
    watch.start()


if __name__ == "__main__":
    p1 = multiprocessing.Process(target=start_zoo_watch)
    p1.start()
    c = 0
    logging.basicConfig()
    zk = KazooClient(hosts=zookeeper_hostname)
    zk.start()
    app.run(debug=True, host="0.0.0.0", port=80, use_reloader=False)
