import json
from flask import Flask, request, Response, jsonify
from dbaas.orchestrator.rpc_client import RpcClient
from dbaas.orchestrator.config import client, apiClient
import sys


app = Flask(__name__)


@app.route('/api/v1/db/write', methods=["POST"])
def write_to_db():
    request_data = request.get_json(force=True)
    # Send request_data to master via rabbitmq using pika
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

    curr_count = get_requests_count()
    if curr_count == 1:
        pass
        # TODO: start scalability script
    elif curr_count % 10 == 1 and (curr_count // 10) % 2 == 0:
        slave_name = "slave" + str((curr_count + 19)/20)
        db_name = "mongoslave" + str((curr_count + 19)/20)
        bring_up_new_worker_container(slave_name, db_name)

    request_data = request.get_json(force=True)

    rpc_client = RpcClient(routing_key='readQ')
    res = rpc_client.call(json_msg=request_data)
    res = json.loads(res)

    print("Received response: " + str(res), file=sys.stdout)
    if res == "Response(status=400)":
        return Response(status=400)
    return jsonify(res)


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
    for i in client.containers.list():
        if i.name == "master":
            i.stop()
            return Response(status=200)
    return Response(status=500)


@app.route('/api/v1/crash/slave', methods=["DELETE"])
def kill_slave():
    res = get_pid_of_all_workers()
    max_pid = max(res)

    for i in client.containers.list():
        if apiClient.inspect_container(i.name)["State"]["Pid"] == max_pid:
            i.stop()
            return Response(status=200)
    return Response(status=500)


@app.route('/api/v1/worker/list', methods=["GET"])
def list_workers():
    res = get_pid_of_all_workers()
    res.sort()
    return jsonify(res)


def bring_up_new_worker_container(slave_name, db_name):
    client.containers.run(
        image="master:latest",
        command="python3 -u worker.py",
        environment={"DB_HOSTNAME": db_name, "WORKER_TYPE": "slave", "NODE_NAME": slave_name},
        hostname=slave_name,
        name=slave_name,
        network="backend",
        volumes={"/home/ubuntu/worker/": {"bind": "/worker", "mode": "rw"}},
    )

    client.containers.run(
        image="mongo:latest",
        network="backend",
        name=db_name,
        hostname=db_name
    )


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


def get_pid_of_all_workers():
    containers = client.containers.list()
    res = []
    for i in containers:
        if "slave" in i.name  or "master" in i.name:
            pid = apiClient.inspect_container(i.name)["State"]["Pid"]
            res.append(pid)
    return res


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=80)
