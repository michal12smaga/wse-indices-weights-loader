# Makefile for Python project template

.PHONY: help init-git devcontainer local-dev check-env test

help:
	@echo "Available targets:"
	@echo "  help           Show this help message"
	@echo "  init-git       Remove old .git, init new repo"
	@echo "  devcontainer   (Re)create VS Code dev container"
	@echo "  local-dev      Run development locally (Python REPL)"
	@echo "  check-env      Check Python version and uv presence"
	@echo "  test          Run template tests"

init-git:
	rm -rf .git
	git init
	git add .
	git commit -m "Initial commit from template"
	$(MAKE) ssh-refresh-known-hosts

# Requires VS Code and Dev Containers extension
# This will rebuild the container if using VS Code

devcontainer:
	@echo "To (re)create dev container, use VS Code:"
	@echo "  Command Palette > Dev Containers: Rebuild Container"

local-dev:
	python -m src

test:
	@echo "Running template tests..."
	@TEST_DIR="/tmp/setup-template-test-$$"; \
	trap 'rm -rf "$$TEST_DIR"' EXIT; \
	mkdir -p "$$TEST_DIR"; \
	cp -r * "$$TEST_DIR/"; \
	cd "$$TEST_DIR"; \
	failed=0; \
	for target in help check-env init-git local-dev; do \
		echo "\n--- Running: make $$target ---"; \
		if ! make $$target; then \
			echo "Target $$target failed"; \
			failed=1; \
		fi; \
	done; \
	exit $$failed

check-env:
	@echo "Checking Python version..."
	python3 --version
	@echo "Checking for uv..."
	@if command -v uv >/dev/null 2>&1; then \
		echo "uv is installed."; \
	else \
		echo "uv is NOT installed. Install with: pip install uv"; \
	fi

.PHONY: ssh-refresh-known-hosts
ssh-refresh-known-hosts:
	@echo "Refreshing github.com host keys"
	@mkdir -p ~/.ssh && chmod 700 ~/.ssh
	@touch ~/.ssh/known_hosts && chmod 644 ~/.ssh/known_hosts
	@ssh-keygen -R github.com >/dev/null 2>&1 || true
	@ssh-keyscan -H -t rsa,ecdsa,ed25519 github.com 2>/dev/null >> ~/.ssh/known_hosts
