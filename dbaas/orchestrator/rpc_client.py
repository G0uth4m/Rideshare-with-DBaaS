import pika
import json
import uuid
from config import rabbitmq_hostname
import sys


class RpcClient:
    def __init__(self, routing_key):
        """
        Connect to rabbitmq and start consuming on the reply queue
        :param routing_key: Name of the queue where db queries are written
        """
        self.routing_key = routing_key
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitmq_hostname))
        self.channel = self.connection.channel()
        result = self.channel.queue_declare(queue='', exclusive=True, durable=True)
        self.callback_queue = result.method.queue

        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self.on_response,
            auto_ack=True
        )

    def on_response(self, ch, method, props, body):
        """
        Match the correlation id to get the correct response as part of the request-reply pattern
        :param props: Used to fetch the correlation id of the reply
        :param body: Message that was consumed
        :return: None
        """
        if self.corr_id == props.correlation_id:
            self.response = body

    def call(self, json_msg):
        """
        Write the message onto the specified queue and fetch the response as part of the request-reply pattern
        :param json_msg: Message that should be written on the queue (Request)
        :return: The message that was consumed from the reply queue (Reply)
        """
        self.response = None
        self.corr_id = str(uuid.uuid4())
        print("Sending data: " + str(json_msg), file=sys.stdout)
        # Write the json message onto the specified queue
        self.channel.basic_publish(
            exchange='',
            routing_key=self.routing_key,
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self.corr_id,
                delivery_mode=2,
            ),
            body=json.dumps(json_msg)
        )
        # Listen for the response recieved as part of the request-reply pattern
        while self.response is None:
            self.connection.process_data_events()

        return self.response
