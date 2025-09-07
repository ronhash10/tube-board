# Project settings
PYTHON=python3
VENV=.venv
ACTIVATE=. $(VENV)/bin/activate;

# Default target: show help
.DEFAULT_GOAL := help

## Create virtual environment
$(VENV)/bin/activate: requirements.txt
	$(PYTHON) -m venv $(VENV)
	$(ACTIVATE) pip install --upgrade pip
	$(ACTIVATE) pip install -r requirements.txt

## Install dependencies into venv
install: $(VENV)/bin/activate ## Create venv and install deps

## Run the train board app
run: install ## Run the app (ensure deps installed)
	$(ACTIVATE) $(PYTHON) archway_tcr_board.py

## Update requirements.txt with currently installed deps
freeze: ## Freeze current deps into requirements.txt
	$(ACTIVATE) pip freeze > requirements.txt

## Remove venv (clean)
clean: ## Remove venv
	rm -rf $(VENV)

## Show available commands
help:
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  make %-10s %s\n", $$1, $$2}'
