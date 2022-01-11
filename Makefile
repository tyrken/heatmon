help: ## Prints this help message
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_-]+:.*?## / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

INSTALL_DIR?=/opt/heatmon
FONT_URL?=https://github.com/adafruit/Adafruit_CircuitPython_framebuf/raw/main/examples/font5x8.bin
export PATH:=$(CURDIR)/.venv/bin:$(PATH)

.venv:
	python3 -m venv --clear .venv

.venv/done: .venv dev-requirements.txt requirements.txt
	pip install -r dev-requirements.txt -r requirements.txt
	curl -LO $(FONT_URL)
	touch .venv/done

heatmon.egg-info: .venv/done
	python ./setup.py develop

venv: heatmon.egg-info ## Make and fill local virtualenv

lint: .venv/done ## Run lint/check-formatting
	flake8 --count --exclude .venv
	black --check --diff --exclude .venv .

format: .venv/done ## Format code
	black --exclude .venv .
	isort

test: .venv/done ## pytest
	python -m pytest

run: heatmon.egg-info ## Run main.py
	heatmon

install:  ## Install systemd service
	sudo python3 -m venv --clear $(INSTALL_DIR)
	sudo $(INSTALL_DIR)/bin/pip install -r requirements.txt
	sudo $(INSTALL_DIR)/bin/python ./setup.py install
	sudo $(INSTALL_DIR)/bin/python ./setup.py clean
	sudo cp ./heatmon.yaml $(INSTALL_DIR)
	sudo cp ./font5x8.bin $(INSTALL_DIR)
	sudo cp ./heatmon.service /etc/systemd/system
	sudo systemctl daemon-reload
	sudo systemctl enable heatmon
	sudo systemctl start heatmon

start: ## Start systemd service
	sudo systemctl enable heatmon
	sudo systemctl start heatmon

stop: ## Stop systemd service
	sudo systemctl disable heatmon
	sudo systemctl stop heatmon

logs: ## Show and follow service logs
	journalctl -u heatmon -f

reinstall:  ## Update systemd service source file
	sudo rm -rf build/ dist/ heatmon.egg-info/
	sudo $(INSTALL_DIR)/bin/python ./setup.py install
	sudo systemctl enable heatmon
	sudo systemctl restart heatmon
	sudo rm -rf build/ dist/ heatmon.egg-info/

uninstall: stop ## Uninstall systemd service
	sudo rm -f /etc/systemd/system/heatmon.service
	sudo systemctl daemon-reload
	sudo rm -rf $(INSTALL_DIR)

clean: ## Clean temporary files
	rm -rf .venv/
