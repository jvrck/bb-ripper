FROM python:3.11-slim-bullseye
ARG AWSCLI=FALSE 

WORKDIR /ripper

COPY requirements.txt /ripper
COPY bb-ripper/ /ripper/
COPY setup.sh /ripper

RUN apt-get update && apt-get upgrade -y && apt-get install -y git
RUN chmod +x setup.sh && ./setup.sh && rm setup.sh
RUN pip install -r requirements.txt

VOLUME /data

ENV BB_RIPPER_EXPORT_DIRECTORY=/data/

CMD python3 .
