FROM nginxinc/nginx-unprivileged:1-alpine
USER root
COPY default.conf /etc/nginx/conf.d
COPY 99-ssl-cert-key.sh /docker-entrypoint.d
# hadolint ignore=DL3018
RUN apk add --update-cache --no-cache openssl1.1-compat
USER nginx
