import pika
import json
from flask import Flask, request, Response, jsonify
from dbaas.orchestrator.config import rabbitmq_hostname
from datetime import datetime

app = Flask(__name__)


@app.route('/api/v1/db/write', methods=["POST"])
def write_to_db():
    request_data = request.get_json(force=True)
    # Send request_data to master via rabbitmq using pika
    produce(queue_name='writeQ', json_msg=request_data)
    res = consume(queue_name='writeResponseQ')
    if res == "Response(status=400)":
        return Response(status=400)
    return Response(status=200)


@app.route('/api/v1/db/read', methods=["POST"])
def read_from_db():
    request_data = request.get_json(force=True)
    # Send request_data to slave via rabbitmq using pika
    produce(queue_name='readQ', json_msg=request_data)
    res = consume(queue_name='responseQ')
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


def produce(queue_name, json_msg):
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitmq_hostname))
    channel = connection.channel()
    channel.queue_declare(queue=queue_name, durable=True)
    channel.basic_publish(exchange='',
                          routing_key=queue_name,
                          body=json.dumps(json_msg),
                          properties=pika.BasicProperties(
                              delivery_mode=2,
                          ))
    connection.close()


def consume(queue_name):
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitmq_hostname))
    channel = connection.channel()
    channel.queue_declare(queue=queue_name, durable=True)

    for method_frame, properties, body in channel.consume(queue_name):
        res = json.loads(body)
        channel.basic_ack(method_frame.delivery_tag)
        if method_frame.delivery_tag == 1:
            break
    channel.cancel()
    channel.close()
    connection.close()
    return res


def convert_datetime_to_timestamp(k):
    day = str(k.day) if len(str(k.day)) == 2 else "0" + str(k.day)
    month = str(k.month) if len(str(k.month)) == 2 else "0" + str(k.month)
    year = str(k.year)
    second = str(k.second) if len(str(k.second)) == 2 else "0" + str(k.second)
    minute = str(k.minute) if len(str(k.minute)) == 2 else "0" + str(k.minute)
    hour = str(k.hour) if len(str(k.hour)) == 2 else "0" + str(k.hour)
    return day + "-" + month + "-" + year + ":" + second + "-" + minute + "-" + hour


def convert_timestamp_to_datetime(time_stamp):
    day = int(time_stamp[0:2])
    month = int(time_stamp[3:5])
    year = int(time_stamp[6:10])
    seconds = int(time_stamp[11:13])
    minutes = int(time_stamp[14:16])
    hours = int(time_stamp[17:19])
    return datetime(year, month, day, hours, minutes, seconds)


def bring_up_new_worker_container():
    pass
    # TODO: keep count of all incoming requests for dbread api and bring up new slave containers every 2 minutes
    #  depending on the number of requests


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=80)
