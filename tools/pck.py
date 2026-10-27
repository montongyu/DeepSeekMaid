"""Read an unencrypted Godot 3/4 PCK without modifying it."""
import argparse
import hashlib
import json
import re
import struct
from pathlib import Path


class Pack:
    def __init__(self, path):
        self.path = Path(path)
        self.entries = {}
        with self.path.open('rb') as f:
            magic, version, major, minor, patch = struct.unpack('<5I', f.read(20))
            if magic != 0x43504447 or version not in (2, 3):
                raise ValueError('Unsupported pack')
            flags, base = struct.unpack('<IQ', f.read(12))
            if flags & 1:
                raise ValueError('Encrypted pack')
            if version == 3:
                directory, = struct.unpack('<Q', f.read(8))
                f.seek(directory)
            else:
                f.seek(96)
            count, = struct.unpack('<I', f.read(4))
            for _ in range(count):
                length, = struct.unpack('<I', f.read(4))
                name = f.read(length).rstrip(b'\x00').decode('utf-8')
                offset, size = struct.unpack('<QQ', f.read(16))
                digest = f.read(16)
                item_flags, = struct.unpack('<I', f.read(4))
                self.entries[name] = (offset + base, size, digest, item_flags)

    def read(self, name):
        offset, size, digest, flags = self.entries[name]
        if flags & 1:
            raise ValueError('Encrypted file')
        with self.path.open('rb') as f:
            f.seek(offset)
            data = f.read(size)
        if hashlib.md5(data).digest() != digest:
            raise ValueError(f'Checksum mismatch: {name}')
        return data


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('pack')
    parser.add_argument('--filter', default='defect|localization/eng/cards')
    parser.add_argument('--extract')
    parser.add_argument('--out')
    args = parser.parse_args()
    pack = Pack(args.pack)
    if args.extract:
        data = pack.read(args.extract)
        if args.out:
            target = Path(args.out)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        else:
            print(data.decode('utf-8'))
    else:
        print('\n'.join(n for n in pack.entries if re.search(args.filter, n)))
