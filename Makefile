help: ## Prints this help message
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_-]+:.*?## / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

INSTALL_DIR?=/opt/heatmon
FONT_URL?=https://github.com/adafruit/Adafruit_CircuitPython_framebuf/raw/master/examples/font5x8.bin

.venv: ## Make raw virtualenv directory
	python3 -m venv --clear .venv

.venv/done: .venv dev-requirements.txt requirements.txt ## Populate virtualenv
	.venv/bin/pip install -r dev-requirements.txt -r requirements.txt
	curl -LO $(FONT_URL)
	touch .venv/done

.venv/bin/heatmon: .venv/done
	.venv/bin/python ./setup.py install
	.venv/bin/python ./setup.py clean

lint: .venv/done ## Run lint/check-formatting
	.venv/bin/flake8 --count --exclude .venv
	.venv/bin/black --check --diff --exclude .venv .

format: .venv/done ## Format code
	.venv/bin/black --exclude .venv .
	.venv/bin/isort

test: .venv/done ## pytest
	python -m pytest

run: .venv/bin/heatmon ## Run main.py
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
	sudo $(INSTALL_DIR)/bin/python ./setup.py clean
	sudo systemctl enable heatmon
	sudo systemctl restart heatmon
	sudo rm -rf build/ dist/ heatmon.egg-info/

uninstall: stop ## Uninstall systemd service
	sudo rm -f /etc/systemd/system/heatmon.service
	sudo systemctl daemon-reload
	sudo rm -rf $(INSTALL_DIR)

clean: ## Clean temporary files
	rm -rf .venv/
