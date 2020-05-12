import pika
import json
from config import rabbitmq_hostname
import sys
import threading


class RpcServer:
    def __init__(self, queue_name, func, is_master, func2=None):
        self.queue_name = queue_name
        self.func = func
        self.func2 = func2
        self.is_master = is_master
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitmq_hostname))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=self.queue_name, durable=True)
        self.channel.basic_qos(prefetch_count=1)

    def on_request(self, ch, method, props, body):
        res = json.loads(body)
        print("Received: " + str(res), file=sys.stdout)
        response = self.func(res)
        print("Sending: " + str(response), file=sys.stdout)
        ch.basic_publish(
            exchange='',
            routing_key=props.reply_to,
            properties=pika.BasicProperties(
                correlation_id=props.correlation_id,
            ),
            body=json.dumps(response)
        )
        if self.is_master and response != "Response(status=400)":
            self.publish(exchange_name='syncQ', json_msg=res)

        ch.basic_ack(delivery_tag=method.delivery_tag)

    def consume(self, queue_name, callback_fn):
        self.channel.basic_consume(queue=queue_name, on_message_callback=callback_fn)
        print("[*] Listening on " + queue_name, file=sys.stdout)
        self.channel.start_consuming()

    def subscribe(self, exchange_name, callback_fn):
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitmq_hostname))
        channel2 = connection.channel()
        channel2.exchange_declare(exchange=exchange_name, exchange_type='fanout')
        result = channel2.queue_declare(queue='', exclusive=True)
        queue_name = result.method.queue
        channel2.queue_bind(exchange=exchange_name, queue=queue_name)
        channel2.basic_consume(queue=queue_name, on_message_callback=callback_fn, auto_ack=True)
        print("[*] Listening on syncQ", file=sys.stdout)
        channel2.start_consuming()

    def start(self):
        if not self.is_master:
            t1 = threading.Thread(target=self.consume, args=(self.queue_name, self.on_request,))
            t2 = threading.Thread(target=self.subscribe, args=("syncQ", self.callback_slave))
            t1.start()
            t2.start()
            t1.join()
            t2.join()
        else:
            self.consume(self.queue_name, self.on_request)

    def callback_slave(self, ch, method, properties, body):
        print("Writing db for query: " + str(json.loads(body)), file=sys.stdout)
        self.func2(json.loads(body))

    def publish(self, exchange_name, json_msg):
        print("Publishing: " + str(json_msg), file=sys.stdout)
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitmq_hostname))
        channel = connection.channel()
        channel.exchange_declare(exchange=exchange_name, exchange_type='fanout')
        channel.basic_publish(exchange=exchange_name, routing_key='', body=json.dumps(json_msg))
        connection.close()