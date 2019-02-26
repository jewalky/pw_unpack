# -*- coding: utf-8 -*-

import struct
import os
import sys
import zlib
import re
import codecs

if len(sys.argv) < 2:
    print('Usage: unpack.py <pck filename>')
    sys.exit(0)

FILENAME = sys.argv[1]

if not os.path.exists(FILENAME) or not os.path.isfile(FILENAME):
    print('Invalid or nonexistent path:\n%s'%FILENAME)
    sys.exit(1)

KEY_1 = 0xA8937462
KEY_2 = 0xF1A43653
KEY_3 = 0x59374231
ASIG_1 = 0xFDFDFEEE
ASIG_2 = 0xF00DBEEF

VERSION_NEW = [131075]
VERSION_OLD = [131074,131073]

EXTENDED = FILENAME.split('.')[-1].lower() == 'pkx'

CHINESE_ENCODING = 'gb2312'

f = open(FILENAME, 'rb')
f.seek(0, os.SEEK_END)
FILESIZE = f.tell()
f.seek(-4, os.SEEK_END)
pck_version = struct.unpack('<I', f.read(4))[0]
print('PCK version: %d'%pck_version)
pck_entry_count = 0
pck_fat_offset = 0

if pck_version not in VERSION_NEW and pck_version not in VERSION_OLD:
    print('Unknown PCK version. Abort.')
    sys.exit(1)

if EXTENDED and pck_version in VERSION_NEW:
    print('PCK is extended (>2GB)')
elif EXTENDED:
    print('Extended PCK for old version is not supported. Abort.')
    sys.exit(1)

if EXTENDED:
    EXT_FILENAME = '.'.join(FILENAME.split('.')[:-1])+'.pck'
    if not os.path.exists(EXT_FILENAME) or not os.path.isfile(EXT_FILENAME):
        print('Invalid or nonexistent path:\n%s'%EXT_FILENAME)
    ef = open(EXT_FILENAME, 'rb')
    ef.seek(0, os.SEEK_END)
    EXT_FILESIZE = ef.tell()
else:
    EXT_FILENAME = ''
    EXT_FILESIZE = 0
    ef = None

# now, recent PWs have "new version" and "old version" archives
# "new version" cannot be unpacked with sPCK (uses slightly different key)
# apparently "new version" is to support >2gb files in a single archive (uses qword as offsets)
# additionally, sPCK does not support unpacking Models (extended archive, two files)
F_POS = 0
def f_seek(pos, mode=os.SEEK_SET):
    global F_POS
    maxp = EXT_FILESIZE+FILESIZE
    if mode == os.SEEK_END:
        pos = maxp+pos
    elif mode == os.SEEK_CUR:
        pos = F_POS+pos
    F_POS = pos

def f_read(size):
    global F_POS
    if ef is None:
        f.seek(F_POS, os.SEEK_SET)
        d = f.read(size)
        F_POS += len(d)
        return d
    else:
        readnext = F_POS
        if F_POS < EXT_FILESIZE:
            ef.seek(F_POS, os.SEEK_SET)
            ef_d = ef.read(min(EXT_FILESIZE-F_POS, size))
            readnext = 0
        else:
            ef_d = b''
            readnext = F_POS-EXT_FILESIZE
        f.seek(readnext, os.SEEK_SET)
        d = f.read(size-len(ef_d))
        d = b''.join((ef_d, d))
        F_POS += len(d)
        return d

def f_tell():
    return F_POS


if pck_version in VERSION_NEW:
    f_seek(-8, os.SEEK_END)
    pck_entry_count = struct.unpack('<I', f_read(4))[0]
    f_seek(-280, os.SEEK_END)
    pck_fat_offset = struct.unpack('<Q', f_read(8))[0] ^ (KEY_1|0xFFFFFFFF00000000)
elif pck_version in VERSION_OLD:
    f_seek(-8, os.SEEK_END)
    pck_entry_count = struct.unpack('<I', f_read(4))[0]
    f_seek(-272, os.SEEK_END)
    pck_fat_offset = struct.unpack('<I', f_read(4))[0] ^ KEY_1

print('PCK entry count: %d'%pck_entry_count)
print('PCK FAT offset: %08X'%pck_fat_offset)

f_seek(pck_fat_offset)


def unpack_fat_entry(data):
    if pck_version in VERSION_NEW:
        if len(data) != 288:
            data = zlib.decompress(data)
        e_name = data[0:260].decode(CHINESE_ENCODING, 'replace').split('\0')[0]
        e_offset, e_size, e_compressed_size = struct.unpack('<QII', data[264:-8])
    else:
        if len(data) != 276:
            data = zlib.decompress(data)
        e_name = data[0:260].decode(CHINESE_ENCODING, 'replace').split('\0')[0]
        e_offset, e_size, e_compressed_size = struct.unpack('<III', data[260:-4])
    return {'name': e_name, 'offset': e_offset, 'size': e_size, 'compressed': e_compressed_size}

fat = []

for i in range(pck_entry_count):
    e_size, e_size_check = struct.unpack('<II', f_read(8))
    e_size ^= KEY_1
    e_size_check ^= KEY_1 ^ KEY_3
    if e_size != e_size_check:  # I don't really know how much to read in this case.. file was packed by broken util
        print('File size invalid: %d != %d. Abort.'%(e_size, e_size_check))
        sys.exit(1)
    e_data = f_read(e_size)
    e = unpack_fat_entry(e_data)
    fat.append(e)

def print_log(s):
    with codecs.open('unpack.log', 'w', encoding='utf-8') as lf:
        lf.write('%s\n'%s)
        lf.flush()

# directory name for output
OUT_NAME = './'+('.'.join(FILENAME.split('.')[:-1]))+'.files'
if not os.path.exists(OUT_NAME):
    os.mkdir(OUT_NAME)
if not os.path.isdir(OUT_NAME):
    print('Error: output path %s exists, but is not a directory'%OUT_NAME)
    sys.exit(1)

for e in fat:
    print_log(repr(e))
    print('Extract: %s'%(e['name'].encode(CHINESE_ENCODING, 'replace').decode('ascii', 'replace').replace('�', '?')))
    f_seek(e['offset'])
    if f_tell() != e['offset']:
        print('Error: invalid offset %016X, can\'t seek'%e['offset'])
    fdata = f_read(e['compressed'])
    if e['compressed'] != e['size']:
        fdata = zlib.decompress(fdata)
    fname = re.sub(r"[\\\/]+", '/', e['name'])
    out_fname = OUT_NAME+'/'+fname
    os.makedirs(os.path.dirname(out_fname), exist_ok=True)
    with open(out_fname, 'wb') as xf:
        xf.write(fdata)
