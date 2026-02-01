import os
import datetime
import sys
import re
from assembler import assemble

class NumberNode:
    def __init__(self, value, size=16):
        self.value = int(value, 0) if isinstance(value, str) else value
        self.size = size
    def __repr__(self): return f"Num({self.value}, {self.size}bit)"

class DerefNode:
    def __init__(self, target_node, size=16):
        self.target = target_node
        self.size = size
    def __repr__(self): return f"Deref({self.target}, {self.size}bit)"

class BinOpNode:
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right
    def __repr__(self): return f"BinOp({self.left} {self.op} {self.right})"

class AssignNode:
    def __init__(self, target_node, value_node, size=16):
        self.target = target_node
        self.value = value_node
        self.size = size
    def __repr__(self): return f"Assign({self.target} = {self.value}, {self.size}bit)"

class LabelNode:
    def __init__(self, name):
        self.name = name.replace(":", "")

class GotoNode:
    def __init__(self, target):
        self.target = target

class DirectiveNode:
    def __init__(self, name, value):
        self.name = name.lower()
        self.value = int(value, 0)

class IfNode:
    def __init__(self, left, op, right, block):
        self.left = left
        self.op = op
        self.right = right
        self.block = block

class OutNode:
    def __init__(self, port, data):
        self.port = port
        self.data = data

class LoadNode:
    def __init__(self, sector, address):
        self.sector = sector
        self.address = address

class SaveNode:
    def __init__(self, sector, address):
        self.sector = sector
        self.address = address

class StringNode:
    def __init__(self, value):
        self.value = value.strip('"')
    def __repr__(self): return f"String({self.value})"

TOKEN_SPEC = [
    ('TYPE',       r'uint8\b|uint16\b'),
    ('DIRECTIVE', r'#[A-Za-z_]+'),
    ('NUMBER',    r'(0x[0-9A-Fa-f]+|\d+)'),
    ('IF',        r'if\b'),
    ('EQ',        r'=='),
    ('NE',        r'!='),
    ('ASSIGN',    r'='),
    ('DEREF',     r'\$'),
    ('OP',        r'[+\-*/]'),
    ('SEMICOLON', r';'),
    ('LBRACE',    r'\{'),
    ('RBRACE',    r'\}'),
    ('LPAREN',    r'\('),
    ('RPAREN',    r'\)'),
    ('GOTO',      r'goto'),
    ('OUT', r'out\b'),
    ('LOAD', r'load\b'),
    ('SAVE', r'save\b'),
    ('CHAR', r"'.'"),
    ('STRING',     r'"[^"]*"'),
    ('LABEL',     r'[A-Za-z_][A-Za-z0-9_]*:'),
    ('NAME',      r'[A-Za-z_][A-Za-z0-9_]*'),
    ('COMMA',     r','),
    ('WHITESPACE', r'\s+'),
]

def preprocess_includes(code, base_path="."):
    include_pattern = r'#include\s+"([^"]+)"'
    
    def replace_match(match):
        filename = match.group(1)
        full_path = os.path.join(base_path, filename)
        if os.path.exists(full_path):
            with open(full_path, "r") as f:
                included_code = f.read()
            return preprocess_includes(included_code, os.path.dirname(full_path))
        else:
            print(f"Warnung: Include-Datei '{filename}' nicht gefunden!")
            return f"// Fehler: {filename} nicht gefunden"

    return re.sub(include_pattern, replace_match, code)

def strip_comments(code):
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    code = re.sub(r'//.*', '', code)
    return code

def tokenize(code):
    tokens = []
    tok_regex = '|'.join('(?P<%s>%s)' % pair for pair in TOKEN_SPEC)
    for mo in re.finditer(tok_regex, code):
        kind = mo.lastgroup
        if kind == 'WHITESPACE': continue
        tokens.append((kind, mo.group()))
    return tokens

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek_token(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def eat(self, expected_type=None):
        token = self.peek_token()
        if not token: raise Exception("Unerwartetes Ende!")
        if expected_type and token[0] != expected_type:
            raise Exception(f"Erwartete {expected_type}, bekam {token[0]}, bei Quellcode {token[1]}")
        self.pos += 1
        return token

    def parse_factor(self, size=16):
        token = self.peek_token()
        if not token: return None

        current_size = 16
        if token[0] == 'TYPE':
            type_str = self.eat('TYPE')[1]
            current_size = 8 if type_str == 'uint8' else 16
            token = self.peek_token()

        if token[0] == 'CHAR':
            val = ord(self.eat('CHAR')[1][1])
            return NumberNode(val, size=8)
        elif token[0] == 'DEREF':
            self.eat('DEREF')
            addr = self.parse_factor() 
            return DerefNode(addr, size=current_size)
        elif token[0] == 'NUMBER':
            return NumberNode(self.eat('NUMBER')[1], size=current_size)
        elif token[0] == 'NAME':
            return self.eat('NAME')[1] 

        raise Exception(f"Unerwartetes Token im Factor: {token}")

    def parse_expression(self):
        node = self.parse_factor()
        while self.peek_token() and self.peek_token()[0] == 'OP':
            op = self.eat('OP')[1]
            node = BinOpNode(node, op, self.parse_factor())
        return node

    def parse_statement(self):
        t = self.peek_token()
        if t is None: return None

        if t[0] == 'LABEL': 
            return LabelNode(self.eat('LABEL')[1])
        if t[0] == 'DIRECTIVE': 
            return self.parse_directive()
        if t[0] == 'GOTO': 
            return self.parse_goto()
        if t[0] == 'IF': 
            return self.parse_if()
        if t[0] == 'OUT':
            self.eat('OUT')
            port = self.parse_expression()
            self.eat('COMMA')
            data = self.parse_expression()
            self.eat('SEMICOLON')
            return OutNode(port, data)

        current_size = 16
        if t[0] == 'TYPE':
            type_str = self.eat('TYPE')[1]
            current_size = 8 if type_str == 'uint8' else 16
            t = self.peek_token()

        if t[0] in ['NUMBER', 'DEREF']:
            node = self.parse_assignment(current_size)
            self.eat('SEMICOLON')
            return node

        if t[0] in ['LOAD', 'SAVE']:
            stmt_type = self.eat()[0]
            sector = self.parse_expression()
            self.eat('COMMA')
            address = self.parse_expression()
            self.eat('SEMICOLON')
            return LoadNode(sector, address) if stmt_type == 'LOAD' else SaveNode(sector, address)
        
        raise Exception(f"Syntax Fehler bei {t}")

    def parse_assignment(self, size):
        target = self.parse_factor() 
        if isinstance(target, DerefNode):
            target.size = size
            
        self.eat('ASSIGN')
        value = self.parse_expression()
        return AssignNode(target, value, size=size)

    def parse_goto(self):
        self.eat('GOTO')
        target = self.parse_expression()
        self.eat('SEMICOLON')
        return GotoNode(target)

    def parse_directive(self):
        name = self.eat('DIRECTIVE')[1]
        val = self.eat('NUMBER')[1]
        return DirectiveNode(name, val)

    def parse_if(self):
        self.eat('IF')
        left = self.parse_expression()
        op = self.eat()[1]
        right = self.parse_expression()
        self.eat('LBRACE')
        block = []
        while self.peek_token() and self.peek_token()[0] != 'RBRACE':
            block.append(self.parse_statement())
        self.eat('RBRACE')
        return IfNode(left, op, right, block)

    def parse_program(self):
        stmts = []
        while self.peek_token(): stmts.append(self.parse_statement())
        return stmts

if_label_count = 0

def generate_asm(statements, is_sub_block=False):
    global if_label_count
    asm = []
    strings_to_embed = []

    if not is_sub_block:
        found_org = False
        for s in statements:
            if isinstance(s, DirectiveNode) and s.name == "#org":
                asm.append(f".org {hex(s.value)}")
                found_org = True
        if not found_org: asm.append(".org 0x0400")

    for stmt in statements:
        if isinstance(stmt, LabelNode):
            asm.append(f"{stmt.name}:")
        elif isinstance(stmt, DirectiveNode):
            if stmt.name == "#sectors":
                continue
        elif isinstance(stmt, AssignNode):
            if isinstance(stmt.value, StringNode):
                str_label = f"str_const_{len(strings_to_embed)}"
                strings_to_embed.append((str_label, stmt.value.value))
                asm.append(f"movi r0, {str_label}")
            else:
                asm.append(generate_expression_asm(stmt.value))
            
            asm.append("mov r10, r0")

            if isinstance(stmt.target, NumberNode):
                asm.append(f"movi r1, {hex(stmt.target.value)}")
            elif isinstance(stmt.target, DerefNode):
                asm.append(f"movi r1, {hex(stmt.target.target.value)}")
                asm.append("movi r2, 0")
                asm.append("peek r0, r1, r2")
                asm.append("mov r1, r0")

            mode = 1 if stmt.size == 8 else 0
            asm.append(f"movi r2, {mode}")
            asm.append("mov r0, r10") 
            asm.append("poke r0, r1, r2")

        if isinstance(stmt, GotoNode):
            if isinstance(stmt.target, str):
                asm.append(f"movi r15, {stmt.target}")
            else:
                asm.append(generate_expression_asm(stmt.target))
                asm.append("mov r15, r0")
        elif isinstance(stmt, OutNode):
            asm.append(generate_expression_asm(stmt.port))
            asm.append("push r0")
            asm.append(generate_expression_asm(stmt.data))
            asm.append("mov r6, r0")
            asm.append("pop r5")
            asm.append("out r5, r6")
        elif isinstance(stmt, (LoadNode, SaveNode)):
            asm.append(generate_expression_asm(stmt.sector))
            asm.append("push r0")
            asm.append(generate_expression_asm(stmt.address))
            asm.append("mov r12, r0")
            asm.append("pop r11")
            asm.append("movi r13, 0")
            cmd = "load" if isinstance(stmt, LoadNode) else "save"
            asm.append(f"{cmd} r11, r12, r13")
        elif isinstance(stmt, IfNode):
            if_label_count += 1
            label_end = f"_endif_{if_label_count}"

            asm.append(generate_expression_asm(stmt.left))
            asm.append("mov r5, r0")
            asm.append(generate_expression_asm(stmt.right))
            asm.append("mov r6, r0")

            asm.append(f"movi r4, {label_end}")

            if stmt.op == "==":
                asm.append("jne r5, r6, r4")
            else:
                asm.append("je r5, r6, r4")

            asm.append(generate_asm(stmt.block, is_sub_block=True))
            asm.append(f"{label_end}:")

    if not is_sub_block:
        asm.append("movi r15, 0xFFFF")

        if strings_to_embed:
            asm.append("\n; --- String Data Section ---")
            for label, text in strings_to_embed:
                asm.append(f"{label}:")
                chars = ", ".join([hex(ord(c)) for c in text])
                asm.append(f".db {chars}, 0x00")
        
    return "\n".join(asm)

def generate_expression_asm(node):
    if isinstance(node, NumberNode):
        return f"movi r0, {hex(node.value)}"
    
    if isinstance(node, DerefNode):
        mode = 1 if node.size == 8 else 0
        addr_asm = generate_expression_asm(node.target)
        return f"{addr_asm}\nmov r1, r0\nmovi r2, {mode}\npeek r0, r1, r2"

    if isinstance(node, BinOpNode):
        left_asm = generate_expression_asm(node.left)
        right_asm = generate_expression_asm(node.right)

        return f"{left_asm}\npush r0\n{right_asm}\nmov r2, r0\npop r3\nmov r0, r3\n" + \
               ("add r0, r2" if node.op == '+' else "sub r0, r2" if node.op == '-' else "mul r0, r2" if node.op == '*' else "div r0, r2")

    return ""

def compile(input_file):
    with open(input_file, "r") as f:
        code = f.read()

    tokens = tokenize(code)

    parser = Parser(tokens)
    statements = parser.parse_program()

    asm_output = generate_asm(statements)
    
    return asm_output

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python compiler.py <source.c> <sector>")
        sys.exit(1)

    input_file = sys.argv[1]
    target_sector = int(sys.argv[2])

    with open(input_file, "r") as f:
        raw_code = f.read()

    clean_code = strip_comments(raw_code)
    source_code = preprocess_includes(clean_code, os.path.dirname(input_file))

    tokens = tokenize(source_code)
    parser = Parser(tokens)
    statements = parser.parse_program()

    max_sectors = 0
    for s in statements:
        if isinstance(s, DirectiveNode) and s.name == "#sectors":
            max_sectors = s.value
            break

    asm_code = generate_asm(statements)

    asm_file_name = f"temp_{datetime.datetime.now().strftime('%H%M%S')}.asm"
    with open(asm_file_name, "w") as f:
        f.write(asm_code)

    bytecode = assemble(asm_file_name)
    os.remove(asm_file_name)

    actual_size = len(bytecode)
    min_needed_sectors = ((actual_size - 1) // 512 + 1) if actual_size > 0 else 1

    final_sector_count = max(min_needed_sectors, max_sectors)

    if max_sectors > 0 and min_needed_sectors > max_sectors:
        print(f"Warnung: {input_file} braucht {min_needed_sectors} Sektoren, aber #sectors ist nur {max_sectors}!")

    target_size = final_sector_count * 512
    padded_bytecode = bytecode.ljust(target_size, b'\x00')

    try:
        with open("disk.bin", "r+b") as f:
            f.seek(target_sector * 512)
            f.write(padded_bytecode)
        print(f"Erfolg! {input_file} ({actual_size} Bytes) wurde in {final_sector_count} Sektoren geschrieben.")
    except FileNotFoundError:
        print("Fehler: disk.bin existiert nicht.")