#!/usr/bin/env python3

import serial
import time
import struct

def make_pkt(data):
    pkt = b"\x01"
    pkt += struct.pack('!H', len(data))
    pkt += data

    # Checksum
    chk = (256 - sum(pkt[1:])) & 0xff
    pkt += bytes([chk, 0x03])

    return pkt


if __name__ == "__main__":
    conn = serial.Serial('COM4', dsrdtr=False, timeout=0.1)
    pico = serial.Serial('COM5', 115200, timeout=0.1)

    # Generate memory ranges we can read
    blocks = []
    addr = 0x0
    for size in [0x2000] * 8 + [0x8000] * 30:
        blocks.append((addr, addr + size - 1))
        addr += size
    # blocks += [(0x100_0000, 0x100_7fff)] # User Flash

    while True:
        for delay in range(23650, 23750, 10):
            for width in range(17, 20):
                print(f"delay: {delay}, width: {width}")
                pico.write(f'{delay} {width}\n'.encode())

                conn.dtr = True # Release reset line
                time.sleep(0.1)

                conn.write(b'\x00' * 10)
                if conn.read(1) != b'\x00':
                    # Sometimes the DTR line stops working. Open connection again to fix
                    conn.close()
                    conn = serial.Serial('COM4', dsrdtr=False, timeout=0.1)
                    print("wrong resp")
                    continue

                conn.write(b'\x55')
                if conn.read(1) != b'\xc1':
                    print("wrong resp")
                    continue

                # Get device type
                conn.write(b'\x01\x00\x01\x38\xc7\x03') # Device Type Acquisition Command
                if conn.read(6) != b'\x81\x00\x01\x38\xc7\x03':
                    print("wrong resp")
                    continue

                conn.write(b'\x81\x00\x01\x38\xc7\x03')
                if conn.read(30) != b'\x81\x00\x19\x38\x10\x01\xff\x40\x00\x28\x2c\x00\x00\xf4\x24\x00\x00\xf4\x24\x00\x09\x89\x68\x00\x09\x89\x68\x00\xe7\x03':
                    print("wrong resp")
                    continue

                # RES: \x38 (OK)
                # TYP: \x10\x01\xff\x40 \x00\x28\x2c\x00 
                # OSA: \x00\xf4\x24\x00 (Maximum input frequency, 16 Mhz)
                # OSI: \x00\xf4\x24\x00 (Minimum input frequency, 16 Mhz)
                # CPA: \x09\x89\x68\x00 (Maximum system clock frequency, 160 Mhz)
                # CPI: \x09\x89\x68\x00 (Minimum system clock frequency, 160 Mhz)

                # Set frequency
                conn.write(b'\x01\x00\x09\x32\x00\xf4\x24\x00\x09\x89\x68\x00\xb3\x03')
                # COM: \x32 (Frequency Setting Command)
                # OC: \x00\xf4\x24\x00 (Input frequency, 16 MHz)
                # CC: \x09\x89\x68\x00 (System clock frequency, 160Mhz)
                if conn.read(6) != b'\x81\x00\x01\x32\xcd\x03':
                    print("wrong resp")
                    continue

                conn.write(b'\x81\x00\x01\x32\xcd\x03')
                if conn.read(14) != b'\x81\x00\x09\x32\x09\x89\x68\x00\x02\x62\x5a\x00\x0d\x03':
                    print("wrong resp")
                    continue

                # RES: x32
                # FQ: \x09\x89\x68\x00 (System clock frequency, 160 Mhz)
                # PF: \x02\x62\x5a\x00 (Peripheral clock frequency, 40 Mhz)

                # Set bitrate
                conn.write(b'\x01\x00\x05\x34\x00\x00\x25\x80\x22\x03')
                # COM: 0x35 (Bit-Rate Setting Command)
                # BR: \x00\x00\x25\x80 (9600 baud)
                if conn.read(6) != b'\x81\x00\x01\x34\xcb\x03':
                    print("wrong resp")
                    continue  

                # Synchronize!
                conn.write(b'\x01\x00\x01\x00\xff\x03')
                resp = conn.read(7) 

                if resp == b'\x81\x00\x01\x00\xff\x03':
                    print('OK received. Glitched successfully!')

                    # Read flash
                    f = open('out.bin', 'wb')
                    for start, end in blocks:
                        print(hex(start), hex(end))
                        pkt = make_pkt(b'\x15' + struct.pack('>II', start, end))

                        conn.write(pkt)
                        time.sleep(0.1)
                        resp = conn.read(conn.in_waiting)
                        print("read", hex(start), hex(end), pkt, resp)

                        assert resp == b'\x81\x00\x01\x15\xea\x03'

                        # Keep reeding until we have the whole block
                        rem = end - start
                        dat = b""
                        while rem > 0:
                            # Send ACK
                            conn.write(b'\x81\x00\x01\x15\xea\x03')

                            # Get size of the rest of the packet
                            length = conn.read(3) 
                            print("got", length)
                            length = struct.unpack('!H', length[1:])[0] - 1 # Data starts with 0x15
                            
                            # Receive all data
                            print(f"waiting for {length} bytes")
                            resp = b""
                            while len(resp) < length + 3: 
                                resp += conn.read(conn.in_waiting)
                                time.sleep(0.05)

                            print("done", rem, length, resp)
                            dat += resp[1:-2]
                            rem -= length

                        print("writing", len(dat))
                        f.write(dat)
                        f.flush()

                    exit(0)
                elif resp == b'\x81\x00\x02\x80\xdc\xa2\x03':
                    print('Serial programmer connection prohibition error')
                else:
                    print('Unknown error. Resp:', resp)

                conn.dtr = False
                time.sleep(0.2)