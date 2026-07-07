FROM caddy:2.7-alpine

WORKDIR /srv

COPY index.html docs.html privacy.html terms.html roadmap.html status.html device.html ./
COPY styles.css assistant.js sw.js ./
COPY manifest.json integrity.json ./
COPY apple-touch-icon.png icon-192.png icon-512.png ./r/ ./r/

COPY Caddyfile /etc/caddy/Caddyfile

EXPOSE 8080

CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile"]
