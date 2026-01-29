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

class LabelNode:
    def __init__(self, name):
        self.name = name.replace(":", "") # Wir speichern nur den Namen

class GotoNode:
    def __init__(self, target):
        # target kann ein String (Label) oder ein Integer (Adresse) sein
        if isinstance(target, str) and target.startswith("0x"):
            self.target = int(target, 0)
        elif target.isdigit():
            self.target = int(target)
        else:
            self.target = target # Es ist ein Label-Name (String)

class DirectiveNode:
    def __init__(self, name, value):
        self.name = name.lower() # z.B. "#org"
        self.value = int(value, 0) # Die Adresse

TOKEN_SPEC = [
    ('DIRECTIVE', r'#[A-Za-z_]+'),            # Präprozessor-Direktiven
    ('NUMBER',   r'(0x[0-9A-Fa-f]+|\d+)'),    # Hexadezimal oder Dezimal
    ('ASSIGN',   r'='),                       # Zuweisung
    ('DEREF',    r'\$'),                      # Pointer Dereferenzierung
    ('OP',       r'[+\-*/]'),                 # Arithmetik
    ('SEMICOLON',  r';'),                     # Semikolon. Ende eines Ausdrucks
    ('LPAREN',   r'\('),                      # (
    ('RPAREN',   r'\)'),                      # )
    ('GOTO',     r'goto'),                    # Das Schlüsselwort
    ('LABEL',    r'[A-Za-z_][A-Za-z0-9_]*:'), # Erkennt "name:"
    ('NAME',     r'[A-Za-z_][A-Za-z0-9_]*'),  # Erkennt "name" (ohne Doppelpunkt)
    ('WHITESPACE', r'\s+'),                   # Leerzeichen (ignorieren wir)
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

    def parse_goto(self):
        self.eat('GOTO')
        # Schau, ob danach eine Nummer oder ein Name kommt
        token = self.peek_token()
        if token[0] in ['NUMBER', 'NAME']:
            target = self.eat(token[0])[1]
            self.eat('SEMICOLON')
            return GotoNode(target)
        raise Exception("Nach goto muss eine Adresse oder ein Label kommen!")

    def parse_directive(self):
        token = self.eat('DIRECTIVE')
        value_token = self.eat('NUMBER')
        # Direktiven brauchen bei uns kein Semikolon, wie in C
        return DirectiveNode(token[1], value_token[1])

    def parse_program(self):
        """Liest das ganze File und entscheidet, was für ein Knotentyp kommt."""
        statements = []
        while self.peek_token() is not None:
            token = self.peek_token()
            
            if token[0] == 'DIRECTIVE':
                statements.append(self.parse_directive())
            
            elif token[0] == 'LABEL':
                # Ein Label ist einfach nur der Name mit Doppelpunkt
                label_token = self.eat('LABEL')
                statements.append(LabelNode(label_token[1]))
            
            elif token[0] == 'GOTO':
                statements.append(self.parse_goto())
            
            elif token[0] == 'NUMBER':
                # Wenn eine Nummer am Zeilenanfang steht, ist es eine Zuweisung
                stmt = self.parse_assignment()
                statements.append(stmt)
                self.eat('SEMICOLON')
            
            else:
                raise Exception(f"Unerwartetes Token am Zeilenanfang: {token}")
                
        return statements

def generate_asm(statements):
    full_asm = []
    has_org = False
    
    # Erst mal nach einer ORG-Direktive suchen
    for stmt in statements:
        if isinstance(stmt, DirectiveNode) and stmt.name == "#org":
            full_asm.append(f".org {hex(stmt.value)}")
            has_org = True
            break
            
    # Falls keine da ist, nimm den Standard
    if not has_org:
        full_asm.append(".org 0x0400")

    # Jetzt den Rest generieren
    for stmt in statements:
        if isinstance(stmt, LabelNode):
            full_asm.append(f"{stmt.name}:")
            
        elif isinstance(stmt, AssignNode):
            full_asm.append(generate_expression_asm(stmt.value))
            full_asm.append(f"movi r1, {hex(stmt.target)}")
            full_asm.append("poke r0, r1")
            
        elif isinstance(stmt, GotoNode):
            if isinstance(stmt.target, int):
                # Direkt an eine feste Speicheradresse springen
                full_asm.append(f"movi r15, {hex(stmt.target)}")
            else:
                # Der Assembler setzt die Adresse des Labels für uns ein
                full_asm.append(f"movi r15, {stmt.target}")
    
    full_asm.append("movi r15, 0x10000")
    return "\n".join(full_asm)

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