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
import time

import RPi.GPIO as GPIO
from ruamel.yaml import YAML

from .display import Display
from .frame import Frame
from .radio import Radio
from .stats import get_stat_summaries, parse_stats, recalc_recent_trv_count


class TRV:
    def __init__(self, config):
        try:
            self.id = bytes.fromhex(config["id"])
            self.name = config["name"]
        except KeyError as e:
            raise ValueError(f"Missing id/name attribute for trv in '{config}'!") from e


class System:
    def __init__(self, config_path="./heatmon.yaml"):
        self.display = None
        self.radio = None

        with open(config_path, "r") as f:
            yaml = YAML(typ="safe")
            yaml_config = yaml.load(f)
        self.trvs_by_id = {}
        if "trvs" not in yaml_config:
            raise ValueError(
                "Config missing: trvs (the list of all the TRVs with their id and name)"
            )
        for config in yaml_config["trvs"]:
            trv = TRV(config)
            self.trvs_by_id[trv.id] = trv
        Frame.register_known_trvs(self.trvs_by_id.values())
        if "secure_key" not in yaml_config:
            raise ValueError(
                "Config missing: secure_key (the 16-byte hex key use to reprogram the TRVs)"
            )
        self.key = bytes.fromhex(yaml_config["secure_key"])
        if len(self.key) != 16:
            raise ValueError("Config bad length: secure_key should be 16 bytes long")
        Frame.register_secure_key(self.key)

    def gather_stats(self):
        try:
            self.display = Display()
            self.display.clear()
            self.display.set_line(0, "Heatmon starting...")
            self.display.show_lines()

            self.radio = Radio()

            self.display.set_line(0, "Heatmon started")
            self.display.show_lines()
            logging.info("Heatmon system starting to gather_stats")

            last_report_time = "never"
            while True:
                packet, rssi = self.radio.wait_for_packet_queue()
                frame = Frame(packet)
                if frame.semi_ok():
                    logging.info(f"Packet: {frame.one_line_summary()}")
                    # frame.debug()
                now = time.time()
                if not frame.corrupt and frame.json_text:
                    parse_stats(frame, rssi)
                    logging.info(f"RSSI {rssi} dBm")
                    last_report_time = time.strftime("%H:%M", time.localtime(now))
                num_recent = recalc_recent_trv_count(now)

                self.display.set_line(0, f"TRVs: {num_recent}, last: {last_report_time}")
                temp_summary, battery_valve_summary = get_stat_summaries()
                self.display.set_line(1, temp_summary)
                self.display.set_line(2, battery_valve_summary)
                self.display.show_lines()
        finally:
            if self.radio:
                self.radio.reset()
                print("Radio reset.", file=sys.stderr, flush=True)
            if self.display:
                self.display.clear()
            GPIO.cleanup()
