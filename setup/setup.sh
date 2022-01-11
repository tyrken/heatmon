#!/usr/bin/env bash

cd "$(dirname "$0")"

set -euxo pipefail

echo "Starting $0 at $(date)"

sudo apt-get update
sudo apt-get upgrade -y

sudo apt-get install -y git python3 python3-pip python3-venv python3-wheel

# Enable I2C and SPI interfaces on RPi to talk to RFM69 board
sudo apt-get install -y i2c-tools python3-smbus
sudo raspi-config nonint do_i2c 0
sudo raspi-config nonint do_spi 0

# Install & add hook for direnv, to make virtualenv work nicely
sudo apt-get install -y direnv
cat <<'EOF' >~/.bash_aliases
alias ll='ls -l'
eval "$(direnv hook bash)"
EOF

# Install prometheus (stores stats), the packaged version is a bit old but sufficient
sudo apt-get install -y --no-install-recommends prometheus
sudo cp files/prometheus.yml /etc/prometheus/prometheus.yml
echo 'ARGS="--storage.tsdb.retention.size=200MiB --storage.tsdb.retention.time=100d"' | sudo tee -a /etc/default/prometheus
sudo systemctl restart prometheus
# Prometheus is a bit old, but will be better in the next Raspbian assuming that's based on Bullseye
# Could install prometheus-alertmanager for proper alerting, but not trivial to configure

# Install grafana for viewing stats & easy alerting
sudo apt-get install -y adduser libfontconfig1
curl -L https://dl.grafana.com/oss/release/grafana-rpi_7.4.1_armhf.deb -o /tmp/grafana-rpi.deb
sudo dpkg -i /tmp/grafana-rpi.deb

sudo mkdir -p /etc/systemd/system/grafana-server.service.d
sudo cp files/grafana_override.conf /etc/systemd/system/grafana-server.service.d/override.conf
sudo cp -r files/grafana_etc/* /etc/grafana
sudo systemctl daemon-reload
sudo systemctl enable grafana-server
sudo systemctl start grafana-server

echo "Finished at $(date)."
