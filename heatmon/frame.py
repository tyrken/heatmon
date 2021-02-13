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

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# from pprint import pprint


class Frame:
    OPEN_FRAME_TYPE = 0x4F
    SECURE_FRAME_TYPE = 0xCF

    KNOWN_TRV_IDS_TO_NAMES = {}
    DECRYPTOR = None

    @staticmethod
    def register_known_trvs(trvs):
        for trv in trvs:
            logging.info(f"Known TRVs: {trv.id.hex()} = {trv.name}")
            Frame.KNOWN_TRV_IDS_TO_NAMES[trv.id] = trv.name

    @staticmethod
    def register_secure_key(key):
        Frame.DECRYPTOR = AESGCM(key)

    def __init__(self, packet: bytearray):
        self.packet = packet
        self.frame_len = 0
        self.frame_type = -1
        self.id_len = -1
        self.body_len = -1
        self.trailer_len = -1
        self.id_len = -1
        self.id_len = -1
        self.id = bytes()
        self.trv_name = "Unknown"
        self.seq_num = 0
        self.restart_counter = -1
        self.message_counter = -1
        self.header = bytes()
        self.body = bytes()
        self.trailer = bytes()
        self.auth_tag = bytes()
        self.data = bytes()
        self.json_text = ""

        self.corrupt = packet is None or len(packet) < 8
        self.unknown_trv = True
        if self.corrupt:
            return

        fifo_length = int(packet[0])
        self.frame_len = len(packet) - 1
        self.frame_type = int(packet[1])
        self.corrupt = fifo_length != self.frame_len or (
            self.frame_type != Frame.OPEN_FRAME_TYPE and self.frame_type != Frame.SECURE_FRAME_TYPE
        )
        self.seq_num = int(packet[2]) >> 4
        self.id_len = int(packet[2]) & 0x0F
        if self.id_len <= 0 or self.id_len > 8 or self.frame_len < (self.id_len + 4):
            self.corrupt = True
            return
        self.id = bytes(packet[3 : 3 + self.id_len])
        self.body_len = int(packet[3 + self.id_len])
        self.trailer_len = self.frame_len - (3 + self.id_len + self.body_len)
        if self.trailer_len < 1:
            self.corrupt = True
            return
        body_start = 4 + self.id_len
        trailer_start = body_start + self.body_len
        self.header = bytes(packet[:body_start])
        self.body = bytes(packet[body_start:trailer_start])
        self.trailer = bytes(packet[trailer_start:])
        if self.frame_type == Frame.OPEN_FRAME_TYPE:
            self.corrupt = self.trailer_len != 1
            self.data = self.body
        else:
            self.corrupt = self.trailer_len != 23 or self.trailer[-1:] != b"\x80"
            if not self.corrupt:
                self.restart_counter = int.from_bytes(self.trailer[0:3], byteorder="big")
                self.message_counter = int.from_bytes(self.trailer[3:6], byteorder="big")
                self.auth_tag = bytes(self.trailer[6:22])

        if self.corrupt:
            return

        # Extend id by matching to known list
        matching = [
            (id, name)
            for id, name in self.KNOWN_TRV_IDS_TO_NAMES.items()
            if id[: self.id_len] == self.id
        ]
        if not matching:
            logging.warning(f"Unknown TRV with id starting: {self.id.hex()}")
        else:
            if self.frame_type != Frame.SECURE_FRAME_TYPE:
                raise NotImplementedError("No processing of open messages...")

            data_and_tag = self.body + self.auth_tag
            for maybe_id, maybe_name in matching:
                # First 6 bytes of Trailer is reset_counter + message_counter
                nonce = maybe_id[:6] + self.trailer[0:6]
                try:
                    self.data = Frame.DECRYPTOR.decrypt(nonce, data_and_tag, self.header)
                    self.id = maybe_id
                    self.trv_name = maybe_name
                    self.unknown_trv = False
                    break
                except InvalidTag:
                    # Decrypt didn't work - not this TRV ID match or key
                    pass
            else:
                logging.error(f"Failed to decrypt packet from {self.id.hex()}")

            if len(self.data) > 0:
                # Decode from https://github.com/opentrv/OpenTRV-standards/blob/master/standards/
                # protocol/IoTCommsFrameFormat/SecureBasicFrame-V0.1-201601.txt
                self.valve_open_percent = self.data[0] & 0x7F
                if self.valve_open_percent == 0x7F:
                    # No valve!
                    self.valve_open_percent = None
                self.call_for_heat = (self.data[0] & 0x80) != 0
                self.fault = (self.data[1] & 0x80) != 0
                self.battery_low = (self.data[1] & 0x40) != 0
                self.tamper = (self.data[1] & 0x20) != 0
                stats_present = (self.data[1] & 0x10) != 0
                # occupancy - 0:unreported, 1:none, 2:possible, 3:likely ... but always seems 0?
                self.occupancy = (self.data[1] & 0x0C) >> 2
                self.frost_risk = (self.data[1] & 0x02) != 0
                if stats_present:
                    end = self.data.find(b"\x00", 2)
                    self.json_text = (
                        self.data[2:end].decode(encoding="utf-8", errors="strict") + "}"
                    )

    def semi_ok(self):
        return self.frame_len > 4 and self.frame_type == Frame.SECURE_FRAME_TYPE

    def has_data(self):
        return not self.corrupt and len(self.data) > 0

    def one_line_summary(self):
        if self.corrupt:
            return "CORRUPT"
        if len(self.data) == 0:
            return "NO_DATA"
        status = " "
        if self.call_for_heat:
            status += "CFH "
        if self.fault:
            status += "FAULT "
        if self.battery_low:
            status += "BATLOW "
        if self.tamper:
            status += "TAMPER "
        if self.frost_risk:
            status += "FROST "
        return (
            f"{self.trv_name} #{self.message_counter} {self.valve_open_percent}%{status}"
            f"Occ{self.occupancy} {self.json_text}"
        )

    def debug(self):
        if not logging.getLogger().isEnabledFor(logging.DEBUG):
            return
        status = "GOOD"
        if self.corrupt:
            status = "CORRUPT"
        msg = f"{status} Packet: len={self.frame_len}, "
        msg += f"type={self.frame_type:x} from {self.trv_name}\n"
        msg += f"fl={self.frame_len} il={self.id_len} bl={self.body_len} tl={self.trailer_len}\n"
        msg += f"id={self.id.hex()} seq={self.seq_num}\n"
        if not self.corrupt:
            msg += "Body:      " + " ".join("{:02x}".format(x) for x in self.body) + "\n"
            msg += "Trailer:   " + " ".join("{:02x}".format(x) for x in self.trailer) + "\n"
            if self.frame_type == Frame.SECURE_FRAME_TYPE:
                msg += f"restart_counter={self.restart_counter} "
                msg += f"message_counter={self.message_counter}\n"

                msg += (
                    "Decrypted: "
                    + " ".join("{:02x}".format(x) for x in self.data)
                    + f" {self.data}\n"
                )
        logging.debug(msg)
