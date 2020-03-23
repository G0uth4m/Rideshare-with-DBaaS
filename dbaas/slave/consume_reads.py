import pika
import json
from dbaas.master.config import db, rabbitmq_hostname
from datetime import datetime


def writedb(request_data):
    if 'delete' in request_data:
        try:
            delete = request_data['delete']
            column = request_data['column']
            collection = request_data['table']
        except KeyError:
            # print("Inappropriate request received")
            return "Response(status=400)"

        try:
            query = {column: delete}
            collection = db[collection]
            x = collection.delete_one(query)
            if x.raw_result['n'] == 1:
                return "Response(status=200)"
            return "Response(status=400)"
        except:
            # print("Mongo query failed")
            return "Response(status=400)"

    if 'update' in request_data:
        try:
            collection = request_data['table']
            where = request_data['where']
            array = request_data['update']
            data = request_data['data']
            operation = request_data['operation']
        except KeyError:
            # print("Inappropriate request received")
            return "Response(status=400)"

        try:
            collection = db[collection]
            x = collection.update_one(where, {"$" + operation: {array: data}})
            if x.raw_result['n'] == 1:
                return "Response(status=200)"
            return "Response(status=400)"
        except:
            return "Response(status=400)"

    try:
        insert = request_data['insert']
        columns = request_data['columns']
        collection = request_data['table']
    except KeyError:
        # print("Inappropriate request received")
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

    except:
        return "Response(status=400)"


def readdb(request_data):
    if 'count' in request_data:
        try:
            collection = db[request_data['table']]
            res = [collection.count_documents({})]
            return res
        except:
            return "Response(status=400)"

    try:
        table = request_data['table']
        columns = request_data['columns']
        where = request_data['where']
    except KeyError:
        # print("Inappropriate request received")
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
        except:
            return "Response(status=400)"

    try:
        collection = db[table]
        result = collection.find_one(where, filter)
        if "timestamp" in result:
            result["timestamp"] = convert_datetime_to_timestamp(result["timestamp"])
        return result
    except:
        return "Response(status=400)"


def consume():
    pass
    # TODO: If slave: Read the db read request readQ and send the response to the responseQ (6. RPC)


def produce():
    pass
    # TODO: If master: Read the db write request from writeQ, and send response to the writeResponseQ. Send
    #  received dbwrite request to syncQ (3. publish/subscribe)


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


def consume(is_master):
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitmq_hostname))
    if is_master:
        queue_name = 'writeQ'
        channel = connection.channel()
        channel.queue_declare(queue=queue_name, durable=True)
        channel.basic_consume(queue=queue_name, on_message_callback=callback_master)
        channel.start_consuming()
    else:
        queue_name = 'readQ'
        exchange_name = 'syncQ'

        channel1 = connection.channel()
        channel2 = connection.channel()

        channel1.queue_declare(queue=queue_name, durable=True)

        channel2.exchange_declare(exchange=exchange_name, exchange_type='fanout')
        result = channel2.queue_declare(queue='', exclusive=True)
        channel2_queue_name = result.method.queue
        channel2.queue_bind(exchange=exchange_name, queue=channel2_queue_name)

        channel1.basic_qos(prefetch_count=1)

        channel1.basic_consume(queue=queue_name, on_message_callback=callback_slave)
        channel2.basic_consume(queue=channel2_queue_name, on_message_callback=callback_slave_write)

        channel1.start_consuming()
        channel2.start_consuming()


def callback_master(ch, method, properties, body):
    res = writedb(json.loads(body))
    produce(queue_name='writeResponseQ', json_msg=json.dumps(res))
    publish('syncQ', body)
    ch.basic_ack(delivery_tag=method.delivery_tag)


def callback_slave(ch, method, properties, body):
    res = readdb(json.loads(body))
    produce(queue_name='responseQ', json_msg=json.dumps(res))
    ch.basic_ack(delivery_tag=method.delivery_tag)


def callback_slave_write(ch, method, properties, body):
    writedb(json.loads(body))


def publish(exchange_name, json_msg):
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitmq_hostname))
    channel = connection.channel()
    channel.exchange_declare(exchange=exchange_name, exchange_type='fanout')
    channel.basic_publish(exchange=exchange_name, routing_key='', body=json.dumps(json_msg))
    connection.close()


def main():
    consume(master)


if __name__ == "__main__":
    master = False
    main()
