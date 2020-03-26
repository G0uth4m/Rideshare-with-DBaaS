import json
from flask import Flask, request, Response, jsonify
from dbaas.orchestrator.rpc_client import RpcClient

app = Flask(__name__)


@app.route('/api/v1/db/write', methods=["POST"])
def write_to_db():
    request_data = request.get_json(force=True)
    # Send request_data to master via rabbitmq using pika
    rpc_client = RpcClient(routing_key='writeQ')
    res = rpc_client.call(json_msg=request_data)
    res = json.loads(res)
    if res == "Response(status=400)":
        return Response(status=400)
    return Response(status=200)


@app.route('/api/v1/db/read', methods=["POST"])
def read_from_db():
    request_data = request.get_json(force=True)
    # Send request_data to slave via rabbitmq using pika
    rpc_client = RpcClient(routing_key='readQ')
    res = rpc_client.call(json_msg=request_data)
    res = json.loads(res)
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
    pass
    # TODO: The slave will kill the master worker


@app.route('/api/v1/crash/slave', methods=["DELETE"])
def kill_slave():
    pass
    # TODO: The slave whose container’s pid is the highest has to be killed


@app.route('/api/v1/worker/list', methods=["GET"])
def list_workers():
    pass
    # TODO: Return sorted list of pid’s of the container’s of all the workers


def bring_up_new_worker_container():
    pass
    # TODO: keep count of all incoming requests for dbread api and bring up new slave containers every 2 minutes
    #  depending on the number of requests


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=80)
