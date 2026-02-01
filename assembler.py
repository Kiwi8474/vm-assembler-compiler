import sys

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

def assemble(filename):
    labels = {}
    current_address = 0x0200
    lines_to_process = []

    # 1. Pass: Labels sammeln
    with open(filename, "r") as f:
        for line in f:
            line = line.strip().split(";")[0]
            if not line: continue
            
            if line.startswith(".org"):
                current_address = int(line.split()[1], 0)
            elif line.endswith(":"):
                labels[line[:-1]] = current_address
            elif line.startswith(".db"):
                # Hier berechnen wir, wie viele Bytes dazukommen
                data_parts = line[3:].split(",")
                lines_to_process.append((current_address, line))
                current_address += len(data_parts) # Jedes Komma-Element ist 1 Byte
            else:
                lines_to_process.append((current_address, line))
                current_address += 3 # Normale Befehle sind 3 Bytes

    binary = b""
    for addr, line in lines_to_process:
        if line.startswith(".db"):
            # Direkt Bytes schreiben
            data_parts = line[3:].split(",")
            for val_str in data_parts:
                binary += bytes([int(val_str.strip(), 0)])
        else:
            binary += assemble_line(line, labels)
    
    return binary

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python assembler.py <file.asm> <sector_number>")
        sys.exit(1)

    input_file = sys.argv[1]
    target_sector = int(sys.argv[2])

    bytecode = assemble(input_file)

    if len(bytecode) > 512:
        print(f"Warnung: {input_file} ist mit {len(bytecode)} Bytes zu groß für einen Sektor!")

    padded_bytecode = bytecode.ljust(512, b'\x00')

    try:
        with open("disk.bin", "r+b") as f:
            f.seek(target_sector * 512)
            f.write(padded_bytecode)
        print(f"Erfolg! {input_file} wurde in Sektor {target_sector} geschrieben.")
    except FileNotFoundError:
        print("Fehler: disk.bin existiert nicht.")