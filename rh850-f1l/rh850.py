import struct

def make_pkt(data):
    pkt = b"\x01"
    pkt += struct.pack('!H', len(data))
    pkt += data

    # Checksum
    chk = (256 - sum(pkt[1:])) & 0xff
    pkt += bytes([chk, 0x03])

    return pkt

def as_hex(s):
    return "".join([f"\\x{ord(c):02x}" for c in s])

def read_block(target, block, gc):
    start, end = block

    # print("reading flash", hex(start), hex(end))
    pkt = make_pkt(b'\x15' + struct.pack('>II', start, end))

    target.write(pkt)
    resp = target.read(6)

    if resp == '\x81\x00\x02\x95\xc3\xa6':
        print("Auth error")
        gc.add("normal")
        return None

    if resp != '\x81\x00\x01\x15\xea\x03':
        print("wrong read ack", as_hex(resp))
        gc.add("reset")
        return None

    rem = end - start
    dat = b""

    while rem > 0:
        target.write(b'\x81\x00\x01\x15\xea\x03')
        length = target.read(3)

        if len(length) != 3:
            print("wrong length received", as_hex(length))
            return None

        length = bytes([ord(c) for c in length])
        length = struct.unpack('!H', length[1:])[0] - 1 # Data starts with 0x15

        resp = b""
        while len(resp) < length + 3:
            resp += bytes([ord(c) for c in target.read(target.in_waiting())])
            time.sleep(0.05)

        dat += resp[1:-2]
        rem -= length

    gc.add("success")
    return dat
