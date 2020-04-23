# import schedule
# import random
# import string
# import sys
# import docker
#
# client = docker.DockerClient(base_url="tcp://192.168.56.105:4444")
#
#
# def bring_up_new_worker_container(db_name):
#     print("[+] Starting(S) container: " + db_name, file=sys.stdout)
#     client.containers.run(
#         image="python:3.7-slim-stretch",
#         name=db_name,
#         hostname=db_name,
#         detach=True,
#         remove=False
#     )
#
#
# def start_scaling():
#     random_name = "".join(random.choices(string.ascii_uppercase + string.digits, k=7))
#     bring_up_new_worker_container(random_name)
#     print('[*] Containers:')
#     for i in client.containers.list(all=True):
#         print(i.name)
#     print()
#
#
# print("[*] Scaling started", file=sys.stdout)
# schedule.every(30).seconds.do(start_scaling)
#
# while 1:
#     schedule.run_pending()
import time
print("Starting")
while 1:
    print("Hehe")
    time.sleep(2)

