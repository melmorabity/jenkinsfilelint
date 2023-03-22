#!/bin/sh

openssl1.1 req -newkey rsa:2048 -nodes -keyout /etc/nginx/nginx.key -x509 -days 365 -out /etc/nginx/nginx.crt -subj "/CN=$(hostname)"
