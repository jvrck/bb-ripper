FROM python:3.8-slim-buster
ARG AWSCLI=FALSE 

WORKDIR /ripper

COPY requirements.txt /ripper
COPY bb-ripper/ /ripper/
COPY setup.sh /ripper

RUN chmod +x setup.sh
RUN /ripper/setup.sh
RUN rm /ripper/setup.sh
RUN apt-get update && apt-get upgrade && apt-get install -y git
RUN  pip install -r requirements.txt

VOLUME /data

ENV BB_RIPPER_EXPORT_DIRECTORY=/data/

CMD python3 .