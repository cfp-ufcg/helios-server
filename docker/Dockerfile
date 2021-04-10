FROM ubuntu:18.04

RUN \
 	apt-get update && \
 	apt-get -y dist-upgrade && \
  	apt-get install -y -q \
    python-minimal \
    python-pip \
    python-virtualenv \
    python-ldap \
    python-dev \
    libpq-dev \
    libsasl2-dev \
    libldap2-dev \
    nginx \
    build-essential \
    gettext \
    supervisor \
    redis-server \
    vim less &&\
    rm -rf /var/lib/apt/lists/* && \
 	apt-get clean

RUN sed -i "s/bind .*/bind 127.0.0.1/g" /etc/redis/redis.conf
RUN sed -i "s/supervised no/supervised systemd/" /etc/redis/redis.conf
RUN sed -i "s/daemonize yes/daemonize no/" /etc/redis/redis.conf
RUN echo "\ndaemon off;" >> /etc/nginx/nginx.conf

COPY ./docker/supervisor/nginx-supervisor.conf /etc/supervisor/conf.d/nginx.conf
COPY ./docker/supervisor/celery-supervisor.conf /etc/supervisor/conf.d/celery-helios.conf
COPY ./docker/supervisor/redis-supervisor.conf /etc/supervisor/conf.d/redis-helios.conf

COPY ./docker/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

COPY ./docker/nginx/helios.conf /etc/nginx/sites-available/default

RUN groupadd -r -g 1000 helios && useradd -r -g helios -u 1000 helios

WORKDIR /var/www/helios-server
RUN chown helios:helios /var/www/helios-server

EXPOSE 80

ENTRYPOINT ["/docker-entrypoint.sh"]
