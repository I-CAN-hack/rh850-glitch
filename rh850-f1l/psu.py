# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "exscript",
# ]
# ///
import sys
from Exscript.protocols.telnetlib import Telnet

class Psu:
    PORT = 5555

    def __init__(self, host="192.168.1.80"):
        self.conn = Telnet(host=host, port=self.PORT)

    def send_cmd(self, cmd):
        self.conn.write(cmd.encode())

    def enable_output(self, channel, state):
        state = "ON" if state else "OFF"
        channel = f"CH{channel}"
        cmd = f":OUTP {channel}, {state}\n"
        self.send_cmd(cmd)

if __name__ == "__main__":
    psu = Psu()
    psu.enable_output(1, sys.argv[1] == "1")
