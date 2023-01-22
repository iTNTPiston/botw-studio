"""
Generate syms.ld from comments in code

The links must be declared in block comments (/**/), and can have 1 link per block comment and 1 block comment per line

This is the format of the links. Spaces are not significant
/* [VERSION][TYPE] KEY=VALUE, ...*/

VERSION: either 1.5.0 or 1.6.0
TYPE: either link-data, link-func, or link-addr
KEY & VALUE pairs:
    symbol=MANGLED_SYMBOL: required, the mangled symbol to link
    uking_name=UKING_NAME: only for data and func, optional. Define the symbol to link to either in data_symbols.csv or uking_functions.csv. If ignored, defaults to MANGLED_SYMBOL
    address=ADDRESS: only for addr, required. The raw address to link to

Example:
/* [1.5.0][link-func] symbol=_ZN4sead10TextWriter6printfEPKcz, uking_name=sead::TextWriter::printf */

Run example: mkdir -p build && python tools/gen_syms_ld.py src build/syms.ld
Or run `just ld`

"""

from os.path import isfile, isdir, join
from os import listdir
import csv
import sys

# Offset for symbols in main (beginning of mod - beginning of main)
MAIN_OFFSET = {
    "1.5.0": "0x2d91000",
    "1.6.0": "0x3483000"
}

EXTENSIONS = [
    ".cpp",
    ".c",
    ".hpp",
    ".h"
]

CUSTOM_HEADER = """
/*
 *  This is a generated file
 *  DO NOT EDIT THIS FILE DIRECTLY
 *  Generate with `just ld` instead
 */

"""
# Keys in .link.toml
TYPE_FUNC = "link-func"
TYPE_DATA = "link-data"
TYPE_ADDR = "link-addr"
KEY_SYMBOL = "symbol"
KEY_ADDRESS = "address"
KEY_UKING_NAME = "uking_name"

DATA_SYMBOL_PATH = "libs/botw/data/data_symbols.csv"
FUNC_SYMBOL_PATH = "libs/botw/data/uking_functions.csv"

# Address Prefix to strip (and check) in botw csv files
ADDR_PREFIX = "0x00000071"
def parse_address(raw_addr):
    """Strip the 0x00000071"""
    if not raw_addr.startswith(ADDR_PREFIX):
        return None
    return "0x" + raw_addr[len(ADDR_PREFIX):]

def read_uking_data_symbols(file, addr_set, symbol_map):
    """Read uking data symbols into map from data_symbols.csv"""
    total_count = 0
    print("Reading", file)
    with open(file, "r", encoding="utf-8") as csv_file:
        reader = csv.reader(csv_file)
        for row in reader:
            # Skip invalid rows
            if len(row) < 2:
                continue
            raw_addr = row[0]
            data_name = row[1]
            if len(data_name) > 0:
                addr_str = parse_address(raw_addr)
                if addr_str is None:
                    print("Error: Invalid Address: ", raw_addr)
                    continue
                if addr_str in addr_set:
                    print("Error: Duplicate Address: ", raw_addr)
                    continue
                addr_set.add(addr_str)
                symbol_map[data_name] = addr_str
                total_count+=1
    print(f"Loaded {total_count} uking data symbols.")

def read_uking_func_symbols(file, addr_set, symbol_map):
    """Read uking func symbols into map from uking_functions.csv"""
    total_count = 0
    with open(file, "r", encoding="utf-8") as csv_file:
        reader = csv.reader(csv_file)
        for row in reader:
            # Skip invalid rows
            if len(row) < 4:
                continue
            raw_addr = row[0]
            # Skip the headers
            if raw_addr == "Address":
                continue
            func_name = row[3]
            if len(func_name) > 0:
                addr_str = parse_address(raw_addr)
                if addr_str is None:
                    print("Error: Invalid Address: ", raw_addr)
                    continue
                if addr_str in addr_set:
                    print("Error: Duplicate Address: ", raw_addr)
                    continue
                addr_set.add(addr_str)
                symbol_map[func_name] = addr_str
                total_count+=1

    print(f"Loaded {total_count} uking func symbols.")


def run(root_directory, target):
    """Main"""

    func_map = {
        "1.5.0": {},
        "1.6.0": {}
    }
    data_map  = {
        "1.5.0": {},
        "1.6.0": {}
    }
    addr_map = {
        "1.5.0": {},
        "1.6.0": {}
    }
    uking_addr_set = set()
    print("Scanning source files")

    if not process_path(root_directory, func_map, data_map, addr_map):
        print()
        print("There were error(s) when processing source files")
        exit(1)

    len_resolve = len(func_map["1.5.0"]) + len(data_map["1.5.0"])
    print(f"Need to resolve {len_resolve} symbol(s)")

    symbols_resolve_ok = True
    
    if len(data_map) > 0:
        uking_data_symbols = {}
        read_uking_data_symbols(DATA_SYMBOL_PATH, uking_addr_set, uking_data_symbols)
        for mangled_name, uking_name in data_map["1.5.0"].items():
            if not resolve_link_to_uking(\
                addr_map["1.5.0"], uking_name, mangled_name, uking_data_symbols, "data"):
                symbols_resolve_ok = False

    if len(func_map) > 0:
        uking_func_symbols = {}
        read_uking_func_symbols(FUNC_SYMBOL_PATH, uking_addr_set, uking_func_symbols)
        for mangled_name, uking_name in func_map["1.5.0"].items():
            if not resolve_link_to_uking(\
                addr_map["1.5.0"], uking_name, mangled_name, uking_func_symbols, "func"):
                symbols_resolve_ok = False

    if not symbols_resolve_ok:
        print()
        print("There were error(s) when resolving symbols")
        exit(1)

    total_symbols_150 = 0
    total_symbols_160 = 0
    
    
    with open(target, "w+", encoding="utf-8") as target_file:
        target_file.write(CUSTOM_HEADER)
        target_file.write("\n/* 1.5.0 */\n")
        for addr, symbols in addr_map["1.5.0"].items():
            for symbol in symbols:
                target_file.write(create_linker_script_line(addr, symbol, "1.5.0"))
                total_symbols_150+=1
        target_file.write("\n/* 1.6.0 */\n")
        for addr, symbols in addr_map["1.6.0"].items():
            for symbol in symbols:
                target_file.write(create_linker_script_line(addr, symbol, "1.6.0"))
                total_symbols_160+=1
    print(f"Written {total_symbols_150} 1.5.0 symbol links.")
    print(f"Written {total_symbols_160} 1.6.0 symbol links.")
    print(f"Saved {target}")


def process_path(path, func_map, data_map, addr_map):
    """Recursively process scripts under path"""
    if isfile(path):
        for ext in EXTENSIONS:
            if path.endswith(ext):
                return process_file(path, func_map, data_map, addr_map)
        return True

    if isdir(path):
        ok = True
        for sub_path in listdir(path):
            if not process_path(join(path, sub_path), func_map, data_map, addr_map):
                ok = False
        return ok
    return True

def process_file(path, func_map, data_map, addr_map):
    """Process source file"""

    with open(path, "r", encoding="utf-8") as source_file:
        for line_number, line in enumerate(source_file):
            start_index = line.find("/*")
            if start_index < 0:
                continue

            end_index = line.find("*/", start_index+2)
            if end_index < 0:
                continue

            comment = line[start_index+2:end_index].strip()
            version, comment = strip_first_bracket(comment)

            if not version or version not in MAIN_OFFSET:
                continue
            link_type, comment = strip_first_bracket(comment)

            if not link_type or link_type not in [TYPE_ADDR, TYPE_DATA, TYPE_FUNC]:
                continue

            data = parse_key_value_pairs(comment)

            if KEY_SYMBOL not in data:
                print(f"Error: in {path}({line_number}): property \"symbol\" missing from link declaration")
                return False

            symbol = data[KEY_SYMBOL]
            if link_type == TYPE_FUNC:
                if version == "1.6.0":
                    print(f"Error: in {path}({line_number}): only link-addr is supported for 1.6.0. Symbol: \"{symbol}\"")
                    return False
                if symbol in func_map[version]:
                    print(f"Error: in {path}({line_number}): duplicate func symbol \"{symbol}\"")
                    return False
                if KEY_UKING_NAME in data:
                    func_map[version][symbol] = data[KEY_UKING_NAME]
                else:
                    func_map[version][symbol] = symbol
            elif link_type == TYPE_DATA:
                if version == "1.6.0":
                    print(f"Error: in {path}({line_number}): only link-addr is supported for 1.6.0. Symbol: \"{symbol}\"")
                    return False
                if symbol in func_map[version]:
                    print(f"Error: in {path}({line_number}): duplicate data symbol \"{symbol}\"")
                    return False
                if KEY_UKING_NAME in data:
                    data_map[version][symbol] = data[KEY_UKING_NAME]
                else:
                    data_map[version][symbol] = symbol

            else:
                if version == "1.5.0":
                    print(f"Warning: in {path}({line_number}): link-addr is not recommended for 1.5.0. Symbol: \"{symbol}\"")

                if KEY_ADDRESS not in data:
                    print(f"Error: in {path}({line_number}): property \"address\" missing from link-addr declaration")
                    return False
                address = data[KEY_ADDRESS]
                if address not in addr_map[version]:
                    addr_map[version][address] = []
                addr_map[version][address].append(symbol)

    return True
               

def strip_first_bracket(text: str):
    start_index = text.find("[")
    if start_index < 0:
        return None, None
    end_index = text.find("]", start_index)
    if end_index < 0:
        return None, None
    return text[start_index+1:end_index], text[end_index+1:]

def parse_key_value_pairs(text: str):
    pairs = [ x.strip() for x in text.split(",") ]
    data = {}
    for pair in pairs:
        key, value = [ x.strip() for x in pair.split("=", 1) ]
        data[key] = value
    return data

def resolve_link_to_uking(addr_map, uking_name, mangled_name, uking_symbols, symbol_type):
    """
        Search for uking_name in uking_symbols,
            and add the address to addr_map which links to mangled_name
        Return true if successful
    """
    if uking_name in uking_symbols:
        address = uking_symbols[uking_name]
        if address not in addr_map:
            addr_map[address] = []
        addr_map[address].append(mangled_name)
        return True

    if mangled_name != uking_name:
        print(f"Error: Fail to link {symbol_type} symbol {mangled_name} ({uking_name})")
    else:
        print(f"Error: Fail to link {symbol_type} symbol {mangled_name}")
    return False

def create_linker_script_line(address, mangled_name, version):
    """Generate line in syms.ld"""
    return f"{mangled_name} = {address} - {MAIN_OFFSET[version]};\n"

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Args: source directory, output file")
        exit(1)
    run(sys.argv[1], sys.argv[2])