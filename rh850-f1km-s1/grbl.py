#!/usr/bin/env python3

import serial

class Grbl:
    def __init__(self, port='/dev/ttyUSB0', baudrate=115200, timeout=1.0, return_home=True):
        self.return_home = return_home
        self.ser = serial.Serial(port, baudrate, timeout=timeout)


        self.set_absolute_positioning_mode()
        self.set_home()
        self.set_units_mm()
        self.set_feed_rate()

    def __del__(self):
        if self.return_home:
            self.set_pos(0, 0, 0)
        self.ser.close()

    def set_absolute_positioning_mode(self):
        self.send_cmd("G90")

    def set_home(self, x=0, y=0, z=0):
        self.send_cmd(f"G92 X{x} Y{y} Z{z}")

    def set_units_mm(self):
        self.send_cmd("G21")

    def set_feed_rate(self, feed_rate=100):
        self.send_cmd(f"F{feed_rate}")

    def set_pos(self, x, y, z=0):
        self.send_cmd(f"G1 X{x} Y{y} Z{z}")

    def send_cmd(self, cmd):
        self.ser.write(cmd.encode() + b";\r\n")

        ack = b'ok\r\n'
        r = self.ser.read_until(ack)
        assert ack in r



if __name__ == "__main__":
    grbl = Grbl()
    grbl.set_pos(2, 0)
