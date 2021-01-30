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
from queue import Empty, Full, Queue

import adafruit_rfm69
import board
import busio
import RPi.GPIO as GPIO
from digitalio import DigitalInOut
from micropython import const


class Radio:
    REG_FIFO = const(0x00)

    def __init__(self):
        self._rfm69 = None

        # RFM69 setup
        chip_select = DigitalInOut(board.CE1)
        reset = DigitalInOut(board.D25)
        spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

        # Setup interrupt directly via RPi.GPIO as Blinka doesn't support interrupts
        self._DIO0 = 22
        GPIO.setup(self._DIO0, GPIO.IN)

        try:
            # Preamble is 40 bits, detect at 20 => 3 bytes for now???
            self._rfm69 = adafruit_rfm69.RFM69(
                spi, chip_select, reset, 868.5, sync_word=b"\x2d\xd4", preamble_length=3
            )
            logging.info("RFM69 Initialised OK!")
        except RuntimeError as error:
            # Thrown on version mismatch
            logging.fatal(f"RFM69 Error: {error}")
            sys.exit(1)

        self._rfm69.modulation_type = 0b00  # FSK
        # self._rfm69.modulation_shaping = 0b01  # Gaussian BT 1.0
        self._rfm69.modulation_shaping = 0b10  # Gaussian BT 0.5
        # ListenEnd?

        self._rfm69.bitrate = 57600
        self._rfm69.frequency_deviation = 28750
        self._rfm69.packet_format = 1  # Packet mode
        self._rfm69.dc_free = 0b00  # No Manchester/Whitening
        self._rfm69.crc_on = 0

        # Start receiving on callback
        self._packet_queue = Queue(maxsize=64)
        GPIO.add_event_detect(self._DIO0, GPIO.RISING)
        GPIO.add_event_callback(self._DIO0, self.payload_ready_callback)
        self._rfm69.listen()

    def payload_ready_callback(self, channel):
        if channel != self._DIO0 or not self._rfm69.payload_ready():
            return
        rssi = self._rfm69.rssi
        # Idle mode to stop receiving data while still reading FIFO
        self._rfm69.idle()
        fifo_length = self._rfm69._read_u8(Radio.REG_FIFO)
        if fifo_length > 0:
            # TODO: Add length byte at start of received packet - needed for decyption
            packet = bytearray(fifo_length)
            self._rfm69._read_into(Radio.REG_FIFO, packet, fifo_length)
        self._rfm69.listen()
        if fifo_length > 0:
            try:
                self._packet_queue.put((packet, rssi), timeout=1)
            except Full:
                logging.warning("Dropping packet as queue full!")

    def wait_for_packet_queue(self, timeout=60.0):
        try:
            return self._packet_queue.get(timeout=timeout)
        except Empty:
            pass
        return None, None

    def reset(self):
        if self._rfm69:
            self._rfm69.reset()
            GPIO.remove_event_detect(self._DIO0)
            GPIO.cleanup(self._DIO0)
