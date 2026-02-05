import sys
import os

isa = {
    "nop": 0x0,
    "mov": 0x1,
    "movi": 0x2,
    "add": 0x3,
    "sub": 0x4,
    "mul": 0x5,
    "div": 0x6,
    "out": 0x7,
    "je": 0x8,
    "jne": 0x9,
    "peek": 0xA,
    "poke": 0xB,
    "load": 0xC,
    "save": 0xD,
    "pop": 0xE,
    "push": 0xF
}

def assemble_line(line, labels):
    parts = line.replace(",", "").split()
    if not parts: return b""
    
    mnemonic = parts[0].lower()
    opcode = isa[mnemonic]

    def reg(s):
        return int(s.lower().replace("r", ""))

    def get_val(s):
        if s in labels:
            return labels[s]
        return int(s, 0)

    reg_a = reg(parts[1])
    b1 = (opcode << 4) | (reg_a & 0x0F)

    if mnemonic in ["movi"]:
        val = get_val(parts[2])
        b2 = (val >> 8) & 0xFF
        b3 = val & 0xFF
    else:
        reg_b = reg(parts[2]) if len(parts) > 2 else 0
        reg_c = reg(parts[3]) if len(parts) > 3 else 0
        b2 = (reg_b << 4) | (reg_c & 0x0F)
        b3 = 0x00

    return bytes([b1, b2, b3])

def assemble(filename, external_labels=None):
    labels = external_labels.copy() if external_labels else {}
    current_address = 0x200
    lines_to_process = []

    with open(filename, "r") as f:
        for line in f:
            line = line.strip().split(";")[0]
            if not line: continue
            
            if line.startswith(".org"):
                current_address = int(line.split()[1], 0)
            elif line.endswith(":"):
                labels[line[:-1]] = current_address
            elif line.startswith(".db"):
                data_parts = line[3:].split(",")
                lines_to_process.append((current_address, line))
                current_address += len(data_parts)
            elif line.startswith(".dw"):
                data_parts = line[3:].split(",")
                lines_to_process.append((current_address, line))
                current_address += len(data_parts) * 2
            else:
                lines_to_process.append((current_address, line))
                current_address += 3

    binary = b""
    for addr, line in lines_to_process:
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
        else:
            binary += assemble_line(line, labels)
    
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