FROM python:3.14.0a3-slim-bookworm
ARG AWSCLI=FALSE 

WORKDIR /ripper

COPY requirements.txt /ripper
COPY bb-ripper/ /ripper/
COPY setup.sh /ripper

RUN chmod +x setup.sh && ./setup.sh && rm setup.sh
RUN pip install -r requirements.txt

VOLUME /data

ENV BB_RIPPER_EXPORT_DIRECTORY=/data/

CMD python3 .
