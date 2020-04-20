import json
from flask import Flask, request, Response, jsonify
from dbaas.orchestrator.rpc_client import RpcClient
from dbaas.orchestrator.config import client, apiClient, zookeeper_hostname
import sys
import multiprocessing
from dbaas.orchestrator.zoo_watch import ZooWatch
import subprocess

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
    print("[*] No. of requests until now: " + str(get_requests_count()), file=sys.stdout)
    global c
    c += 1

    if c == 1:
        print("[*] Running scalability script ...", file=sys.stdout)
        subprocess.Popen("python3 scaling.py", stdout=sys.stdout, shell=True)

    request_data = request.get_json(force=True)

    rpc_client = RpcClient(routing_key='readQ')
    res = rpc_client.call(json_msg=request_data)
    res = json.loads(res)

    print("Received response: " + str(res), file=sys.stdout)
    if res == "Response(status=400)":
        return Response(status=400)
    return jsonify(res)


@app.route('/api/v1/db/clear', methods=["DELETE"])
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


@app.route('/api/v1/crash/master', methods=["DELETE"])
def kill_master():
    try:
        master = client.containers.get("master")
        master.stop()
        master_db = client.containers.get("mongomaster")
        master_db.stop()
        return Response(status=200)
    except:
        return Response(status=500)


@app.route('/api/v1/crash/slave', methods=["DELETE"])
def kill_slave():
    try:
        containers = client.containers.list()
        res = get_pid_of_all_slaves(containers)
        max_pid = max(res)

        selected_slave = ""

        for i in containers:
            if apiClient.inspect_container(i.name)["State"]["Pid"] == max_pid:
                selected_slave = i.name
                i.stop()
                break

        slave_db = client.containers.get("mongo" + selected_slave)
        slave_db.stop()
        return Response(status=200)

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
            pid = apiClient.inspect_container(i.name)["State"]["Pid"]
            res.append(pid)
    return res


def get_pid_of_all_slaves(containers):
    res = []
    for i in containers:
        if "mongo" not in i.name and "slave" in i.name:
            print(i.name, file=sys.stdout)
            pid = apiClient.inspect_container(i.name)["State"]["Pid"]
            res.append(pid)
    return res


def start_zoo_watch():
    watch = ZooWatch(zookeeper_hostname)
    watch.start()


if __name__ == "__main__":
    p1 = multiprocessing.Process(target=start_zoo_watch)
    p1.start()
    c = 0
    app.run(debug=True, host="0.0.0.0", port=80)
