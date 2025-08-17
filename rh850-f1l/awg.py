from Exscript.protocols.telnetlib import Telnet

class Awg:
    PORT = 5025

    def __init__(self, host="192.168.1.87"):
        self.conn = Telnet(host=host, port=self.PORT)

        self._offset = {}
        self._delay = {}
        self._amplitude = {}
        self._period = {}

    def init_for_glitching(self, channel=1):
        self.output_state(channel, False)
        self.apply_pulse(channel)

        self.burst_state(channel, True)
        self.burst_mode(channel)
        self.trigger_source(channel)
        self.burst_n_cycles(channel)
        self.trigger_delay(channel, 0.0)
        self.burst_phase(channel, 180)
        # self.burst_phase(channel, 0)
        self.output_idle(channel, "TOP")


    def read_response(self):
        response = ""

        while not response.endswith("\n"):
            response += self.conn.read_some()

        return response[:-1]

    def send_cmd(self, cmd):
        self.conn.write(cmd.encode() + b"\n")

    def ident(self):
        self.send_cmd("*IDN?")
        return self.read_response()

    def output_state(self, channel, state):
        assert channel > 0, "Channel number must be greater than 0"
        state = "ON" if state else "OFF"
        cmd = f":OUTPut{channel}:STATe {state}"
        self.send_cmd(cmd)

    def output_idle(self, channel, position="TOP"):
        assert channel > 0, "Channel number must be greater than 0"
        cmd = f":OUTPut{channel}:IDLE {position}"
        self.send_cmd(cmd)

    def apply_pulse(self, channel, frequency=1, amplitude=2e-3, offset=0, phase=0):
        assert channel > 0, "Channel number must be greater than 0"
        cmd = f":SOURce{channel}:APPLy:PULSe {frequency}, {amplitude}, {offset}, {phase}"
        self.send_cmd(cmd)

    def period(self, channel, period):
        assert channel > 0, "Channel number must be greater than 0"
        period *= 2.0

        if self._period.get(channel, None) != period:
            cmd = f":SOURce{channel}:PERiod {period}"
            self.send_cmd(cmd)
            self._period[channel] = period

    def frequency(self, channel, frequency):
        assert channel > 0, "Channel number must be greater than 0"
        cmd = f":SOURce{channel}:FREQuency {frequency}"
        self.send_cmd(cmd)

    def burst_state(self, channel, state):
        assert channel > 0, "Channel number must be greater than 0"
        state = "ON" if state else "OFF"
        cmd = f":SOURce{channel}:BURSt:STATe {state}"
        self.send_cmd(cmd)

    def burst_mode(self, channel, mode="TRIGgered"):
        assert channel > 0, "Channel number must be greater than 0"
        assert mode in ["TRIGgered", "GATed"], "Mode must be 'TRIGgered' or 'GATed'"
        cmd = f":SOURce{channel}:BURSt:MODE {mode}"
        self.send_cmd(cmd)

    def burst_n_cycles(self, channel, cycles=1):
        assert channel > 0, "Channel number must be greater than 0"
        assert cycles > 0, "Number of cycles must be greater than 0"
        cmd = f":SOURce{channel}:NCYCles {cycles}"
        self.send_cmd(cmd)

    def trigger_delay(self, channel, delay):
        assert channel > 0, "Channel number must be greater than 0"

        if self._delay.get(channel, None) != delay:
            cmd = f":TRIGger{channel}:DELay {delay}"
            self.send_cmd(cmd)
            self._delay[channel] = delay

    def burst_phase(self, channel, phase):
        assert channel > 0, "Channel number must be greater than 0"
        cmd = f":SOURce{channel}:BURSt:PHASE {phase}"
        self.send_cmd(cmd)

    def amplitude(self, channel, amplitude):
        assert channel > 0, "Channel number must be greater than 0"

        if self._amplitude.get(channel, None) != amplitude:
            cmd = f":SOURce{channel}:VOLTage {amplitude}"
            self.send_cmd(cmd)
            self._amplitude[channel] = amplitude

    def offset(self, channel, offset):
        assert channel > 0, "Channel number must be greater than 0"

        if self._offset.get(channel, None) != offset:
            cmd = f":SOURce{channel}:VOLTage:OFFSet {offset}"
            self.send_cmd(cmd)
            self._offset[channel] = offset

    def trigger_source(self, channel, source="EXTernal"):
        assert channel > 0, "Channel number must be greater than 0"
        assert source in ["INTernal", "EXTernal"], "Source must be 'INTernal', 'EXTernal'"
        cmd = f":TRIGger{channel}:SOURce {source}"
        self.send_cmd(cmd)

    def glitch_voltage(self, channel, idle, glitch):
        assert channel > 0, "Channel number must be greater than 0"
        # assert glitch < idle, "Glitch voltage must be less than idle voltage"

        amplitude = abs(idle - glitch)
        offset = (glitch + idle) / 2

        self.offset(channel, offset)
        self.amplitude(channel, amplitude)


if __name__ == "__main__":
    awg = Awg()
    print(awg.ident())

    awg.init_for_glitching()

    awg.period(1, 500e-9)
    awg.glitch_voltage(1, 1.25, 0.5)
    awg.output_state(1, True)
