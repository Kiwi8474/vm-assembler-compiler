import sys
import os
import struct

isa16 = {
    "nop": 0x0, "mov": 0x1, "movi": 0x2, "add": 0x3,
    "sub": 0x4, "mul": 0x5, "jgt": 0x6, "out": 0x7,
    "je": 0x8, "jne": 0x9, "peek": 0xA, "poke": 0xB,
    "jlt": 0xC, "jge": 0xD, "pop": 0xE, "push": 0xF
}

isa32 = {
    "nop": 0x00, "halt": 0x01, "jmp": 0x02, "je": 0x03, "jne": 0x04,
    "jg": 0x05, "jge": 0x06, "jl": 0x07, "jle": 0x08, "call": 0x09,
    "ret": 0x0A, "int": 0x0B, "iret": 0x0C,

    "mov": 0x10, "push": 0x11, "pop": 0x12,

    "add": 0x20, "sub": 0x21, "mul": 0x22, "div": 0x23, "mod": 0x24,

    "and": 0x30, "or": 0x31, "xor": 0x32, "not": 0x33,

    "shl": 0x40, "shr": 0x41, "sar": 0x42, "rol": 0x43, "ror": 0x44,

    "fadd": 0x50, "fsub": 0x51, "fmul": 0x52, "fdiv": 0x53, "fmod": 0x54,

    "fsqrt": 0x60, "fsin": 0x61, "fcos": 0x62, "fabs": 0x63, "f2i": 0x64,
    "i2f": 0x65,

    "gpuclear": 0x70, "gpublit": 0x71, "gpurect": 0x72, "gpuline": 0x73, "gpurectfill": 0x74,
    "gpucirc": 0x75, "gpucircfill": 0x76,

    "time": 0x80, "wait": 0x81, "rand": 0x82,

    "out": 0xF0, "in": 0xF1
}

def get_val(s, labels):
    if s in labels:
        return labels[s]
    try:
        if "." in s:
            f_val = float(s)
            return struct.unpack('>I', struct.pack('>f', f_val))[0]
        return int(s, 0)
    except Exception as e:
        print(f"Error at value {s}: {e}")

def assemble_16(line, labels):
    parts = line.replace(",", "").split()
    if not parts: return b""
    
    mnemonic = parts[0].lower()
    opcode = isa16[mnemonic]

    def reg(s):
        return int(s.lower().replace("r", ""))

    reg_a = reg(parts[1])
    b1 = (opcode << 4) | (reg_a & 0x0F)

    if mnemonic in ["movi"]:
        val = get_val(parts[2], labels)
        b2 = (val >> 8) & 0xFF
        b3 = val & 0xFF
    else:
        reg_b = reg(parts[2]) if len(parts) > 2 else 0
        reg_c = reg(parts[3]) if len(parts) > 3 else 0
        b2 = (reg_b << 4) | (reg_c & 0x0F)
        b3 = 0x00

    return bytes([b1, b2, b3])

def assemble_32(line, labels):
    raw_parts = line.split()
    if not raw_parts: return b""
    
    mnemonic_full = raw_parts[0].lower()

    remaining_line = " ".join(raw_parts[1:])
    args = [a.strip() for a in remaining_line.split(",") if a.strip()]

    size = 2
    is_signed = False

    tokens = mnemonic_full.split('.')
    mnemonic = tokens[0]
    for suffix in tokens[1:]:
        if suffix == "b": size = 0
        elif suffix == "w": size = 1
        elif suffix == "d": size = 2
        elif suffix == "s": is_signed = True

    if mnemonic not in isa32:
        print(f"Unknown command: {mnemonic}")
        return b""
        
    opcode = isa32[mnemonic]
    res = bytearray(8)
    res[0] = opcode

    use_imm = False
    use_indirect_src = False
    use_indirect_dest = False

    def parse_arg(arg):
        nonlocal use_indirect_src, use_indirect_dest
        arg = arg.strip()
        is_ptr = arg.startswith("[") and arg.endswith("]")
        clean = arg.strip("[] ").strip() 
        return is_ptr, clean

    parsed_args = [parse_arg(a) for a in args]

    reg_idx = 0
    regs = [0, 0, 0]
    imm_val = 0

    for i, (is_ptr, val) in enumerate(parsed_args):
        if val.lower().startswith("r") and any(char.isdigit() for char in val):
            r_num = int(''.join(filter(str.isdigit, val)))
            if i == 0 and is_ptr: use_indirect_dest = True
            elif i > 0 and is_ptr: use_indirect_src = True
            if reg_idx < 3:
                regs[reg_idx] = r_num
                reg_idx += 1
        else:
            use_imm = True
            imm_val = get_val(val, labels)
            if i == 0 and is_ptr: use_indirect_dest = True
            elif i > 0 and is_ptr: use_indirect_src = True

    res[1] = (regs[0] << 4) | (regs[1] & 0x0F)
    res[2] = (regs[2] << 4)

    mode = 0
    if use_imm:          mode |= 0x01
    if use_indirect_src:  mode |= 0x02
    if use_indirect_dest: mode |= 0x04
    if is_signed:         mode |= 0x08
    mode |= (size << 4)
    res[3] = mode

    res[4] = (imm_val >> 24) & 0xFF
    res[5] = (imm_val >> 16) & 0xFF
    res[6] = (imm_val >> 8) & 0xFF
    res[7] = imm_val & 0xFF
        
    return bytes(res)

start_address = 0x200
def assemble(filename, external_labels=None):
    labels = external_labels.copy() if external_labels else {}
    current_address = 0x200
    current_bits = 16
    lines_to_process = []

    with open(filename, "r") as f:
        for line in f:
            line = line.strip().split(";")[0]
            if not line: continue
            
            if line.startswith(".org"):
                current_address = int(line.split()[1], 0)
                start_address = current_address
            elif line.startswith(".align"):
                alignment = int(line.split()[1], 0)
                current_address = (current_address + alignment - 1) & ~(alignment - 1)
            elif ":" in line:
                label_part = line.split(":")[0].strip()
                labels[label_part] = current_address
                remaining = line.split(":")[1].strip()
                if not remaining:
                    continue
                line = remaining
            elif line.startswith(".db"):
                data_parts = line[3:].split(",")
                lines_to_process.append((current_address, line, current_bits))
                current_address += len(data_parts)
            elif line.startswith(".dw"):
                data_parts = line[3:].split(",")
                lines_to_process.append((current_address, line, current_bits))
                current_address += len(data_parts) * 2
            elif line.startswith(".dd"):
                data_parts = line[3:].split(",")
                lines_to_process.append((current_address, line, current_bits))
                current_address += len(data_parts) * 4
            elif line.startswith(".bits"):
                current_bits = int(line.split()[1])
                continue
            else:
                lines_to_process.append((current_address, line, current_bits))
                current_address += 8 if current_bits == 32 else 3

    binary = b""
    for addr, line, bits in lines_to_process:
        while len(binary) < (addr - start_address):
            binary += b'\x00'

        if line.startswith(".db"):
            data_parts = line[3:].split(",")
            for val_str in data_parts:
                binary += bytes([int(val_str.strip(), 0)])
        elif line.startswith(".dw"):
            data_parts = line[3:].split(",")
            for val_str in data_parts:
                val = 0
                val_str = val_str.strip()
                if val_str in labels:
                    val = labels[val_str]
                else:
                    val = int(val_str, 0)
                binary += bytes([(val >> 8) & 0xFF, val & 0xFF])
        elif line.startswith(".dd"):
            data_parts = line[3:].split(",")
            for val_str in data_parts:
                val_str = val_str.strip()
                val = labels[val_str] if val_str in labels else int(val_str, 0)
                binary += bytes([(val >> 24) & 0xFF, (val >> 16) & 0xFF, (val >> 8) & 0xFF, val & 0xFF])
        else:
            if bits == 32:
                binary += assemble_32(line, labels)
            else:
                binary += assemble_16(line, labels)
    
    return binary, labels

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python assembler.py <file.asm> <sector_number>")
        sys.exit(1)

    input_file = sys.argv[1]
    target_sector = int(sys.argv[2])

    bytecode, _ = assemble(input_file)

    if len(bytecode) > 512:
        print(f"[Assembler Warning] {input_file} is {len(bytecode)} bytes long and too large for a single sector.")

    if len(bytecode) > 0:
        target_size = ((len(bytecode) - 1) // 512 + 1) * 512
    else:
        target_size = 512

    padded_bytecode = bytecode.ljust(target_size, b'\x00')

    disk_path = "disk.bin"
    if not os.path.exists(disk_path):
        potential_path = os.path.join("..", "emulator", "disk.bin")
        if os.path.exists(potential_path):
            disk_path = potential_path
            
    try:
        with open(disk_path, "r+b") as f:
            f.seek(target_sector * 512)
            f.write(padded_bytecode)
        print(f"[Success] Wrote {len(bytecode)} bytes to sector {target_sector} in {disk_path}.")
    except FileNotFoundError:
        print(f"[Assembler Error] disk.bin not found.")