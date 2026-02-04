# MX-ASM Language Specification & Toolchain Manual

---

## 0. Table of Contents
- [1\. Language Overview](#1-language-overview)
- [2\. Syntax & Formatting](#2-syntax--formatting)
- [3\. Assembler Directives](#3-assembler-directives)
- [4\. Tooling mxa (The Assembler)](#4-tooling-mxa-the-assembler)
    - [4.1 Sector Deployment Logic](#41-sector-deployment-logic)

---

## 1. Language Overview
MX-ASM is the low-level symbolic language for the MX-26 processor series. It provides a 1:1 mapping to machine opcodes while supporting labels and data definitions for streamlined development.

## 2. Syntax & Formatting
The language is designed for clarity and rapid parsing.

- **Mnemonics:** Case-insensitive (e.g., `MOVI` is equivalent to `movi`).
- **Registers:** Defined as `r0` through `r15`.
- **Comments:** Everything following a semicolon is ignored by the parser.
- **Labels:** Defined by a trailing colon. Labels store the memory address of the next instruction.

### Instruction structure
`[label:] [mnemonic] [regA], [regB/imm], [regC] [; comment]`

## 3. Assembler Directives
Directives control the assembly process and do not represent CPU instructions.

| Directive | Description | Example |
| :--- | :--- | :--- |
| `.org [addr]` | Sets the starting memory address. Defaults to `0x200` if not specified | `.org 0x400` |
| `.db [val]` | Defines raw bytes (comma-seperated list) | `.db 0x48, 0x49, 0` |

## 4. Tooling mxa (The Assembler)
The `mxa` utility is the official implementation of the MX-ASM specification. It is a sector-aware assembler designed to interface directly with virtual disk images.

### 4.1 Sector Deployment Logic
Unlike standard assemblers, `mxa` targets specific hardware blocks (sectors) on the `disk.bin` image.

**Command Usage:**
`mxa <source.asm> <target sector>`

**Key Features:**
- **Automated Padding:** If the assembled bytecode is smaller than 512 bytes, `mxa` automatically pads the remaining space with `0x00` to maintain sector alignment.
- **Multi-Sector Support:** If the binary exceeds 512 bytes, `mxa` calculates the required span and warns the developer if the size exceeds a single block.
- **Direct Injection:** The utility seeks to `target_sector * 512` and writes the padded binary directly into the disk image.

---

### MX-Technologies Inc. | R&D Division | Lead Architect: [Kiwi8474](https://github.com/Kiwi8474)