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

import adafruit_ssd1306
import board
import busio
from digitalio import DigitalInOut


class Display:
    def __init__(self):
        i2c = busio.I2C(board.SCL, board.SDA)

        # OLED display drivers needs font5x8.bin file present
        reset_pin = DigitalInOut(board.D4)
        self._display = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c, reset=reset_pin)

        self._display.fill(0)
        self._display.show()
        self._width = self._display.width
        self._height = self._display.height
        self._text_width = 7
        self._text_height = 11
        self._max_text_lines = 3
        self._text = []

    def clear(self, display=True):
        self._text = []
        if display:
            self._display.fill(0)
            self._display.show()

    def append_line(self, text):
        if len(self._text) >= self._max_text_lines:
            raise RuntimeError(f"Too many lines appended: {','.join(self._text)},{text}")
        self._text.append(text)

    def set_line(self, line_num, text):
        if line_num >= self._max_text_lines:
            raise RuntimeError(f"Setting line {line_num} but should be <{self._max_text_lines}")
        while len(self._text) <= line_num:
            self._text.append("")
        self._text[line_num] = text

    def show_lines(self):
        self._display.fill(0)
        for i, text in enumerate(self._text):
            self._display.text(text, 0, i * self._text_height, 1)
        self._display.show()
