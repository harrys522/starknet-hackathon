# Makefile for moosh_id project

# --- Configuration ---
VENV_DIR = .venv
FALCON_DIR = falcon
PYTHON = python3
VENV_PYTHON = $(VENV_DIR)/bin/python
VENV_PIP = $(VENV_DIR)/bin/pip
N = 512  # Default polynomial degree

# Directories
TARGET_DIR = target
KEY_DIR = $(TARGET_DIR)/keys
MSG_DIR = $(TARGET_DIR)/messages
KEY_FILE = $(KEY_DIR)/key_n$(N).json
MSG_FILE = $(MSG_DIR)/msg_n$(N).json

.PHONY: all setup clean test key generate-arguments

# Create and setup virtual environment
venv:
	$(PYTHON) -m venv $(VENV_DIR)
	$(VENV_PIP) install --upgrade pip

# Install Python dependencies
install-deps: venv
	$(VENV_PIP) install --upgrade setuptools wheel
	$(VENV_PIP) install -r requirements.txt

# Setup dependencies
build: install-deps
	$(VENV_PIP) install -e $(FALCON_DIR)
	cd moosh_id && scarb build

# Create necessary directories
$(KEY_DIR):
	mkdir -p $(KEY_DIR)

$(MSG_DIR):
	mkdir -p $(MSG_DIR)

# Generate key only (without running tests or setup)
generate-arguments: $(KEY_DIR)
	$(VENV_PYTHON) scripts/generate_inputs.py --n 512 --num_signatures 1
	$(VENV_PYTHON) scripts/generate_inputs.py --n 1024 --num_signatures 1
	@echo "Key generated and saved to moosh_id/tests/inputs/falcon_test_vectors_n512.cairo and moosh_id/tests/inputs/falcon_test_vectors_n1024.cairo"

# Generate and register a key (with setup)
key: setup
	cd moosh_id && scarb test test_keyregistry

# Run all tests (experimental)
test: key
	cd moosh_id && scarb test

test-only:
	cd moosh_id && scarb test

# Clean up generated files
clean:
	rm -rf $(TARGET_DIR)
	rm -rf $(VENV_DIR)
	cd moosh_id && scarb clean

python-shell:
	nix-shell -p python311

app:
	$(VENV_PYTHON) scripts/app.py

# app:
# 	nix-shell -p python311 --run 'make _app_internal'