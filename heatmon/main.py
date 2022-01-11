#!/usr/bin/env python3

# Copyright 2021 Tristan Keen

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import sys
from os import environ

from prometheus_client import start_http_server

from .system import System

# Warning, may want to switch METRICS_IP back to 127.0.0.1
METRICS_IP = environ.get("METRICS_IP", "0.0.0.0")
METRICS_PORT = int(environ.get("METRICS_PORT", "8000"))

log_format = "%(asctime)s.%(msecs)03d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s"
if "INVOCATION_ID" in environ:
    # Running under Systemd - no need for timestamp as journald provides
    log_format = "%(levelname)-8s [%(filename)s:%(lineno)d] %(message)s"

logging.basicConfig(
    format=log_format,
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.DEBUG,
)


def main():
    logging.info("Heatmon starting...")

    # Expose prometheus metrics
    start_http_server(addr=METRICS_IP, port=METRICS_PORT)

    try:
        system = System()
        system.gather_stats()
    except KeyboardInterrupt:
        print("Exiting due to KeyboardInterrupt...", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
