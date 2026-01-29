import os
import datetime
import sys
import re
from assembler import assemble

# --- AST NODES ---
class NumberNode:
    def __init__(self, value):
        self.value = int(value, 0)
    def __repr__(self): return f"Num({self.value})"

class DerefNode:
    def __init__(self, target_node):
        self.target = target_node
    def __repr__(self): return f"Deref({self.target})"

class BinOpNode:
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right
    def __repr__(self): return f"BinOp({self.left} {self.op} {self.right})"

class AssignNode:
    def __init__(self, target_node, value_node):
        self.target = target_node  # Kann jetzt NumberNode ODER DerefNode sein!
        self.value = value_node
    def __repr__(self): return f"Assign({self.target} = {self.value})"

class LabelNode:
    def __init__(self, name):
        self.name = name.replace(":", "")

class GotoNode:
    def __init__(self, target):
        if isinstance(target, str) and target.startswith("0x"):
            self.target = int(target, 0)
        elif target.isdigit():
            self.target = int(target)
        else:
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

# --- TOKENIZER ---
TOKEN_SPEC = [
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
    ('LABEL',     r'[A-Za-z_][A-Za-z0-9_]*:'),
    ('NAME',      r'[A-Za-z_][A-Za-z0-9_]*'),
    ('COMMA',     r','),
    ('WHITESPACE', r'\s+'),
]

def tokenize(code):
    tokens = []
    tok_regex = '|'.join('(?P<%s>%s)' % pair for pair in TOKEN_SPEC)
    for mo in re.finditer(tok_regex, code):
        kind = mo.lastgroup
        if kind == 'WHITESPACE': continue
        tokens.append((kind, mo.group()))
    return tokens

# --- PARSER ---
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
            raise Exception(f"Erwartete {expected_type}, bekam {token[0]}")
        self.pos += 1
        return token

    def parse_factor(self):
        token = self.peek_token()
        if token[0] == 'LPAREN':
            self.eat('LPAREN')
            node = self.parse_expression() # Rekursion! Wir parsen alles in der Klammer
            self.eat('RPAREN')
            return node
        elif token[0] == 'DEREF':
            self.eat('DEREF')
            # Hier auch wichtig: Erlaube Ausdrücke nach dem $, nicht nur Nummern!
            # return DerefNode(self.parse_factor()) 
            return DerefNode(NumberNode(self.eat('NUMBER')[1]))
        elif token[0] == 'NUMBER':
            return NumberNode(self.eat('NUMBER')[1])
        raise Exception(f"Faktor Fehler: {token}")

    def parse_expression(self):
        node = self.parse_factor()
        while self.peek_token() and self.peek_token()[0] == 'OP':
            op = self.eat('OP')[1]
            node = BinOpNode(node, op, self.parse_factor())
        return node

    def parse_statement(self):
        t = self.peek_token()
        if t[0] == 'DIRECTIVE': return self.parse_directive()
        if t[0] == 'LABEL': return LabelNode(self.eat('LABEL')[1])
        if t[0] == 'GOTO': return self.parse_goto()
        if t[0] == 'OUT':
            self.eat('OUT')
            port = self.parse_expression() # Welcher Port?
            self.eat('COMMA')
            data = self.parse_expression() # Welche Daten?
            self.eat('SEMICOLON')
            return OutNode(port, data)
        if t[0] == 'IF': return self.parse_if()
        if t[0] in ['NUMBER', 'DEREF']:
            node = self.parse_assignment()
            self.eat('SEMICOLON')
            return node
        raise Exception(f"Syntax Fehler bei {t}")

    def parse_assignment(self):
        target = self.parse_factor() 
        self.eat('ASSIGN')
        value = self.parse_expression()
        return AssignNode(target, value)

    def parse_goto(self):
        self.eat('GOTO')
        target = self.eat()[1]
        self.eat('SEMICOLON')
        return GotoNode(target)

    def parse_directive(self):
        name = self.eat('DIRECTIVE')[1]
        val = self.eat('NUMBER')[1]
        return DirectiveNode(name, val)

    def parse_if(self):
        self.eat('IF')
        left = self.parse_expression()
        op = self.eat()[1] # == oder !=
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

# --- GENERATOR ---
if_label_count = 0

def generate_expression_asm(node):
    if isinstance(node, NumberNode):
        return f"movi r0, {hex(node.value)}"
    if isinstance(node, DerefNode):
        return f"movi r1, {hex(node.target.value)}\npeek r0, r1"
    if isinstance(node, BinOpNode):
        left = generate_expression_asm(node.left)
        res = f"{left}\nmov r3, r0\n"
        res += generate_expression_asm(node.right)
        res += f"\nmov r2, r0\nmov r0, r3\n"
        res += "add r0, r2" if node.op == '+' else "sub r0, r2"
        return res

def generate_asm(statements, is_sub_block=False):
    global if_label_count
    asm = []
    
    # ORG nur ganz am Anfang schreiben, nicht in Unterblöcken!
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
        elif isinstance(stmt, AssignNode):
            # 1. Wert berechnen (z.B. 65 oder 0xFF)
            asm.append(generate_expression_asm(stmt.value))
            asm.append("mov r10, r0") # Wert SICHER in r10 parken
            
            # 2. Zieladresse bestimmen
            if isinstance(stmt.target, NumberNode):
                # Direkte Adresse (z.B. 0x8000)
                asm.append(f"movi r1, {hex(stmt.target.value)}")
            elif isinstance(stmt.target, DerefNode):
                # Indirekte Adresse (z.B. $0x8000)
                # Wir berechnen den Ausdruck INNERHALB des $...
                asm.append(generate_expression_asm(stmt.target.target)) 
                # Jetzt steht in r0 die Adresse (z.B. 0x8000)
                # Wir müssen JETZT peeken, um die ECHTE Zieladresse zu kriegen
                asm.append("mov r1, r0")
                asm.append("peek r0, r1") 
                # Jetzt steht in r0 die 65! Das ist unser Ziel.
                asm.append("mov r1, r0") 

            # 3. Finaler Poke
            asm.append("mov r0, r10") # Den Wert (0xFF) zurückholen
            asm.append("poke r0, r1") # Wert (0xFF) an Adresse (65)
        elif isinstance(stmt, GotoNode):
            target = hex(stmt.target) if isinstance(stmt.target, int) else stmt.target
            asm.append(f"movi r15, {target}")
        elif isinstance(stmt, OutNode):
            # Port in r5, Daten in r6 laden (als Beispiel)
            asm.append(generate_expression_asm(stmt.port))
            asm.append("mov r5, r0")
            asm.append(generate_expression_asm(stmt.data))
            asm.append("mov r6, r0")
            asm.append("out r5, r6")
        elif isinstance(stmt, IfNode):
            if_label_count += 1
            label_end = f"_endif_{if_label_count}"
            
            # 1. Linke Seite berechnen -> r5
            asm.append(generate_expression_asm(stmt.left))
            asm.append("mov r5, r0")
            # 2. Rechte Seite berechnen -> r6
            asm.append(generate_expression_asm(stmt.right))
            asm.append("mov r6, r0")
            
            # 3. Sprung-Ziel laden
            asm.append(f"movi r4, {label_end}")
            
            # 4. Vergleich (Invertiert, um den Block zu überspringen!)
            if stmt.op == "==":
                asm.append("jne r5, r6, r4")
            else:
                asm.append("je r5, r6, r4")
            
            # 5. Block-Inhalt (Rekursion!)
            asm.append(generate_asm(stmt.block, is_sub_block=True))
            asm.append(f"{label_end}:")
            
    # Halt-Befehl nur am Ende des Hauptprogramms
    if not is_sub_block:
        asm.append("movi r15, 0x10000") # Dein System-Halt
        
    return "\n".join(asm)

def generate_expression_asm(node):
    """Rekursive Funktion, die ASM für Rechnungen baut"""
    if isinstance(node, NumberNode):
        return f"movi r0, {hex(node.value)}"
    
    if isinstance(node, DerefNode):
        # r1 = Adresse, dann r0 = [r1] (peek)
        # Beachte: node.target ist wieder ein Node (meist NumberNode)
        return f"movi r1, {hex(node.target.value)}\npeek r0, r1"

    if isinstance(node, BinOpNode):
        # 1. Linke Seite (Ergebnis in r0)
        left_asm = generate_expression_asm(node.left)
        
        # 2. Wir brauchen r0 für die rechte Seite, also r0 -> r3 retten
        # (Einfaches Register-Management für den Anfang)
        save_asm = "mov r3, r0"
        
        # 3. Rechte Seite (Ergebnis in r0)
        right_asm = generate_expression_asm(node.right)
        
        # 4. Rechnen (r3 OP r0 -> r0)
        # Wir tauschen r0 und r2 für die OP
        prep_op = "mov r2, r0\nmov r0, r3" 
        
        if node.op == '+':
            op_asm = "add r0, r2"
        elif node.op == '-':
            op_asm = "sub r0, r2"
        elif node.op == '*':
            op_asm = "mul r0, r2"
        elif node.op == '/':
            op_asm = "div r0, r2"
        else:
            op_asm = "; OP nicht implementiert"
            
        return f"{left_asm}\n{save_asm}\n{right_asm}\n{prep_op}\n{op_asm}"

    return ""

def compile(input_file):
    with open(input_file, "r") as f:
        code = f.read()
    
    # 1. In Tokens zerlegen
    tokens = tokenize(code)
    
    # 2. Baum bauen (AST Liste)
    parser = Parser(tokens)
    statements = parser.parse_program() # Holt alle Zeilen!
    
    # 3. ASM Generierung
    # Wir übergeben die Liste der Statements an unseren Generator
    asm_output = generate_asm(statements)
    
    return asm_output

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