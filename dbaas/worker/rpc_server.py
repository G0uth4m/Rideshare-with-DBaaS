import pika
import json
from dbaas.worker.config import rabbitmq_hostname


class RpcServer:
    def __init__(self, queue_name, func, is_master, func2=None):
        self.queue_name = queue_name
        self.func = func
        self.func2 = func2
        self.is_master = is_master
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitmq_hostname))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=self.queue_name)
        self.channel.basic_qos(prefetch_count=1)

    def on_request(self, ch, method, props, body):
        res = json.loads(body)
        response = self.func(res)

        ch.basic_publish(
            exchange='',
            routing_key=props.reply_to,
            properties=pika.BasicProperties(
                correlation_id=props.correlation_id,
            ),
            body=json.dumps(response)
        )
        if self.is_master:
            self.publish(exchange_name='syncQ', json_msg=res)

        ch.basic_ack(delivery_tag=method.delivery_tag)

    def start(self):
        self.channel.basic_consume(queue=self.queue_name, on_message_callback=self.on_request)
        self.channel.start_consuming()
        if not self.is_master:
            channel2 = self.connection.channel()
            channel2.exchange_declare(queue='', exchange_type='fanout')
            result = channel2.queue_declare(queue='', exclusive=True)
            queue_name = result.method.queue
            channel2.queue_bind(exchange='syncQ', queue=queue_name)
            channel2.basic_consume(queue=queue_name, on_message_callback=self.calback_slave, auto_ack=True)
            channel2.start_consuming()

    def calback_slave(self, ch, method, properties, body):
        self.func2(json.loads(body))

    def publish(self, exchange_name, json_msg):
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitmq_hostname))
        channel = connection.channel()
        channel.exchange_declare(exchange=exchange_name, exchange_type='fanout')
        channel.basic_publish(exchange=exchange_name, routing_key='', body=json.dumps(json_msg))
        connection.close()