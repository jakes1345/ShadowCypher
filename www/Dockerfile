FROM caddy:2.7-alpine

WORKDIR /srv

COPY www/index.html www/docs.html www/privacy.html www/terms.html www/roadmap.html www/status.html www/device.html www/self-host.html ./
COPY www/styles.css www/assistant.js www/sw.js ./
COPY www/manifest.json www/integrity.json ./
COPY www/apple-touch-icon.png www/icon-192.png www/icon-512.png ./
COPY www/r/ ./r/

COPY www/Caddyfile /etc/caddy/Caddyfile

EXPOSE 8080

CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile"]
