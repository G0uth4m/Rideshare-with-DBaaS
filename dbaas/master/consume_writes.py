import pika
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


def convert_timestamp_to_datetime(time_stamp):
    day = int(time_stamp[0:2])
    month = int(time_stamp[3:5])
    year = int(time_stamp[6:10])
    seconds = int(time_stamp[11:13])
    minutes = int(time_stamp[14:16])
    hours = int(time_stamp[17:19])
    return datetime(year, month, day, hours, minutes, seconds)


def main():
    pass
    # TODO: Read the db wrtie request from orchestrator via rabbitmq and write to database and return response to
    #  orchestrator via rabbitmq


if __name__ == "__main__":
    main()
