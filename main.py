# -*- coding: ANSI -*-
#     Script for editing VCCD Files
#     Copyright (C) 2023 EM4Volts
#
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program.  If not, see <https://www.gnu.org/licenses/>.

import sys, json, codecs, os, struct


def write_char(file, char):
    entry = struct.pack('<s', bytes(char, 'utf-8'))
    file.write(entry)

def write_buffer(file, size):
    for i in range(size):
        write_char(file, '')

def read_uint16(file) -> int:
    entry = file.read(2)
    return struct.unpack('<H', entry)[0]

def read_int32(file) -> int:
    entry = file.read(4)
    return struct.unpack('<i', entry)[0]

def read_uint32(file) -> int:
    entry = file.read(4)
    return struct.unpack('<I', entry)[0]

def write_uInt16(file, int):
    entry = struct.pack('<H', int)
    file.write(entry)

def write_Int16(file, int):
    entry = struct.pack('<h', int)
    file.write(entry)

def write_Int32(file, int):
    entry = struct.pack('<i', int)
    file.write(entry)

def write_uInt32(file, int):
    entry = struct.pack('<I', int)
    file.write(entry)

def write_string(file, str):
    for char in str:
        write_char(file, char)
    write_buffer(file, 1)

class VCCD_ENTRY:
    def __init__( self, in_file ):
        self.hash = read_uint32(in_file)
        self.block_number = read_int32(in_file)
        self.offset = read_uint16(in_file)
        self.lenght = read_uint16(in_file)
        self.data = ""
        self.data_offset = 0

class VCCD:

    def __init__( self, in_file , user_specified_encoding):
        self.vccd_file = in_file
        self.magic = self.vccd_file.read(4).decode(user_specified_encoding)
        self.version = read_int32(self.vccd_file)
        self.num_blocks = read_int32(self.vccd_file)
        self.block_size = read_int32(self.vccd_file)
        self.directory_size = read_int32(self.vccd_file)
        self.data_offset = read_int32(self.vccd_file)

        self.entries = []
        for i in range(self.directory_size):
            self.entries.append(VCCD_ENTRY(self.vccd_file))
        #116832
        self.entries_data = []

        self.read_entries_data_offset = self.data_offset

        old_block = 0

        for i in self.entries:
            new_block = i.block_number

            if new_block > old_block: 
                self.read_entries_data_offset += self.block_size
                
            self.vccd_file.seek(self.read_entries_data_offset + i.offset)
            i.data = str( self.vccd_file.read(i.lenght).decode(user_specified_encoding) )
            old_block = i.block_number
        

    def debug_entries( self ):
        entries_count = 1
        for i in self.entries:
            print("++++++++++++++++++++++++++++++++++")
            print(f"debug info for entry |{entries_count}|")
            print("hash             ----", i.hash)
            print("block count      ----", i.block_number)
            print("offset           ----", i.offset)
            print("lenght           ----", i.lenght)
            print(i.data)
            entries_count += 1

    def subtitles_to_json(self):

        subtitles = {

            "version"           :       self.version,
            "block_sizes"       :       self.block_size,
            "subtitle_list"     :       []

        }
        counter = 0
        for i in self.entries:

            entry_template = {
                "hash"              :       i.hash,
                "subtitle_string"   :       "".join(i.data)
                }

            subtitles["subtitle_list"].append(entry_template)
            counter += 1
        return subtitles, counter

def sanitize(obj):
    if isinstance(obj, str):
      return obj.replace('\u0000', '').replace("\u0019", "'")
    if isinstance(obj, list):
      return [sanitize(item) for item in obj]
    if isinstance(obj, tuple):
      return tuple([sanitize(item) for item in obj])
    if isinstance(obj, dict):
      return {k:sanitize(v) for k,v in obj.items()}
    return obj

def write_subtitle_string(in_file, s_string):
    return_string = ""
    for i, c in enumerate(s_string):
        write_string(in_file, c)

class VCCD_JSON_ENTRY():
    def __init__( self, s_hash, s_block_number, s_offset, s_lenght ):
        self.hash = s_hash
        self.block_number = s_block_number
        self.offset = s_offset
        self.lenght = s_lenght

def json_to_vccd(in_file):

    #calculate header
    with open(in_file, 'r') as f:
        subtitles_json = json.load(f)
    
    entry_count = 0
    current_block = 0
    temp_block_lenght = 0
    current_offset = 0

    f = open("subtitles_out.dat", 'w+b')
    f.write(str.encode("VCCD"))
    write_Int32(f, 1)
    f.seek(24)

    for v in subtitles_json["subtitle_list"]:
        entry_count += 1
    data_offset = entry_count * 12 + 4096
    block_size = subtitles_json["block_sizes"]

    for v in subtitles_json["subtitle_list"]:
        subtitle_string = v["subtitle_string"]
        sub_len = len(subtitle_string) * 2 + 2
        if sub_len % 2 != 0:
            sub_len += 1
        temp_block_lenght += sub_len
        

        if temp_block_lenght > block_size:
            temp_block_lenght = 0
            current_block += 1
            current_offset = 0
            data_offset += block_size

        temp_stored_pointer = f.tell()

        f.seek(data_offset + current_offset)
        write_subtitle_string(f, subtitle_string)
        f.seek(temp_stored_pointer)
            
        write_uInt32(f, v["hash"])
        write_Int32(f, current_block)
        write_uInt16(f, current_offset)
        write_uInt16(f, sub_len)
        current_offset += sub_len

    f.seek(8)
    write_Int32(f, current_block)
    write_Int32(f, block_size)
    write_Int32(f, entry_count)
    write_Int32(f, entry_count * 12 + 4096)

    f.close()

    print("\n\n=-----------------------------------------=\n")
    print("WROTE VCCD FILE\n")
    print("block count        ----  ", current_block)
    print("block size         ----  ", block_size)
    print("entries            ----  ", entry_count)
    print("filesize in bytes  ----  ", os.path.getsize(in_file))
    print("\n=-----------------------------------------=\n")

    return
        
if __name__ == "__main__":
    in_file = sys.argv[1]
    user_specified_encoding = "ANSI"
    if in_file.lower().endswith(".json"):
        json_to_vccd(in_file)
    else:
        if len(sys.argv) > 2:
            user_specified_encoding = sys.argv[2]

        print("\n\n=-----------------------------------------=\n")
        print("Reading VCCD file: %s\n" % in_file)
        vccd = VCCD(open(in_file, "rb"), user_specified_encoding)
        print("magic              ----  ", vccd.magic)
        if vccd.magic != "VCCD":
            print("\nFAILED MAGIC CHECK, ABORTING")
        else:
            print("version            ----  ", vccd.version)
            if not vccd.version == 1:
                print("\nUNRECOGNIZED VERSION, ATTEMPTING\n")
            print("block count        ----  ", vccd.num_blocks)
            print("block size         ----  ", vccd.block_size)
            print("entries            ----  ", vccd.directory_size)
            print("data start offset  ----  ", vccd.data_offset)
            temp_dict = vccd.subtitles_to_json()
            f = codecs.open(f"{in_file}_out.json", "w", user_specified_encoding)
            json.dump(sanitize(temp_dict[0]), f, indent=4)
            f.close()
            print(f"\nExtracted {temp_dict[1]} lines")
        print("\n=-----------------------------------------=\n")
        #vccd.debug_entries()

