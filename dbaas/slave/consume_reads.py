import pika
from dbaas.slave.config import db, rabbitmq_hostname
from datetime import datetime

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


def main():
    pass
    # TODO: Read db read requests from orchestrator via rabbitmq; query the database and return back the
    #  results to orchestrator via rabbitmq


if __name__ == '__main__':
    main()