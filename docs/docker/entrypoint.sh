#!/usr/bin/env sh

python manage.py migrate --noinput
gunicorn -b 0.0.0.0:${FRAMARAMA_PORT:=8000} framarama.wsgi

