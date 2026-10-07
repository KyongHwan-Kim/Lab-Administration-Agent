#!/bin/sh
set -eu

trap 'exit 0' TERM INT

if [ -z "${DOMAIN:-}" ] || [ -z "${CERTBOT_EMAIL:-}" ]; then
  echo "DOMAIN 과 CERTBOT_EMAIL 이 없어 인증서 발급을 건너뜁니다. HTTP 로만 엽니다."
  while true; do
    sleep 3600 &
    wait $!
  done
fi

staging=""
if [ "${CERTBOT_STAGING:-0}" = "1" ]; then
  staging="--staging"
fi

mkdir -p /var/www/certbot
echo "인증서를 확인합니다: ${DOMAIN}"

while true; do
  if certbot certonly \
    --webroot -w /var/www/certbot \
    --email "$CERTBOT_EMAIL" \
    --agree-tos --no-eff-email \
    --non-interactive \
    --keep-until-expiring \
    $staging \
    -d "$DOMAIN"; then
    touch /var/www/certbot/reload
    break
  fi
  echo "인증서 발급에 실패했습니다. 15초 후 다시 시도합니다."
  sleep 15
done

while true; do
  certbot renew --webroot -w /var/www/certbot --deploy-hook "touch /var/www/certbot/reload" || true
  sleep 12h &
  wait $!
done
