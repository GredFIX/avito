FROM postgres:latest

RUN sed -i '/ru_RU.UTF-8/s/^# //g' /etc/locale.gen \
 && locale-gen

ENV LANG ru_RU.UTF-8
ENV LANGUAGE ru_RU:ru
ENV LC_ALL ru_RU.UTF-8
