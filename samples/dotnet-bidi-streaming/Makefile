# Import .env if present
-include .env
export

# Clean variables
PROJECT_ID                := $(shell echo $(PROJECT_ID) | tr -d "'\"")
LOCATION_ID               := $(shell echo $(LOCATION_ID:-global) | tr -d "'\"")
CONVERSATION_PROFILE_NAME := $(shell echo $(CONVERSATION_PROFILE_NAME) | tr -d "'\"")
PORT                      := $(shell echo $(PORT:-8080) | tr -d "'\"")
SERVICE_NAME              := $(shell echo $(SERVICE_NAME:-dialogflow-bidi-stream) | tr -d "'\"")

# Container & Compose CLI Detection
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

TTY_FLAG := $(shell [ -t 0 ] && echo "-it" || echo "-i")

# Colors
CYAN  := $(shell printf "\033[36m")
RESET := $(shell printf "\033[0m")

.PHONY: help all build up down logs test test-unit clean

help: ## Display this help screen
	@grep -Eh '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

all: down build up logs ## Clean, rebuild, start and tail logs

# --- Local Development ---
build: ## Build the .NET container image (includes running unit tests during Docker build)
	$(COMPOSE_CLI) build

up: ## Start the service in the background
	$(COMPOSE_CLI) up -d

down: ## Stop and remove running containers
	$(COMPOSE_CLI) down

logs: ## Follow service container logs
	$(COMPOSE_CLI) logs -f dialogflow-bidi-stream

.PHONY: help all build up down logs test test-unit test-integration test-load clean

test: ## Run all unit, integration, and load tests
	$(CONTAINER_CLI) run --rm -v dotnet-nuget-cache:/root/.nuget -v $(PWD):/workspace -w /workspace mcr.microsoft.com/dotnet/sdk:8.0 dotnet test tests/DialogflowBidiStream.Tests/DialogflowBidiStream.Tests.csproj

test-unit: ## Run unit tests only
	$(CONTAINER_CLI) run --rm -v dotnet-nuget-cache:/root/.nuget -v $(PWD):/workspace -w /workspace mcr.microsoft.com/dotnet/sdk:8.0 dotnet test tests/DialogflowBidiStream.Tests/DialogflowBidiStream.Tests.csproj --filter "Category=Unit"

test-integration: ## Run integration tests only
	$(CONTAINER_CLI) run --rm -v dotnet-nuget-cache:/root/.nuget -v $(PWD):/workspace -w /workspace mcr.microsoft.com/dotnet/sdk:8.0 dotnet test tests/DialogflowBidiStream.Tests/DialogflowBidiStream.Tests.csproj --filter "Category=Integration"

test-load: ## Run load and stress tests only
	$(CONTAINER_CLI) run --rm -v dotnet-nuget-cache:/root/.nuget -v $(PWD):/workspace -w /workspace mcr.microsoft.com/dotnet/sdk:8.0 dotnet test tests/DialogflowBidiStream.Tests/DialogflowBidiStream.Tests.csproj --filter "Category=Load"

stream-cli: ## Stream audio via CLI runner (requires ADC: gcloud auth application-default login)
	$(CONTAINER_CLI) run --rm $(TTY_FLAG) -v $(HOME)/.config/gcloud:/root/.config/gcloud:ro -v dotnet-nuget-cache:/root/.nuget -v $(PWD):/workspace -w /workspace -e PROJECT_ID="$(PROJECT_ID)" -e LOCATION_ID="$(LOCATION_ID)" -e CONVERSATION_PROFILE_NAME="$(CONVERSATION_PROFILE_NAME)" mcr.microsoft.com/dotnet/sdk:8.0 dotnet run --project samples/CliStreamer -- --project "$(PROJECT_ID)" --location "$(LOCATION_ID)" --profile "$(CONVERSATION_PROFILE_NAME)"

clean: down ## Clean up containers and build artifacts
	$(CONTAINER_CLI) image rm -f dotnet-dialogflow-test 2>/dev/null || true
