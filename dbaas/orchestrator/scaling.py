# docker commit --message="up scaling" slave slave_snapshot
# docker run --name=slave1 slave_snapshot
import schedule


def reset_requests_count():
    f = open("requests_count.txt", "w")
    f.write("0")
    f.close()


schedule.every(2).minutes.do(reset_requests_count())

