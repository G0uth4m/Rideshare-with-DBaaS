import schedule
from config import client
import math
import random
import string
import time
import sys
import threading


def get_requests_count():
    f = open("requests_count.txt", "r")
    count = int(f.read())
    f.close()
    return count


def bring_up_new_worker_container(slave_name, db_name):
    print("[+] Starting(S) container: " + db_name, file=sys.stdout)
    client.containers.run(
        image="mongo:3.6.3",
        network="ubuntu_backend",
        name=db_name,
        hostname=db_name,
        detach=True,
        remove=False
    )

    time.sleep(2)

    print("[+] Starting(S) container: " + slave_name, file=sys.stdout)
    client.containers.run(
        image="slave:latest",
        command="python3 -u worker.py",
        environment={"DB_HOSTNAME": db_name, "WORKER_TYPE": "slave", "NODE_NAME": slave_name},
        entrypoint=["sh", "trap.sh"],
        hostname=slave_name,
        name=slave_name,
        network="ubuntu_backend",
        detach=True,
        remove=False
    )


def start_scaling():
    print("[+] Round started", file=sys.stdout)
    current_count = get_requests_count()
    print("[*] Resetting requests count to 0", file=sys.stdout)
    f = open("requests_count.txt", "w")
    f.write("0")
    f.close()
    containers = client.containers.list()
    current_slaves = 0
    for i in containers:
        if "slave" in i.name and "mongo" not in i.name:
            current_slaves += 1
    print("[*] Containers before scaling: ", file=sys.stdout)
    print([i.name for i in client.containers.list()])

    if current_count == 0:
        no_of_slaves_to_be_present = 1
    else:
        no_of_slaves_to_be_present = (int(math.ceil(current_count/20.0))*20)//20

    if current_slaves < no_of_slaves_to_be_present:
        n = no_of_slaves_to_be_present - current_slaves
        print("[*] Scaling out - starting " + str(n) + " containers", file=sys.stdout)
        for i in range(n):
            random_name = "".join(random.choices(string.ascii_lowercase + string.digits, k=7))
            slave_name = "slave" + random_name
            db_name = "mongo" + slave_name
            bring_up_new_worker_container(slave_name=slave_name, db_name=db_name)

    elif current_slaves > no_of_slaves_to_be_present:
        n = current_slaves - no_of_slaves_to_be_present
        print("[*] Scaling in - removing " + str(n) + " containers", file=sys.stdout)
        for i in range(n):
            temp = []
            for i in client.containers.list():
                if "master" not in i.name and "mongo" not in i.name and "slave" in i.name:
                    temp.append(i)
            cnt = random.choice(temp)
            print("[-] Removing db: " + "mongo" + cnt.name, file=sys.stdout)
            db = client.containers.get("mongo" + cnt.name)
            db.stop()
            db.remove()

            print("[-] Removing container: " + cnt.name, file=sys.stdout)
            cnt.stop()
            cnt.remove()

    else:
        print("[*] No scaling required", file=sys.stdout)

    print("[*] Containers after scaling: ", file=sys.stdout)
    print([i.name for i in client.containers.list()])

    print("[+] Round ended\n", file=sys.stdout)


def scaling_threaded():
    t1 = threading.Thread(target=start_scaling)
    t1.start()


print("[*] Scaling started", file=sys.stdout)
schedule.every(2).minutes.do(scaling_threaded)

while 1:
    schedule.run_pending()

