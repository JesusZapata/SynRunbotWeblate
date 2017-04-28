FROM python:2.7
MAINTAINER Jesus Zapata <jesus@vauxoo.com>

RUN mkdir -p /app/SynRunbotWeblate
COPY requirements.txt /app/SynRunbotWeblate/
COPY synchronize.py /app/SynRunbotWeblate/
RUN chmod a+rx /app/SynRunbotWeblate/synchronize.py
RUN pip install -r /app/SynRunbotWeblate/requirements.txt
RUN apt-get update && apt-get install -y cron python-requests
RUN echo "* * * * * root /usr/local/bin/python2 /app/SynRunbotWeblate/synchronize.py >> /var/log/cron.log 2>&1" >> /etc/crontab
RUN /etc/init.d/cron start
RUN touch /var/log/cron.log
CMD cron && tail -f /var/log/cron.log
