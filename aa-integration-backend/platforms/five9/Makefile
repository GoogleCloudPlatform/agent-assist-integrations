# Import .env (Fill this out before running)
-include .env
export

# Clean variables
GRPC_SERVICE_NAME			:= $(shell echo $(GRPC_SERVICE_NAME) | tr -d "'\"")
HTTP_SERVICE_NAME			:= $(shell echo $(HTTP_SERVICE_NAME) | tr -d "'\"")
GRPC_PORT					:= $(shell echo $(GRPC_PORT) | tr -d "'\"")
HTTP_PORT					:= $(shell echo $(HTTP_PORT) | tr -d "'\"")

# Compose service keys (must match docker-compose.yaml)
GRPC_SERVICE_KEY			:= five9-mediastream-grpc
HTTP_SERVICE_KEY			:= five9-mediastream-http

PROJECT_ID					:= $(shell echo $(PROJECT_ID) | tr -d "'\"")
REGION						:= $(shell echo $(REGION) | tr -d "'\"")
CONVERSATION_PROFILE_NAME	:= $(shell echo $(CONVERSATION_PROFILE_NAME) | tr -d "'\"")
FEATURES					:= $(shell echo $(FEATURES) | tr -d "'\"")

FIVE9_TRUST_TOKEN			:= $(shell echo $(FIVE9_TRUST_TOKEN) | tr -d "'\"")
FIVE9_API_KEY				:= $(shell echo $(FIVE9_API_KEY) | tr -d "'\"")

# OS Detection
OS := $(shell uname -s)

# Detect container and compose tools
ifneq ($(shell command -v docker 2>/dev/null),)
    CONTAINER_CLI := docker
    COMPOSE_CLI := $(shell if command -v docker-compose >/dev/null 2>&1; then echo "docker-compose"; elif docker compose version >/dev/null 2>&1; then echo "docker compose"; else echo "docker compose"; fi)
else ifneq ($(shell command -v podman 2>/dev/null),)
    CONTAINER_CLI := podman
    COMPOSE_CLI := podman-compose
else
    CONTAINER_CLI := docker
    COMPOSE_CLI := docker compose
endif

# Colors
GREEN  := $(shell printf "\033[32m")
BLUE   := $(shell printf "\033[34m")
CYAN   := $(shell printf "\033[36m")
RESET  := $(shell printf "\033[0m")

.PHONY: help all build up down logs-local logs-cloudrun test test-grpc-unit \
		test-grpc-reachable test-http-reachable test-grpc-stream \
		generate-trust-token deploy deploy-grpc deploy-http podman-setup build-protos

help: ## Display this help screen
	@grep -Eh '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

all: down build up logs-local

# --- Local Development ---
build: build-images build-protos ## Build service containers
	$(COMPOSE_CLI) build

build-images:
	$(COMPOSE_CLI) build

build-protos: build-images ## Build gRPC protos using the container (no local venv needed)
	$(COMPOSE_CLI) run --rm $(GRPC_SERVICE_KEY) python3 -m grpc_tools.protoc \
		-I./proto --python_out=./proto --grpc_python_out=./proto voice.proto

up: ## Run services in background
	@CONNECTOR_SERVICE_NAME=$$(grep CONNECTOR_SERVICE_NAME ../../.env | cut -d '=' -f2 | tr -d "'"); \
	export UI_CONNECTOR_URL=$$(gcloud run services describe $$CONNECTOR_SERVICE_NAME --platform managed --region $(REGION) --format 'value(status.url)'); \
	$(COMPOSE_CLI) up -d

down: ## Stop and remove services
	$(COMPOSE_CLI) down

logs-local: ## Tail logs for both services with prefixes
	@echo "Tailing logs (Ctrl+C to stop)..."
	@trap 'kill 0' SIGINT; \
	$(CONTAINER_CLI) logs -f $(GRPC_SERVICE_NAME) 2>&1 | sed "s/^/$(GREEN)[GRPC]$(RESET) /" & \
	$(CONTAINER_CLI) logs -f $(HTTP_SERVICE_NAME) 2>&1 | sed "s/^/$(BLUE)[HTTP]$(RESET) /" & \
	wait

logs-cloudrun:
	@echo "Tailing Cloud Run logs..."
	@trap 'kill 0' SIGINT; \
	script -q /dev/null gcloud beta run services logs tail $(GRPC_SERVICE_NAME) --project $(PROJECT_ID) --region $(REGION) | while read -r l; do printf "\r$(GREEN)[GRPC]$(RESET) %s\n" "$$l"; done & \
	script -q /dev/null gcloud beta run services logs tail $(HTTP_SERVICE_NAME) --project $(PROJECT_ID) --region $(REGION) | while read -r l; do printf "\r$(BLUE)[HTTP]$(RESET) %s\n" "$$l"; done & \
	wait

# --- Testing ---
test: ## Run reachability and unit tests
	@LOCAL=true make test-grpc-reachable test-http-reachable test-grpc-unit

test-grpc-unit: ## Run unit tests inside the container (using volume mounts)
	$(COMPOSE_CLI) run --rm $(GRPC_SERVICE_KEY) /bin/bash -c "python -m unittest -v test.test_utils test.test_get_suggestions"

test-grpc-reachable: ## Test gRPC reachability (Use LOCAL=true for localhost)
	@if [ "$(LOCAL)" = "true" ]; then \
		HOST="localhost:$(GRPC_PORT)"; \
		FLAGS="-plaintext"; \
	else \
		URL=$$(gcloud run services describe $(GRPC_SERVICE_NAME) --platform managed --region $(REGION) --format 'value(status.url)' --project $(PROJECT_ID)); \
		HOST="$${URL##*//}:443"; \
		FLAGS=""; \
	fi; \
	echo "Target Host: $${HOST}"; \
	grpcurl $$FLAGS $${HOST} list; \
	grpcurl $$FLAGS -d '{"streaming_config": {"vcc_call_id": "$(shell date +%s)", "voice_config": {"sample_rate_hertz": 16000}, "call_leg": 1}}' $${HOST} five9.voicestream.Voice/StreamingVoice; \
	echo "\n(Hint: Use LOCAL=true to test against local containers)"; \

test-http-reachable: ## Test HTTP reachability (Use LOCAL=true for localhost)
	@if [ "$(LOCAL)" = "true" ]; then \
		BASE_URL="http://localhost:$(HTTP_PORT)"; \
	else \
		URL=$$(gcloud run services describe $(HTTP_SERVICE_NAME) --platform managed --region $(REGION) --format 'value(status.url)' --project $(PROJECT_ID)); \
		BASE_URL="$$URL"; \
	fi; \
	echo "Target URL: $${BASE_URL}"; \
	curl -s "$${BASE_URL}" | grep -q "Available" && echo "Root: OK" || echo "Root: FAILED"; \
	curl -s -X POST "$${BASE_URL}/mediastream-event-destination/subscriptions/test" -d '{"status":"test"}' -H "Content-Type: application/json"

test-grpc-stream: ## Stream audio to gRPC (Local or Cloud)
	@if [ "$(LOCAL)" = "true" ]; then \
		TARGET_HOST="five9-mediastream-grpc"; \
		TARGET_PORT="50051"; \
		EXTRA_FLAGS=""; \
	else \
		URL=$$(gcloud run services describe $(GRPC_SERVICE_NAME) --platform managed --region $(REGION) --format 'value(status.url)' --project $(PROJECT_ID) 2>/dev/null); \
		[ -z "$$URL" ] && echo "Error: Cloud Run URL not found." && exit 1; \
		TARGET_HOST="$${URL##*//}"; \
		TARGET_PORT="443"; \
		EXTRA_FLAGS="--secure"; \
	fi; \
	N=$(or $(LOAD_N),1); \
	DUR=$(or $(LOAD_DUR),115); \
	\
	echo "Streaming to $${TARGET_HOST}:$${TARGET_PORT} (Count: $$N, Duration: $$DUR)..."; \
	$(COMPOSE_CLI) run --rm $(GRPC_SERVICE_KEY) /bin/bash -c \
		"python test/client_streaming.py \
		--customer-wav test/audio/END_USER_google_store.wav \
		--agent-wav test/audio/HUMAN_AGENT_google_store.wav \
		--host $${TARGET_HOST} --port $${TARGET_PORT} $$EXTRA_FLAGS --duration $$DUR --count $$N"

# --- Cloud Run Deployment ---
generate-trust-token: ## Generate a random trust token
	@token=$$(openssl rand -hex 32); \
	echo "" >> .env; \
	echo "\nFIVE9_TRUST_TOKEN='$$token'" >> .env; \
	echo "\nFIVE9_TRUST_TOKEN='$$token'" >> ../../.env; \
	echo "Generated and appended FIVE9_TRUST_TOKEN to .env"

deploy: ## Deploy both services sequentially
	make deploy-grpc deploy-http

deploy-grpc: ## Deploy gRPC Service
	@if [ -z "$(CONVERSATION_PROFILE_NAME)" ]; then echo "Error: CONVERSATION_PROFILE_NAME missing"; exit 1; fi
	@echo "$(GREEN)Starting gRPC Deployment...$(RESET)"
	gcloud run deploy $(GRPC_SERVICE_NAME) \
		--source ./mediastream-grpc \
		--use-http2 \
		--set-env-vars CONVERSATION_PROFILE_NAME="$(CONVERSATION_PROFILE_NAME)" \
		--set-env-vars FIVE9_TRUST_TOKEN="$(FIVE9_TRUST_TOKEN)" \
		--set-env-vars FIVE9_API_KEY="$(FIVE9_API_KEY)" \
		--set-env-vars PROJECT_ID="$(PROJECT_ID)" \
		--allow-unauthenticated \
		--timeout 3600 \
		--region $(REGION) \
		--project $(PROJECT_ID)

deploy-http: ## Deploy HTTP Service
	@echo "$(BLUE)Starting HTTP Deployment...$(RESET)"
	@CONNECTOR_SERVICE_NAME=$$(grep CONNECTOR_SERVICE_NAME ../../.env | cut -d '=' -f2 | tr -d "'"); \
	UI_CONNECTOR_URL=$$(gcloud run services describe $$CONNECTOR_SERVICE_NAME --platform managed --region $(REGION) --format 'value(status.url)'); \
	echo "UI Connector URL: $$UI_CONNECTOR_URL"; \
	gcloud run deploy $(HTTP_SERVICE_NAME) \
		--source ./mediastream-http \
		--no-use-http2 \
		--set-env-vars PROJECT_ID="$(PROJECT_ID)" \
		--set-env-vars CONVERSATION_PROFILE_NAME="$(CONVERSATION_PROFILE_NAME)" \
		--set-env-vars "^:^FEATURES=$(FEATURES)" \
		--set-env-vars UI_CONNECTOR_URL="$$UI_CONNECTOR_URL" \
		--set-env-vars FIVE9_TRUST_TOKEN="$(FIVE9_TRUST_TOKEN)" \
		--set-env-vars FIVE9_API_KEY="$(FIVE9_API_KEY)" \
		--allow-unauthenticated \
		--region $(REGION) \
		--project $(PROJECT_ID)