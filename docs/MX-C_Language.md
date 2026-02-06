# MX-C Language Specification & Toolchain Manual

---

## 0. Table of Contents
- [1\. Language Overview & Philosophy](#1-language-overview--philosophy)
- [2\. Basic Syntax & Data Types](#2-basic-syntax--data-types)
    - [2.1 Strict Typing requirement](#21-strict-typing-requirement)
    - [2.2 Memory Access & Dereferencing](#22-memory-access--dereferencing)
    - [2.3 Variables (def)](#23-variables-def)
    - [2.4 Arrays & Strings](#24-arrays--strings)
    - [2.5 Flexible Typing & Casting](#25-flexible-typing--casting)
    - [2.6 Operators](#26-operators)
    - [2.7 Literals](#27-literals)
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
- **Assignments:** A type must precede the target address or variable name.
- **Value Access ($\)**: When reading a value from a variable or memory, a type must be placed before the \$ operator.

**Example:**
```c
uint16 0x87D0 = 0xABCD; // Legacy: Explicit 16-bit assignment
uint8 $0x87D0 = 0xFF; // Legacy: Explicit 8-bit write via pointer
0x87D0 = 5; // Error: Missing type keyword
def uint16 my_var = 5; // Modern: Explicit 16-bit variable definition
uint8 $my_var = 0xFF; // Correct: Explicit 8-bit write to variable location
```

### 2.2 Memory Access & Dereferencing
MX-C distinguishes between a memory location (address or variable name) and its stored value.

- **Literal Address:** Writing a hex value (e.g., 0x8000) refers to the address location itself.
- **Value Access (\$):** The `$` operator is used to access the data stored at a specific address.

| Syntax | Description | Example |
| :--- | :--- | :--- |
| `0xXXXX` | The raw address | `uint16 0x87D0 = 5;` |
| `name` | Variable address (Modern) | `uint16 my_var = 10;` |
| `$name` | Value at address/variable | `if uint16 $my_var == 10 { ... }` |
| `$$name` | Double dereference (Pointer) | `uint16 $$my_ptr = 1;` |

### 2.3 Variables (def)
The `def` keyword is used to define named variables. The compiler automatically assigns a safe memory address to these names, preventing collisions that often occur with manual hex-mapping.

**Note:** Definitions are only allowed at the top-level of your code. They cannot be placed inside `if` blocks, `while` loops, or functions. Variables must also be initialized with a literal (number or char) before they can hold results from expressions or functions.

**Example:**
```c
def uint16 player_score = 0;
uint16 player_score = uint16 $player_score + 10;
```

### 2.4 Arrays & Strings
Strings and arrays are contiguous blocks of memory. To optimize speed, MX-C uses a Length-Prefix strategy.

**Layout:** For every arrray, the compiler stores its length as a uint16 immediately before the actual data.
- The `_len` label points to the length field.
- The main label (e.g., `my_array`) points to the first data element.

**Accessing Data & Metadata:**
- **Data:** Use the variable name directly
- **Length:** Access the `_len` label or use the prefix-offset: `uint16 $(my_array - 2)`

**Array Definition Syntax:** Arrays are defined using curly braces `{}`. No size specification is needed; the compiler calculates it automatically.

**Example:**
```c
def uint8 my_bytes = {10, 20, 30}; // my_bytes_len will be 3
def uint16 my_words = {'A', 'B', 'C'}; // my_words_Len will be 3
```

**Indexing:** Elements can be accessed by using square brackets `[]`. The compiler automatically calculates the memory offset based on the element size.

**Important (Bit-Width):** Because MX-C uses a prefix-based type system, the `uint8` or `uint16` keyword placed before the access determines how many bytes are read from or written to the index.

**Strings:** When defining a string, the variable holds the start address of the character sequence and _not_ the first character of the string.

**Example:**
```c
def uint16 message = "Hello, World!\n"; // 'message' points to the 'H' and does not contain the 'H'
```

### 2.5 Flexible Typing & Casting
Types are not "locked" to a memory address. The type keyword acts as an instruction for the compiler on how to interpret the bytes at that moment.

**Example:** This is particularly useful for splitting a 16-bit word into two 8-bit bytes.
```c
def uint16 combined = 0xABCD;
def uint8 high_byte = 0;
def uint8 low_byte = 0;
uint8 high_byte = uint8 $combined; // Reads 0xAB
uint8 low_byte = uint8 $(combined+1); // Reads 0xCD
```

**Note on Endianness:** MX-C follows the Big-Endian architecture of the MX-26 series. The most significant byte (MSB) is stored at the lower address.

### 2.6 Operators
| Operator | Description |
| :--- | :--- |
| `+` | Adds two values |
| `-` | Subtracts two values |
| `*` | Multiplies two values |
| `/` | Divides two values |
| `%` | Applies a modulo-operation to two values |
| `( )` | Since the compiler cannot multiply before it adds, parantheses are used in long operations |

### 2.7 Literals
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

**Note:** You cannot use the def keyword inside a control flow block. All variables must be declared at the top-level scope.

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
| `>` | Execute if greater |
| `>=` | Execute if greater or equal |
| `<=` | Execute if less or equal |

## 5. Functions & Subroutines
Functions allow the encapsulation of logic and the reuse of code blocks. In MX-C, functions are defined using a specific memory-mapping syntax for parameters.

### 5.1 Declaration & Parameter Storage
To define a function, use the `void` keyword followed by the function name. Parameters are declared by providing existing variable names (modern) or specifying the memory address where the passed value should be stored (legacy). When a function is called, the arguments are popped from the stack and stored in these locations.

**Format:**
```c
void <name>(<address1>, <address2>, ...) {
    // Function body
    return;
}
```

**Modern Syntax Example (Recommended):**
```c
def uint16 global_counter_ptr = 0;
def uint16 amount_ptr = 0;
void add_global_counter(amount_ptr) {
    uint16 global_counter_ptr = uint16 $global_counter_ptr + uint16 $amount_ptr;
    return;
}
```

**Legacy Syntax (still supported):**
```c
void add_global_counter(0x87E0) {
    uint16 0x87E2 = uint16 $0x87E2 + uint16 $0x87E0;
    return;
}
```

### 5.2 Calling Functions
A function is called by its name followed by arguments in parentheses. Arguments are pushed onto the hardware stack (r14) before the jump.

**Example:**
```c
strcmp(addr1, addr2); // Pushes addr2, then addr1, then calls strcmp
```

### 5.3 Return Values
Functions can return a single value using the `return <value>;` statement. The result is typically passed back via the hardware stack.

- **Void Return:** Used to simply exit the function. `return;`
- **Value Return:** Used to pass a result back to the caller. The result can be a dereferenced address or to be more modern: a dereferenced variable. `return uint16 $my_return_val;`
- **Stability Best Practice:** You should always store the result in a variable first and then return that variable using a dereference. Returning literals (like `return 1;`) directly can lead to stack corruption or incorrect results.

**Example:**
```c
def uint16 result = 0;
void my_function() {
    uint16 result = 42;
    return uint16 $result;
}
```

MX-C also supports using function calls directly within expressions or conditional statements. This allows for more concise coe by using the return value of a function as an operand without manually storing it in a temporary variable.

**Example:**
```c
if strcmp(uint16 cmd_input, "exit") == 0 {
    uint16 running = 0;
}
```

### 5.4 Important Constraints
- **Initialization of Parameters:** While parameters are defined in the function header, any additional "local" variables used inside the function must be defined using `def` at the top-level (outside the function) and initialized with a literal or array before use.
- **Static Parameter Mapping:** Parameters in MX-C are not stored on a dynamic stack. They are aliases for fixed RAM addresses (defined via def at the top-level).
- **Non-Recursion:** Because each parameter points to a unique, fixed memory location, functions cannot call themselves. A recursive call would overwrite the parameters of the parent call, leading to immediate data corruption.
- **Global Scope Side-Effect:** Parameters are essentially global variables. Modifying a parameter inside a function is identical to modifying its corresponding def variable anywhere else.
- **Return Statement:** Every function must have at least one `return;` statement (or `return <value>;`) in every possible execution path.

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
The `out` command sends data to specific hardware ports. These ports are used to interface with the system's primary output devices, such as serial consoles or debug displays. Each CPU as its own ports but `0x1` and `0x2` are the same for every processor.

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
#ifndef STDIO_H
#define STDIO_H

def print_addr_ptr = 0;
void print(print_addr_ptr) {
    // ...
}

#endif
```

### 9.4 Function Parameter Tagging
Since MX-C uses global scope for all `def` variables and static parameter mapping, name collisions can lead to critical bugs.

- **Prefixing:** Always prefix variables used as function parameters with the function name (e.g., print_ptr).
- **Reuse with Caution:** ONly reuse variable for different functions if you are absolutely certain those functions will never be active at the same time.

**Modern Example:**
```c
def uint16 scroll_target = 0; // Prefixed for the scroll function
void scroll(scroll_target) {
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
| "Garbage MMIO Data" | Used `uint16` on 8-bit MMIO port | Always use `uint8` for MMIO ports |
| "Jump out of range" | `#org` mismatch | Ensure `#org` matches the actual load address |
| "Can't define global variables inside nested blocks" | `def` used inside an if-, while- or function-block | Move the `def` line to the very top of your file, outside of all `{ }` brackets |
| "Variable not defined" | Used a name in a function header or assignment that wasn't created via `def` | Add `def uint16 <name> = 0;` at the top-level of your code. |
| "Array Length Offset" | Pointer arithmetic went into the length field. | Remember: `my_array` points to data, `my_array - 2` points to the length. |

---

### MX-Technologies Inc. | R&D Division | Lead Architect: [Kiwi8474](https://github.com/Kiwi8474)