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

import sys
import time

import serial


def set_trv_key(key, port):
    print(f"Setting TRV key via serial port '{port}'...")
    ser = serial.Serial(port=port, baudrate=4800, timeout=0.5)

    try:
        connected = False
        last_command_time = time.monotonic()
        command_period = 10.0
        finished = False
        while not finished:
            gap = time.monotonic() - last_command_time
            command = None
            if connected:
                command = "K B " + " ".join(f"{x:02X}" for x in key) + "\r\n"
            elif gap > command_period:
                command = "\r\n"
            if command:
                print("Sending: " + command)
                ser.write(command.encode("utf-8"))
                connected = False
                last_command_time = time.monotonic()

            connected = False
            while True:
                bytes_read = ser.read_until(size=150)
                if len(bytes_read) <= 0 or all((x == 0 for x in bytes_read)):
                    break
                # print("** " + " ".join(f"{x:02x}" for x in bytes_read))
                text = ""
                try:
                    text = bytes_read.decode(encoding="utf-8", errors="strict")
                    if text:
                        print("## " + text)
                except UnicodeDecodeError:
                    print("** " + " ".join(f"{x:02x}" for x in bytes_read))
                if "B set\r\n" in text:
                    print("\n### Have set encryption key successfully!")
                    finished = True
                if not connected and text == ">":
                    print("### Detected active connection...")
                    connected = True

    except KeyboardInterrupt:
        print("Exiting due to Ctrl+C", file=sys.stderr)
    finally:
        ser.close()
    print("Done.")


def main():
    port = "/dev/ttyUSB0"
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <16-byte-hex-key> [Serial-port={port}]", file=sys.stderr)
        sys.exit(1)

    key = bytes.fromhex(sys.argv[1])
    if len(key) != 16:
        raise ValueError("key bad length - reprogrammer first argument should be 16 bytes of hex")
    if len(sys.argv) > 2:
        port = sys.argv[2]

    set_trv_key(key, port)
    print("Finished.")


if __name__ == "__main__":
    main()
