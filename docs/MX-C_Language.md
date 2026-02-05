# MX-C Language Specification & Toolchain Manual

---

## 0. Table of Contents
- [1\. Language Overview & Philosophy](#1-language-overview--philosophy)
- [2\. Basic Syntax & Data Types](#2-basic-syntax--data-types)
    - [2.1 Strict Typing requirement](#21-strict-typing-requirement)
    - [2.2 Memory Access & Dereferencing](#22-memory-access--dereferencing)
    - [2.3 Strings](#23-strings)
    - [2.4 Flexible Typing & Casting](#24-flexible-typing--casting)
    - [2.5 Operators](#25-operators)
    - [2.6 Literals](#26-literals)
- [3\. Compiler Directives](#3-compiler-directives)
    - [3.1 Symbolic Names (#define)](#31-symbolic-names-define)
    - [3.2 File Inclusion (#include)](#32-file-inclusion-include)
    - [3.3 Conditional Compilation (#ifdef, #ifndef, #else, #endif)](#33-conditional-compilation-ifdef-ifndef-else-endif)
    - [3.4 Compiler Messages & Export](#34-compiler-messages--exports)
    - [3.5 Storage & Memory Directives](#35-storage--memory-directives)
- [4\. Control Flow](#4-control-flow)
    - [4.1 Conditional Branching (if)](#41-conditional-branching-if)
    - [4.2 Unconditional Branching (Labels & Goto)](#42-unconditional-branching-labels--goto)
    - [4.3 Iteration (while)](#43-iteration-while)
    - [4.4 Conditional Operators](#44-conditional-operators)
- [5\. Functions & Subroutines](#5-functions--subroutines)
    - [5.1 Declaration & Parameter Storage](#51-declaration--parameter-storage)
    - [5.2 Calling Functions](#52-calling-functions)
    - [5.3 Return Values](#53-return-values)
    - [5.4 Important Constraints](#54-important-constraints)
- [6\. Inline Assembly](#6-inline-assembly)
    - [6.1 The asm Block](#61-the-asm-block)
    - [6.2 Behavior and Safetey](#62-behavior-and-safetey)
- [7\. Hardware I/O & Storage](#7-hardware-io--storage)
    - [7.1 Output Ports (out)](#71-output-ports-out)
    - [7.2 Memory Mapped Input (MMIO)](#72-memory-mapped-input-mmio)
    - [7.3 Persistent Storage (load & save)](#73-persistent-storage-load--save)
- [8\. Toolchain & Compilation](#8-toolchain--compilation)
    - [8.1 Usage](#81-usage)
    - [8.2 Compiler Flags](#82-compiler-flags)
    - [8.3 Modular Linking (Export & Import)](#83-modular-linking-export--import)
- [9\. Conventions & Best Practices](#9-conventions--best-practices)
    - [9.1 Register Usage in asm Blocks](#91-register-usage-in-asm-blocks)
    - [9.2 Standard Memory Layout](#92-standard-memory-layout)
    - [9.3 Include Guard](#93-include-guards)
    - [9.4 Function Parameter Tagging](#94-function-parameter-tagging)
    - [9.5 Infinite Loops](#95-infinite-loops)
- [10\. Troubleshooting](#10-troubleshooting)

---

## 1. Language Overview & Philosophy
MX-C is a low-level systems language specifically engineered for the MX-26 processor series. It bridges the gap between raw Assembly and high-level logic, providing a "C-like" experience without sacrifing direct hardware control.

**Key Principles:**
- **Static First:** No hidden memory allocation. The programmer is the master of memory.
- **Transparency:** Every line of MX-C-code maps directly to lines of MX-ASM.
- **Minimalist Syntax:** No unnecessary parentheses or boilerplate.
- **No Entry Restrictions:** Unlike standard C, MX-C does not require a `main()` function. Execution starts at the first line of the file.

## 2. Basic Syntax & Data Types
MX-C is strictly typed. Every memory operation (assignment, dereference, or cast) requires an explicit type specification. This ensures compatibility with the registers and prevents accidental bit-width mismatches.

| Type | Size | Description |
| :--- | :--- | :--- |
| uint8 | 8-bit | Used for characters and small flags |
| uint16 | 16-bit | Standard word size for addresses and integers |
| void | -  | Keyword used to declare functions. More precise description in [Chapter 5](#5-functions--subroutines) |

### 2.1 Strict Typing Requirement
Unlike higher-level languages, MX-C does not infer types from context. You must explicitly state the data width for every operation.

**Rules:**
- **Assignments:** A type must precede the target address.
- **Value Access ($\)**: When reading a value from memory, a type must be placed before the \$ operator.
- **Literals:** Constants default to uint16 unless a cast is used.

**Example:**
```c
uint16 0x87D0 = 0xABCD; // Correct: Explicit 16-bit assignment
uint8 $0x87D0 = 0xFF; // Correct: Explicit 8-bit write via pointer
0x87D0 = 5; // Error: Missing type keyword
```

### 2.2 Memory Access & Dereferencing
In MX-C, there is a strict distinction between a memory address (a literal uint16) and its value.
- **Literal Address:** Writing a hex value (e.g., 0x8000) refers to the address location itself.
- **Value Access (\$):** The `$` operator is used to access the data stored at a specific address.

| Syntax | Description | Example |
| :--- | :--- | :--- |
| `0xXXXX` | The raw address | `uint16 0x87D0 = 5;` |
| `$0xXXXX` | The value at the address | `if $0x87D0 == 5 { ... }` |
| `$$0xXXXX` | Double dereference (Pointer-Pointer) | `uint16 $$0x87D0 = 1;` |

### 2.3 Strings
MX-C supports string literals enclosed in double qoutes. When a string is defined, the compiler automatically stores it as a null-terminated byte sequence and returns a memory address of the first character of the string if used in an expression.

**Example:**
```c
#define msg 0x87D0
uint16 msg = "Hello, World!";
out 0x01, $$msg; // Outputs 'H' to the character port
```

### 2.4 Flexible Typing & Casting
In MX-C, types are not "locked" to a memory address. The type keyword (uint8/uint16) acts as an instruction for the compiler on how many bytes to read or write at that specific moment.
- **Default behavior:** If no type is specified, the compiler defaults to uint16.
- **On-the-fly casting:** You can treat any address as a different type at any time.

**Example:** This is particularly useful for splitting a 16-bit word into two 8-bit bytes.
```c
uint16 0x87D0 = 0xABCD;
uint8 0x87E0 = uint8 $0x87D0;
uint8 0x87E1 = uint8 $0x87E1;
```

**Note on Endianness:** MX-C follows the Big-Endian architecture of the MX-26 series. The most significant byte (MSB) is stored at the lower address.

### 2.5 Operators
| Operator | Description |
| :--- | :--- |
| `+` | Adds two values |
| `-` | Subtracts two values |
| `*` | Multiplies two values |
| `/` | Divides two values |
| `%` | Applies a modulo-operation to two values |
| `( )` | Since the compiler cannot multiply before it adds, parantheses are used in long operations |

### 2.6 Literals
MX-C supports different ways to represent constant values:
- **Integer Literals:** Can be written in decimal or hexadecimal
- **Character Literals:** Single characters enclosed in single qoutes. The compiler automatically converts these to their corresponding 8-bit ASCII value.

**Example:**
```c
#define VRAM 0x8000
uint8 $VRAM = 'A'; // Internally stored as 65
uint8 $VRAM = 10; // Decimal ASCII for line feed
```

## 3. Compiler Directives
Directives are instructions for the compiler that control the build process rather than being translated into direct CPU instructions.

### 3.1 Symbolic Names (#define)
The `#define` directive creates an alias for a memory address or a constant value to improve code readability.

**Example:**
```c
#define VRAM 0x8000
uint8 $VRAM = 'X';
```

### 3.2 File inclusion (#include)
Allows merging multiple source files. The preprocessor replaces the `#include` line with the entire content of the target file.

**Example:**
```c
#include "header.c"
#include "drivers/display.c"
```

### 3.3 Conditional Compilation (#ifdef, #ifndef, #else, #endif)
Enables or disables code blocks based on whether a symbolic name is defined. This is crucial for hardware-specific builds.

**Example:**
```c
#define DEBUG_MODE
#ifdef DEBUG_MODE
    out 0x01, 'D';
#endif
```

### 3.4 Compiler Messages & Exports
You can trigger messages during the compilation process or mark symbols for the linker.

- `#info "msg"`, `#debug "msg"`, `#warn "msg"`: Prints a message to the console during compilation
- `#error "msg"`: Aborts compilation with a fatal error.
- `#export <label>`: Marks a label to be included in the -export JSON file.

**Example:**
```c
#ifndef VRAM_START
    #error "VRAM_START not defined!"
#endif
```

### 3.5 Storage & Memory Directives
These directives define where and how the program is stored on the MX-system.

| Directive | Type | Description |
| :--- | :--- | :--- |
| `#org <addr>` | Mandatory | Sets the memory address where the code is loaded |
| `#sector <n>` | Mandatory | Sets the starting disk sector |
| `#sectors <n>` | Mandatory | Reserves a fixed number of sectors (pads with `0x00`) |

**Example:**
```c
#org 0x200 // Compiler resolves labels as if the program gets loaded at 0x200. Does not load the program itself!
#sector 1 // Program starts at sector 1 (after boot sector)
#sectors 4 // Reserve 2KB of space regardless of code size
```

## 4. Control Flow
MX-C follows a minimalist approach to branching. Logical evaluations do not require parantheses, reducing visual clutter and mapping directly to CPU status flags.

### 4.1 Conditional Branching (if)
The `if` statement evaluates a single condition. If the condition is met, the code within the mandatory curly braces `{ }` is executed.

**Format:**
```c
if <value1> <operator> <value2> {
    // If body
}
```

**Example:**
```c
#define PLAYER_X 0x87D0

if uint16 $PLAYER > 0x4F { // Check if the value at PLAYER_X is greater than 79
    uint16 $PLAYER_X = 0; // Reset position to 0
}
```

### 4.2 Unconditional Branching (Labels & goto)
For manual flow control, MX-C allows the use of labels and the goto command.

**Format:**
```c
name: // Defines a label at the current code position
goto <target>; // Jumps to a label or a specific memory address
```

**Example:**
```c
main_loop:
// ...
goto main_loop; // Creates an infinite loop
```

### 4.3 Iteration (while)
The `while` statement repeats a block of code as long as the condition remains true. Like the `if` statement, it uses minimalist syntax without parentheses.

**Format:**
```c
while <value1> <operator> <value2> {
    // While body
}
```

**Example:**
```c
#define COUNTER 0x87D0
uint16 COUNTER = 0;

while uint16 $COUNTER < 10 {
    uint16 $COUNTER = uint16 $COUNTER + 1;
}
```

### 4.4 Conditional Operators

| Operator | Description |
| :--- | :--- |
| `==` | Execute if equal |
| `!=` | Execute if not equal |
| `<` | Execute if less |
| `>` | Execute if more |

## 5. Functions & Subroutines
Functions allow the encapsulation of logic and the reuse of code blocks. In MX-C, functions are defined using a specific memory-mapping syntax for parameters.

### 5.1 Declaration & Parameter Storage
To define a function, use the `void` keyword followed by the function name. Parameters are declared by specifying the memory address where the passed value should be stored.

**Format:**
```c
void <name>(<address1>, <address2>, ...) {
    // Function body
    return;
}
```

**Example:**
```c
// The caller pushes a value; the function stores it at 0x87E0
void print(0x87E0) {
    // Within this block, 0x87E0 holds the passed argument.
    // We can now use it directly:
    uint16 0x87E2 = $0x87E0;
    return;
}
```

### 5.2 Calling Functions
A function is called by its name followed by the arguments in parentheses. Arguments can be literals, addresses or expressions.

**Example:**
```c
#define MY_STRING 0x9000
print(MY_STRING); // Passes the address 0x9000 to the function
```

### 5.3 Return Values
Functions can return a value to the caller. A function call can therefore be used as a value within an expression, such as an assignment or a condition. Functions in MX-C can return either no value or exactly one value.

- **Void Return:** Used to simply exit the function. `return;`
- **Value Return:** Used to pass a result back to the caller. The result can be a literal, an address or a complex expression. `return $0x87E0 + 5;`

**Example:**
```c
#define result 0x87D0
uint16 result = calculate_sum(5, 10);

if get_status() == 1 {
    // ...
}
```

### 5.4 Important Constraints
- **Return Statement:** Every function must have at least one `return;` statement (or `return <value>;`) in every possible execution path.
- **Non-Recursion:** Due to the static nature of parameter mapping, functions in MX-C are not recursive. Calling a function within itself will lead to unpredictable results as parameter addresses are overwritten.

## 6. Inline Assembly
For performance-critical tasks, special CPU instructions, or direct hardware access, MX-C allows you to embed raw MX-ASM code directly.

### 6.1 The asm Block
The `asm` keyword opens a block where tokens are collected and passed directly to the assembler. Within this block, the standard MX-C syntax rules are suspended in favor of MX-ASM.

**Format:**
```c
asm {
    // Raw MX-ASM logic
}
```

**Example:**
```c
asm {
    movi r0, 0xABCD;
    movi r1, 0x2;
    out r1, r0; // Outputs 0xABCD to port 0x2
}
```

### 6.2 Behavior and Safetey
- **Semicolons:** Inside an `asm` block, a semicolon is treated as a line break for the assembler.
- **Register Freedom:** You have full access to all registers.
- **Automatic Reset:** After an `asm` block, the compiler resets the Register Manager. It assumes all registers have been modified and clears its internal cache. This prevents the compiler from using "stale" data that might have been overwritten by your assembly code.
- **No Validation:** The MX-C compiler does not validate the assembly-code. Errors within the `asm` block will only be caught during the assembly stage.

## 7. Hardware I/O & Storage
MX-C interacts with the MX-series hardware through direct port output and memory-mapped input. This architecture allows for a standardized way to communicate with peripherals across different CPU models.

### 7.1 Output Ports (out)
The `out` command sends data to specific hardware ports. These ports are used to interface with the system's primary output devices, such as serial consoles or debug displays.

**Standard Port Map (Architecture Default):**
| Port | Mode | Description |
| :--- | :--- | :--- |
| `0x01` | Char Mode | Outputs the value as an ASCII character (e.g, 65 -> 'A') |
| `0x02` | Int Mode | Outputs the value as a Decimal and Hexadecimal string |

**Format:**
```c
out <port>, <value>;
```

**Example:**
```c
out 0x01, 75; // Outputs 'K'
out 0x01, 'A'; // Outputs 'A'
out 0x01, 10; // Outputs a Newline
out 0x02, 512; // Outputs "512 / 0x200"
```

### 7.2 Memory Mapped Input (MMIO)
Input handling is achieved via Memory Mapped I/O. Peripheral data is mapped to specific, high-range memory addresses.

**Important:** MMIO addresses in the MX-architecture are 8-bit only. Always use the uint8 keyword when reading or writing to these addresses to avoid "garbage data" from adjacent memory cells.

**Keyboard Handshake Protocol**
The keyboard buffer requires a manual reset. Once a key is read, the programmer must write `0` back to the address to signal the VM that it is ready for the next character.

**Example:**
```c
#define KEY_BUF 0xFFFF
#define key 0x87D0
uint16 key = uint8 $KEY_BUF;

if key != 0 {
    // Process key...
    uint8 $KEY_BUF = 0; // Clear for next key
}
```

### 7.3 Persistent Storage (load & save)
To move data between the system's RAM and the 512-byte disk sectors, MX-C provides the `load` and `save` instructions.

**Format:**
```c
load <sector>, <address>; // Copies 512 bytes from disk to RAM
save <sector>, <address>; // Copies 512 from RAM to disk
```

**Memory Wrapping:* If an operation exceeds the address space, the data transfer automatically wraps around to address `0x0000`.

**Example:**
```c
load 0, 0x200; // Load boot sector
save 10, 0x400; // Save RAM 0x400 to sector 10
```

## 8. Toolchain & Compilation
The official MX-C compiler `mxc` is a multi-stage tool that handles preprocessing, compilation and linking. It directly interfaces with the virtual disk system of the MX-Processors.

### 8.1 Usage
The compiler is executed via the command line. It requires a source file.

**Command Format:** `python mxc.py <source.c> [flags]`

### 8.2 Compiler Flags
| Flag | Description |
| :--- | :--- |
| `-n` | Compiles without writing to `disk.bin` |
| `-info` | Shows the binary size and sector usage |
| `-asm` | Keeps the temporary Assembly file (`temp_XXXX.asm`) |
| `-export <file>` | Exports labeled symbols to a JSON file |
| `-import <file>` | Imports symbols from a JSON file for external calls |

### 8.3 Modular Linking (Export & Import)
MX-C features a built-in JSON linker. This allows you to call functions or access variables defined in separate compiled binaries.
- **Exporting:** Label your function or variable and use the `-export` flag.
- **Importing:** Use the `-import` flag to make those labels available in your current project. This is essential for building OS kernels or shared libraries.

## 9. Conventions & Best Practices
To ensure code maintainability and hardware compatibility, the following conventions are recommended for MX-C development.

### 9.1 Register Usage in `asm` Blocks
While the compiler resets the Register Manager after an `asm` block, you should follow these internal guidelines to avoid side effects:
- **r0 - r13:** General purpose. Use these for temporary calculations.
- **r14:** Used as the hardware stack pointer for `pop` and `push` operations.
- **r15:** Used as the hardware program counter. Set via `mov` or `movi` to an address to jump unconditional.

### 9.2 Standard Memory Layout
While MX-C gives you full control over the RAM, the following layot is the official convention for the MX-series to ensure compatibility with the BIOS and standard libraries.

| Region | Recommended Use | Logic |
| :--- | :--- | :--- |
| `0x0400` | Program Start | Typical location for `#org` |
| `0x87D0 - 0xABFF` | Variable Base | Directly follows VRAM; easy to track |
| `0xAC00 - 0xAFFF` | System Stack | BIOS Default. Grows downwards from `0xAFFF` |
| `0xB000 - 0xFFFB` | High Data | Best for large assets or long-term buffers |

### 9.3 Include Guards
When creating libraries or header files, always wrap the content in a conditional directive to prevent multiple definition errors during the compilation of complex projects.

**Example:**
```c
#ifndef STDIO_C
#define STDIO_C

void print(0x87E0) {
    // ...
    return;
}

#endif
```

### 9.4 Function Parameter Tagging
Since parameters are mapped to fixed addresses, name them clearly to avoid "address collision" (two functions using the same address for different parameters) or ensure, that they do not operate at the same time if using the same address.

**Example:**
```c
#define P_PRINT_CHAR 0x87E0
void print(P_PRINT_CHAR) {
    // ...
}
```

### 9.5 Infinite Loops
For intentional infinite loops (such as the main execution loop or a final idle state), prefer the use of `while 1 == 1 {}` or a similar infinite while-loop over the combination of a label and goto. This improves readability, aligns with high-level language standards and prevents collision with existing labels, as the compiler generates an unique label for every while-loop.

**Example:**
```c
while 1 == 1 {
    check_input();
}
```

## 10. Troubleshooting
Common issues and how to solve them:

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| "Overwritten Params" | Non-recursive function called itself | Use a manual stack or seperate addresses |
| "Garbage MMIO Data" | Used uint16 on 8-bit MMIO port | Always use `uint8` for MMIO ports |
| "Jump out of range" | `#org mismatch` | Ensure `#org` matches the actual load address |

---

### MX-Technologies Inc. | R&D Division | Lead Architect: [Kiwi8474](https://github.com/Kiwi8474)