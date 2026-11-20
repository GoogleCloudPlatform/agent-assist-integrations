#!/usr/bin/env bash
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Builds production Docker images, boots each container with minimal test
# configuration, and verifies live HTTP / HTTP2 readiness checks.
#
# Usage:
#   ./scripts/docker_smoke_test.sh [all|backend|five9|genesyscloud|<service>...]
#
# Supported service names:
#   ui-connector, cloud-pubsub-interceptor, five9-grpc, five9-http,
#   genesyscloud-audiohook, genesyscloud-frontend

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_ID="aai-smoke-$$"
NETWORK_NAME="${RUN_ID}-net"
REDIS_CONTAINER="${RUN_ID}-redis"
TMP_DIR="$(mktemp -d)"
ADC_FILE="${TMP_DIR}/adc.json"
printf '{"type":"authorized_user","client_id":"smoke-test","client_secret":"smoke-test","refresh_token":"smoke-test","quota_project_id":"smoke-test-project"}\n' > "$ADC_FILE"
chmod 644 "$ADC_FILE"

CONTAINERS=()
IMAGES=()
NETWORK_CREATED=false

cleanup() {
  for c in "${CONTAINERS[@]}"; do
    docker rm -f "$c" >/dev/null 2>&1 || true
  done
  docker rm -f "$REDIS_CONTAINER" >/dev/null 2>&1 || true
  if [ "$NETWORK_CREATED" = true ]; then
    docker network rm "$NETWORK_NAME" >/dev/null 2>&1 || true
  fi
  for img in "${IMAGES[@]}"; do
    docker rmi -f "$img" >/dev/null 2>&1 || true
  done
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

ensure_redis() {
  if [ "$NETWORK_CREATED" = false ]; then
    docker network create "$NETWORK_NAME" >/dev/null
    NETWORK_CREATED=true
    docker run -d --name "$REDIS_CONTAINER" --network "$NETWORK_NAME" \
      redis:7-alpine >/dev/null
    echo "Started temporary Redis container ($REDIS_CONTAINER)"
  fi
}

free_port() {
  python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1]); s.close()'
}

wait_for_http() {
  local url="$1"
  local expected_code="${2:-200}"
  local container="$3"
  local method="${4:-GET}"
  local body="${5:-}"
  local attempts=40
  for ((i = 1; i <= attempts; i++)); do
    local code
    if [ -n "$body" ]; then
      code=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" \
        -H "Content-Type: application/json" -d "$body" "$url" 2>/dev/null || echo "000")
    else
      code=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" "$url" 2>/dev/null || echo "000")
    fi
    if [ "$code" = "$expected_code" ]; then
      return 0
    fi
    if ! docker ps -q -f "name=^${container}$" | grep -q .; then
      echo "Container $container exited prematurely! Logs:"
      docker logs "$container" || true
      return 1
    fi
    sleep 0.5
  done
  echo "Timed out waiting for $method $url (expected HTTP $expected_code). Logs:"
  docker logs "$container" || true
  return 1
}

wait_for_grpc_h2() {
  local port="$1"
  local container="$2"
  local attempts=40
  for ((i = 1; i <= attempts; i++)); do
    if python3 -c "
import socket
s = socket.create_connection(('127.0.0.1', ${port}), 1.0)
s.settimeout(1.0)
s.sendall(b'PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n\x00\x00\x00\x04\x00\x00\x00\x00\x00')
data = s.recv(9)
s.close()
assert len(data) == 9 and data[3] == 4
" 2>/dev/null; then
      return 0
    fi
    if ! docker ps -q -f "name=^${container}$" | grep -q .; then
      echo "Container $container exited prematurely! Logs:"
      docker logs "$container" || true
      return 1
    fi
    sleep 0.5
  done
  echo "Timed out waiting for gRPC HTTP/2 SETTINGS on 127.0.0.1:${port}. Logs:"
  docker logs "$container" || true
  return 1
}

smoke_ui_connector() {
  echo "=== Docker smoke: ui-connector ==="
  ensure_redis
  local img="${RUN_ID}-ui-connector"
  local name="${RUN_ID}-ui-connector"
  local port
  port="$(free_port)"
  local secret_file="${TMP_DIR}/jwt_secret_key"
  printf 'docker-smoke-jwt-secret-key-at-least-32-bytes!' > "$secret_file"

  docker build -t "$img" "$REPO_ROOT/aa-integration-backend/ui-connector"
  IMAGES+=("$img")

  docker run -d --name "$name" --network "$NETWORK_NAME" \
    -p "127.0.0.1:${port}:8080" \
    -v "${secret_file}:/secret/jwt_secret_key:ro" \
    -v "${ADC_FILE}:/tmp/adc.json:ro" \
    -e PORT=8080 \
    -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/adc.json \
    -e GCP_PROJECT_ID=smoke-test-project \
    -e REDISHOST="$REDIS_CONTAINER" \
    -e REDISPORT=6379 \
    -e AUTH_OPTION=Skip \
    -e LOGGING_FILE=/tmp/ui-connector.log \
    "$img" >/dev/null
  CONTAINERS+=("$name")

  wait_for_http "http://127.0.0.1:${port}/status" 200 "$name"
  echo "PASS: ui-connector (/status -> 200)"
}

smoke_cloud_pubsub_interceptor() {
  echo "=== Docker smoke: cloud-pubsub-interceptor ==="
  ensure_redis
  local img="${RUN_ID}-pubsub"
  local name="${RUN_ID}-pubsub"
  local port
  port="$(free_port)"

  docker build -t "$img" "$REPO_ROOT/aa-integration-backend/cloud-pubsub-interceptor"
  IMAGES+=("$img")

  docker run -d --name "$name" --network "$NETWORK_NAME" \
    -p "127.0.0.1:${port}:8080" \
    -e PORT=8080 \
    -e GCP_PROJECT_ID=smoke-test-project \
    -e REDISHOST="$REDIS_CONTAINER" \
    -e REDISPORT=6379 \
    -e LOGGING_FILE=/tmp/pubsub.log \
    "$img" >/dev/null
  CONTAINERS+=("$name")

  wait_for_http "http://127.0.0.1:${port}/conversation-lifecycle-event" 204 "$name" POST '{}'
  echo "PASS: cloud-pubsub-interceptor (POST /conversation-lifecycle-event -> 204)"
}

smoke_five9_grpc() {
  echo "=== Docker smoke: five9-grpc ==="
  local img="${RUN_ID}-five9-grpc"
  local name="${RUN_ID}-five9-grpc"
  local port
  port="$(free_port)"

  docker build -t "$img" "$REPO_ROOT/aa-integration-backend/platforms/five9/mediastream-grpc"
  IMAGES+=("$img")

  docker run -d --name "$name" \
    -p "127.0.0.1:${port}:8080" \
    -v "${ADC_FILE}:/tmp/adc.json:ro" \
    -e PORT=8080 \
    -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/adc.json \
    -e PROJECT_ID=smoke-test-project \
    "$img" >/dev/null
  CONTAINERS+=("$name")

  wait_for_grpc_h2 "$port" "$name"
  echo "PASS: five9-grpc (gRPC HTTP/2 SETTINGS on :8080)"
}

smoke_five9_http() {
  echo "=== Docker smoke: five9-http ==="
  local img="${RUN_ID}-five9-http"
  local name="${RUN_ID}-five9-http"
  local port
  port="$(free_port)"

  docker build -t "$img" "$REPO_ROOT/aa-integration-backend/platforms/five9/mediastream-http"
  IMAGES+=("$img")

  docker run -d --name "$name" \
    -p "127.0.0.1:${port}:8080" \
    -e PORT=8080 \
    -e FIVE9_TRUST_TOKEN=smoke-trust-token \
    -e FIVE9_API_KEY=smoke-api-key \
    "$img" >/dev/null
  CONTAINERS+=("$name")

  wait_for_http "http://127.0.0.1:${port}/" 200 "$name"
  echo "PASS: five9-http (/ -> 200)"
}

smoke_genesyscloud_audiohook() {
  echo "=== Docker smoke: genesyscloud-audiohook ==="
  ensure_redis
  local img="${RUN_ID}-audiohook"
  local name="${RUN_ID}-audiohook"
  local port
  port="$(free_port)"

  docker build -t "$img" "$REPO_ROOT/genesyscloud/genesyscloud-audiohook"
  IMAGES+=("$img")

  docker run -d --name "$name" --network "$NETWORK_NAME" \
    -p "127.0.0.1:${port}:8080" \
    -v "${ADC_FILE}:/tmp/adc.json:ro" \
    -e PORT=8080 \
    -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/adc.json \
    -e API_KEY=smoke-api-key \
    -e GCP_PROJECT_ID=smoke-test-project \
    -e CONVERSATION_PROFILE_NAME=projects/p/locations/global/conversationProfiles/cp1 \
    -e UI_CONNECTOR=http://127.0.0.1:9 \
    -e REDISHOST="$REDIS_CONTAINER" \
    -e REDISPORT=6379 \
    "$img" >/dev/null
  CONTAINERS+=("$name")

  wait_for_http "http://127.0.0.1:${port}/healthz" 200 "$name"
  echo "PASS: genesyscloud-audiohook (/healthz -> 200)"
}

smoke_genesyscloud_frontend() {
  echo "=== Docker smoke: genesyscloud-frontend ==="
  local img="${RUN_ID}-genesys-fe"
  local name="${RUN_ID}-genesys-fe"
  local port
  port="$(free_port)"

  docker build -t "$img" "$REPO_ROOT/genesyscloud/frontend"
  IMAGES+=("$img")

  docker run -d --name "$name" \
    -p "127.0.0.1:${port}:8080" \
    -e PORT=8080 \
    -e APPLICATION_SERVER_URL="http://127.0.0.1:${port}" \
    -e PROXY_SERVER=http://127.0.0.1:9 \
    "$img" >/dev/null
  CONTAINERS+=("$name")

  wait_for_http "http://127.0.0.1:${port}/ping" 200 "$name"
  echo "PASS: genesyscloud-frontend (/ping -> 200)"
}

run_target() {
  case "$1" in
    all)
      smoke_ui_connector
      smoke_cloud_pubsub_interceptor
      smoke_five9_grpc
      smoke_five9_http
      smoke_genesyscloud_audiohook
      smoke_genesyscloud_frontend
      ;;
    backend)
      smoke_ui_connector
      smoke_cloud_pubsub_interceptor
      ;;
    five9)
      smoke_five9_grpc
      smoke_five9_http
      ;;
    genesyscloud)
      smoke_genesyscloud_audiohook
      smoke_genesyscloud_frontend
      ;;
    ui-connector) smoke_ui_connector ;;
    cloud-pubsub-interceptor) smoke_cloud_pubsub_interceptor ;;
    five9-grpc) smoke_five9_grpc ;;
    five9-http) smoke_five9_http ;;
    genesyscloud-audiohook) smoke_genesyscloud_audiohook ;;
    genesyscloud-frontend) smoke_genesyscloud_frontend ;;
    *)
      echo "Unknown target: $1" >&2
      exit 2
      ;;
  esac
}

if [ $# -eq 0 ]; then
  run_target all
else
  for target in "$@"; do
    run_target "$target"
  done
fi
echo "All requested Docker smoke tests passed!"
