// SSH 로 배포 서버에 소스를 올리고, 그 서버에서 docker compose 를 실행합니다.
// 기존 볼륨은 지우지 않습니다. COMPOSE_PROJECT_NAME 을 유지해야 데이터가 남습니다.
//
// Jenkins 자격 증명
// - lab-admin-ssh : SSH Username with private key
// - lab-admin-env : Secret file (.env)
//
// 플러그인: SSH Agent
// 에이전트: OpenSSH, rsync
// 서버: Docker Compose v2, SSH 사용자가 docker 를 실행할 수 있어야 합니다.
//
// 잡 매개변수 DEPLOY_HOST, DEPLOY_USER, DEPLOY_PATH 를 채웁니다.

pipeline {
    agent any

    options {
        disableConcurrentBuilds()
        timestamps()
    }

    parameters {
        string(name: 'DEPLOY_HOST', description: '배포 서버 호스트 또는 IP')
        string(name: 'DEPLOY_USER', defaultValue: 'deploy', description: 'SSH 사용자. lab-admin-ssh 자격 증명의 사용자와 같아야 합니다.')
        string(name: 'DEPLOY_PATH', defaultValue: '/home/ubuntu/lab-administration-agent', description: '서버의 배포 디렉터리')
    }

    environment {
        COMPOSE_PROJECT_NAME = 'lab-administration-agent'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('배포') {
            steps {
                sshagent(credentials: ['lab-admin-ssh']) {
                    withCredentials([file(credentialsId: 'lab-admin-env', variable: 'ENV_FILE')]) {
                        sh '''
                            set -eu
                            : "${DEPLOY_HOST:?DEPLOY_HOST 를 지정해 주세요.}"
                            : "${DEPLOY_USER:?DEPLOY_USER 를 지정해 주세요.}"
                            : "${DEPLOY_PATH:?DEPLOY_PATH 를 지정해 주세요.}"

                            case "$DEPLOY_HOST" in
                                *[!A-Za-z0-9.:-]*) echo "DEPLOY_HOST 형식이 올바르지 않습니다."; exit 1 ;;
                            esac
                            case "$DEPLOY_USER" in
                                *[!A-Za-z0-9._-]*) echo "DEPLOY_USER 형식이 올바르지 않습니다."; exit 1 ;;
                            esac
                            case "$DEPLOY_PATH" in
                                /*) ;;
                                *) echo "DEPLOY_PATH 는 절대 경로여야 합니다."; exit 1 ;;
                            esac
                            case "$DEPLOY_PATH" in
                                *[!A-Za-z0-9_./-]*) echo "DEPLOY_PATH 에 허용되지 않는 문자가 있습니다."; exit 1 ;;
                            esac

                            find nginx -name '*.sh' -exec sh -c 'tr -d "\\r" < "$1" > "$1.tmp" && mv "$1.tmp" "$1"' _ {} \\;

                            target="${DEPLOY_USER}@${DEPLOY_HOST}"
                            ssh_opts="-o StrictHostKeyChecking=accept-new"

                            ssh $ssh_opts "$target" "mkdir -p '$DEPLOY_PATH'"
                            rsync -az --delete \
                                -e "ssh $ssh_opts" \
                                --exclude '.git/' \
                                --exclude '.venv/' \
                                --exclude '.env' \
                                --exclude 'data/' \
                                --exclude 'seeds/' \
                                --exclude 'frontend/node_modules/' \
                                --exclude 'frontend/dist/' \
                                --exclude 'app/static/' \
                                ./ "${target}:${DEPLOY_PATH}/"
                            scp $ssh_opts "$ENV_FILE" "${target}:${DEPLOY_PATH}/.env"
                            ssh $ssh_opts "$target" "chmod 600 '$DEPLOY_PATH/.env' && cd '$DEPLOY_PATH' && COMPOSE_PROJECT_NAME='$COMPOSE_PROJECT_NAME' docker compose up -d --build --remove-orphans && COMPOSE_PROJECT_NAME='$COMPOSE_PROJECT_NAME' docker compose ps"
                        '''
                    }
                }
            }
        }
    }
}
