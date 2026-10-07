#!/bin/sh
set -eu

WEBROOT="/var/www/certbot"
CONF="/etc/nginx/conf.d/default.conf"
DOMAIN="${DOMAIN:-}"
CERT_DIR="/etc/letsencrypt/live/${DOMAIN}"

mkdir -p "$WEBROOT"

write_config() {
  if [ -n "$DOMAIN" ] && [ -f "$CERT_DIR/fullchain.pem" ] && [ -f "$CERT_DIR/privkey.pem" ]; then
    cat > "$CONF" <<EOF
server {
    listen 80;
    server_name ${DOMAIN};
    client_max_body_size 320m;

    location /.well-known/acme-challenge/ {
        root ${WEBROOT};
    }

    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 443 ssl;
    http2 on;
    server_name ${DOMAIN};
    ssl_certificate ${CERT_DIR}/fullchain.pem;
    ssl_certificate_key ${CERT_DIR}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    client_max_body_size 320m;

    location / {
        proxy_pass http://lab-admin:8000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_read_timeout 180s;
        proxy_send_timeout 180s;
    }
}
EOF
    return
  fi

  cat > "$CONF" <<'EOF'
server {
    listen 80;
    server_name _;
    client_max_body_size 320m;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        proxy_pass http://lab-admin:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 180s;
        proxy_send_timeout 180s;
    }
}
EOF
}

stamp() {
  cert_stamp=0
  if [ -n "$DOMAIN" ] && [ -f "$CERT_DIR/fullchain.pem" ]; then
    cert_stamp=$(stat -c %Y "$CERT_DIR/fullchain.pem")
  fi
  flag_stamp=0
  if [ -f "$WEBROOT/reload" ]; then
    flag_stamp=$(stat -c %Y "$WEBROOT/reload")
  fi
  echo "$cert_stamp:$flag_stamp"
}

write_config

(
  last=$(stamp)
  while true; do
    sleep 60
    now=$(stamp)
    if [ "$now" != "$last" ]; then
      write_config
      nginx -s reload || true
      last=$now
    fi
  done
) &

exec nginx -g 'daemon off;'
