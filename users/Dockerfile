FROM ubuntu:latest
RUN apt-get update
RUN apt-get -y install python3 python3-pip

WORKDIR /app_users
COPY . /app_users

ENV TEAM_NAME=CC_0132_1017_1025_1666

RUN pip3 install -r requirements.txt