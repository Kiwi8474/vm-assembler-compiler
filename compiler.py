import os
import datetime
import sys
import re
from assembler import assemble

class NumberNode:
    def __init__(self, value):
        self.value = int(value, 0) # Wandelt 0x123 oder 123 in echte Zahlen um
    def __repr__(self): return f"Num({self.value})"

class DerefNode:
    def __init__(self, target_node):
        self.target = target_node # Das Ziel (z.B. ein NumberNode)
    def __repr__(self): return f"Deref({self.target})"

class BinOpNode:
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right
    def __repr__(self): return f"BinOp({self.left} {self.op} {self.right})"

class AssignNode:
    def __init__(self, target_addr, value_node):
        self.target = int(target_addr, 0)
        self.value = value_node
    def __repr__(self): return f"Assign({hex(self.target)} = {self.value})"

TOKEN_SPEC = [
    ('NUMBER',   r'(0x[0-9A-Fa-f]+|\d+)'),  # Hexadezimal oder Dezimal
    ('ASSIGN',   r'='),                     # Zuweisung
    ('DEREF',    r'\$'),                    # Pointer Dereferenzierung
    ('OP',       r'[+\-*/]'),                # Arithmetik
    ('LPAREN',   r'\('),                    # (
    ('RPAREN',   r'\)'),                    # )
    ('WHITESPACE', r'\s+'),                 # Leerzeichen (ignorieren wir)
]

def tokenize(code):
    tokens = []
    tok_regex = '|'.join('(?P<%s>%s)' % pair for pair in TOKEN_SPEC)
    
    for mo in re.finditer(tok_regex, code):
        kind = mo.lastgroup
        value = mo.group()
        if kind == 'WHITESPACE':
            continue
        tokens.append((kind, value))
    return tokens

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek_token(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def eat(self, expected_type=None):
        token = self.peek_token()
        if not token:
            raise Exception("Unerwartetes Ende des Codes!")
        if expected_type and token[0] != expected_type:
            raise Exception(f"Syntax-Fehler: Erwartete {expected_type}, bekam {token[0]}")
        self.pos += 1
        return token

    def parse_factor(self):
        """Ein Faktor ist die kleinste Einheit: Eine Zahl oder ein Deref."""
        token = self.peek_token()
        
        if token[0] == 'DEREF':
            self.eat('DEREF')
            addr_token = self.eat('NUMBER')
            return DerefNode(NumberNode(addr_token[1]))
        
        elif token[0] == 'NUMBER':
            num_token = self.eat('NUMBER')
            return NumberNode(num_token[1])
        
        raise Exception(f"Unbekannter Faktor: {token}")

    def parse_expression(self):
        """Verarbeitet Rechnungen wie A + B - C"""
        node = self.parse_factor()
        
        # Solange danach ein Operator kommt, hängen wir ihn dran
        while self.peek_token() and self.peek_token()[0] == 'OP':
            op_token = self.eat('OP')
            right_node = self.parse_factor()
            node = BinOpNode(node, op_token[1], right_node)
            
        return node

    def parse_assignment(self):
        """Das Haupt-Statement: Ziel = Ausdruck"""
        target_token = self.eat('NUMBER') # Die Zieladresse
        self.eat('ASSIGN')
        expression_tree = self.parse_expression()
        return AssignNode(target_token[1], expression_tree)

def compile(input_file):
    with open(input_file, "r") as f:
        code = f.read()
    
    # 1. In Tokens zerlegen
    tokens = tokenize(code)
    
    # 2. Baum bauen (AST)
    parser = Parser(tokens)
    # Für den Anfang gehen wir davon aus, dass nur EINE Zeile drin steht
    # Später machen wir eine Schleife für das ganze File
    ast = parser.parse_assignment()
    
    # 3. Hier kommt später der Generator, der aus dem 'ast' ASM macht
    # Erst mal geben wir einen Platzhalter zurück
    print(f"AST gebaut: {ast}")
    return ".org 0x0400"

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python assembler.py <source.c> <sector>")
        sys.exit(1)

    input_file = sys.argv[1]
    target_sector = int(sys.argv[2])

    asm_code = compile(input_file)
    asm_file_name = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.asm"
    with open(asm_file_name, "w") as f:
        f.write(asm_code)

    bytecode = assemble(asm_file_name)
    os.remove(asm_file_name)

    if len(bytecode) > 512:
        print(f"Warnung: {input_file} ist mit {len(bytecode)} Bytes zu groß für einen Sektor!")

    try:
        with open("disk.bin", "r+b") as f:
            f.seek(target_sector * 512)
            f.write(bytecode)
        print(f"Erfolg! {input_file} wurde in Sektor {target_sector} geschrieben.")
    except FileNotFoundError:
        print("Fehler: disk.bin existiert nicht.")