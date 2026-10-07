# Lab-Administration-Agent

연구실 행정 대시보드입니다. 로그인 후 초과근무 메뉴에서 과제별 사용 내역을 보고, 항목을 추가하고, 배달 내역과 영수증을 한 열 PDF로 받을 수 있습니다.

웹과 FastAPI는 하나의 컨테이너에서 동작하고, PostgreSQL은 별도 컨테이너로 연결됩니다.

```bash
docker compose up --build
```

`.env.example` 을 `.env` 로 복사하고 세션 키, 관리자 비밀번호, 데이터베이스 비밀번호, 스프레드시트 ID, OpenAI API 키를 채운 뒤 실행합니다. 브라우저에서 `http://localhost:8000` 또는 nginx 를 거친 `http://localhost` 를 엽니다. 처음 만들어지는 관리자 계정은 `.env` 의 `ADMIN_USERNAME` 과 `ADMIN_PASSWORD` 입니다.

도메인으로 HTTPS 를 열려면 `.env` 에 `DOMAIN` 과 `CERTBOT_EMAIL` 을 넣고, 그 도메인의 DNS 가 이 서버를 가리키게 한 뒤 80·443 포트를 엽니다. nginx 가 인증서를 받고, certbot 이 12시간마다 갱신을 확인합니다. 인증서는 `certbot-certs` 볼륨에 남습니다.
