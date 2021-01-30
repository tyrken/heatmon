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

import json
import logging
import time

from prometheus_client import Counter, Gauge

RECENT_REPORTING_TRVS = Gauge(
    "recent_reporting_trv_count", "Number of TRVs that were reporting in the last 10 minutes",
)

# Unless explicitly mentioned, all below metrics are labelled/split per TRV by TRV name
std_lables = ["trv"]

SUCCESSFUL_MESSAGES = Counter(
    "messages_received", "Messages successfully decrypted from each TRV", labelnames=std_lables
)

# Judged absent by receiving new message counter value more than 1 above previous value
SKIPPED_MESSAGES = Counter(
    "messages_missed", "Messages judged absent from TRV", labelnames=std_lables
)

LAST_REPORT_TIME = Gauge(
    "last_message",
    "Unix timestamp of last successful message",
    unit="timestamp",
    labelnames=std_lables,
)

RADIO_RSSI = Gauge(
    "radio_rssi",
    "Received Signal Strength Indicator in decibel-milliwatts (dBm)",
    unit="dbm",
    labelnames=std_lables,
)

VALVE_OPEN = Gauge(
    "valve_open", "Fractional opening of the radiator valve", unit="ratio", labelnames=std_lables
)
CALL_FOR_HEAT = Gauge(
    "call_for_heat", "TRV is calling for heat from boiler", unit="", labelnames=std_lables
)
FAULT = Gauge("fault", "TRV detected a fault", unit="", labelnames=std_lables)
BATTERY_LOW = Gauge("battery_low", "TRV detected low Battery", unit="", labelnames=std_lables)
TAMPER = Gauge("tamper", "TRV detected tampering", unit="", labelnames=std_lables)
FROST_RISK = Gauge("frost_risk", "TRV detected a risk of frost", unit="", labelnames=std_lables)

# occupancy1 comes from the body/stats header (i.e. every frame), but seems always 0
# occupancy2 is in the JSON data body (i.e. once every several frames) and has data
OCCUPANCY1 = Gauge(
    "occupancy1",
    "TRV judged occupancy (0=unknown, 1-3=none-likely)",
    unit="",
    labelnames=std_lables,
)
OCCUPANCY2 = Gauge(
    "occupancy2",
    "TRV judged occupancy (0=unknown, 1-3=none-likely)",
    unit="",
    labelnames=std_lables,
)

# TRV counts up valve movement to make vC|%.
# Would use prometheus Counter metric except the auto metric "_created" would be incorrect
# ... so using a Gauge named ending "_total" like Counters
CUMULATIVE_VALVE = Gauge(
    "cumulative_valve_total",
    "Total valve operations (1 for each full opening)",
    labelnames=std_lables,
)

ROOM_TEMP = Gauge(
    "room_temperature", "Room temperature in Celsius", unit="celsius", labelnames=std_lables
)
BATTERY_VOLTAGE = Gauge("battery", "TRV battery voltage", unit="volts", labelnames=std_lables)
LIGHT_LEVEL = Gauge(
    "light_level", "Amount of light detected in a 0-1 scale", unit="ratio", labelnames=std_lables
)
RELATIVE_HUMIDITY = Gauge(
    "relative_humidity",
    "Room relative humidity in a 0-1 scale",
    unit="ratio",
    labelnames=std_lables,
)
VACANCY = Gauge("vacancy", "TRV judged hours since occupied", unit="hours", labelnames=std_lables)
TARGET_TEMP = Gauge(
    "target_temperature", "TRV target temperature", unit="celsius", labelnames=std_lables
)
# Not exactly sure what SETBACK_TEMP is
SETBACK_TEMP = Gauge(
    "setback_temperature",
    "Target temperature in setback mode",
    unit="celsius",
    labelnames=std_lables,
)

# Not sure of meaning of these metrics
SETBACK_LOCKOUT = Gauge("setback_lockout", "???", labelnames=std_lables)
ERROR_REPORT = Gauge("error_report", "???", labelnames=std_lables)
VALVE_STATUS = Gauge("valve_status", "???", unit="ratio", labelnames=std_lables)
RESET_COUNTER = Gauge("reset_counter", "???", labelnames=std_lables)


JSON_STAT_TO_METRIC = {
    "B|cV": BATTERY_VOLTAGE,
    "O": OCCUPANCY2,
    "L": LIGHT_LEVEL,
    "H|%": RELATIVE_HUMIDITY,
    "T|C16": ROOM_TEMP,
    "tT|C": TARGET_TEMP,
    "tS|C": SETBACK_TEMP,
    "vac|h": VACANCY,
    "vC|%": CUMULATIVE_VALVE,
    "gE": SETBACK_LOCKOUT,
    "gP": None,  # ???
    "err": ERROR_REPORT,
    "v|%": VALVE_STATUS,  # Duplicate with value at start of body
    "R": RESET_COUNTER,
}
# Divisors to convert TRV scales or Light level to Prometheus standard base units
UNIT_FACTOR = {"%": 100.0, "C16": 16.0, "cV": 100.0, "L": 255.0}

TRV_LAST_MESSAGE_COUNTER = {}
TRV_LAST_REPORT_TIME = {}
RECENT_MESSAGE_MAX_AGE = 600

DROP_WHEN_MISSING = [
    RADIO_RSSI,
    VALVE_OPEN,
    CALL_FOR_HEAT,
    FAULT,
    BATTERY_LOW,
    TAMPER,
    FROST_RISK,
    OCCUPANCY1,
    OCCUPANCY2,
    CUMULATIVE_VALVE,
    ROOM_TEMP,
    BATTERY_VOLTAGE,
    LIGHT_LEVEL,
    RELATIVE_HUMIDITY,
    VACANCY,
    TARGET_TEMP,
    SETBACK_TEMP,
    SETBACK_LOCKOUT,
    ERROR_REPORT,
    VALVE_STATUS,
    RESET_COUNTER,
]


def recalc_recent_trv_count(now):
    num_recent = 0
    missing_trvs = []
    for trv, x in TRV_LAST_REPORT_TIME.items():
        if now - x < RECENT_MESSAGE_MAX_AGE:
            num_recent += 1
        else:
            logging.info(f"Dropping metrics for missing trv: {trv}")
            for metric in DROP_WHEN_MISSING:
                try:
                    metric.remove(trv)
                except KeyError:
                    pass
            missing_trvs.append(trv)
    for trv in missing_trvs:
        TRV_LAST_REPORT_TIME.pop(trv)
    # num_recent = sum(1 for x in TRV_LAST_REPORT_TIME.values() if now - x < RECENT_MESSAGE_MAX_AGE)
    RECENT_REPORTING_TRVS.set(num_recent)


def parse_stats(frame, rssi):
    name = frame.trv_name

    RADIO_RSSI.labels(name).set(rssi)

    SUCCESSFUL_MESSAGES.labels(name).inc()
    prev_mc = TRV_LAST_MESSAGE_COUNTER.get(name, -1000)
    diff = (frame.message_counter - prev_mc) - 1
    if diff < 50:
        SKIPPED_MESSAGES.labels(name).inc(diff)
    TRV_LAST_MESSAGE_COUNTER[name] = frame.message_counter

    now = time.time()
    TRV_LAST_REPORT_TIME[name] = now
    LAST_REPORT_TIME.labels(name).set(now)
    recalc_recent_trv_count(now)

    if frame.valve_open_percent is not None:
        VALVE_OPEN.labels(name).set(frame.valve_open_percent / 100.0)

    CALL_FOR_HEAT.labels(name).set(frame.call_for_heat)
    FAULT.labels(name).set(frame.fault)
    BATTERY_LOW.labels(name).set(frame.battery_low)
    TAMPER.labels(name).set(frame.tamper)
    OCCUPANCY1.labels(name).set(frame.occupancy)
    FROST_RISK.labels(name).set(frame.frost_risk)

    for json_stat, value in json.loads(frame.json_text).items():
        metric = JSON_STAT_TO_METRIC.get(json_stat, "")
        if not metric:
            if metric == "":
                logging.warning(f"Unknown JSON stat: {json_stat} from trv {name}")
            continue
        if "|" in json_stat:
            unit = json_stat.split("|")[1]
            value /= UNIT_FACTOR.get(unit, 1.0)
        value /= UNIT_FACTOR.get(json_stat, 1.0)
        metric.labels(name).set(value)
