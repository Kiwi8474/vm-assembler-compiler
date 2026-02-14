import os
import datetime
import sys
import re
import struct
from mxa import assemble

class CompilerError(Exception):
    def __init__(self, message, line=None, token=None):
        self.message = message
        self.line = line
        self.token = token
        super().__init__(self.message)

    def __str__(self):
        prefix = f"[Error in line {self.line}] " if self.line else "[Compiler Error] "
        token_info = f" (at '{self.token}')" if self.token else ""
        return f"\n{prefix}{self.message}{token_info}"

class NumberNode:
    def __init__(self, value, size=32, is_float=False, source_line=None):
        if value is None:
            raise CompilerError("Parser delivered 'None'.")

        if isinstance(value, str):
            try:
                self.value = int(value, 0)
            except ValueError:
                self.value = value
        else:
            self.value = value
            
        self.is_float = is_float
        self.size = size
        self.source_line = source_line

class DerefNode:
    def __init__(self, target_node, size=32, source_line=None):
        self.target = target_node
        self.size = size
        self.source_line = source_line
    def __repr__(self): return f"Deref({self.target}, {self.size}bit)"

class BinOpNode:
    def __init__(self, left, op, right, is_float=False, source_line=None):
        self.left = left
        self.op = op
        self.right = right
        self.is_float = is_float
        self.source_line = source_line
    def __repr__(self): return f"BinOp({self.left} {self.op} {self.right})"

class AssignNode:
    def __init__(self, target_node, value_node, size=32, source_line=None):
        self.target = target_node
        self.value = value_node
        self.size = size
        self.source_line = source_line
    def __repr__(self): return f"Assign({self.target} = {self.value}, {self.size}bit)"

class LabelNode:
    def __init__(self, name, source_line=None):
        self.name = name.replace(":", "")
        self.source_line = source_line

class GotoNode:
    def __init__(self, target, source_line=None):
        self.target = target
        self.source_line = source_line

class DirectiveNode:
    def __init__(self, name, value, source_line=None):
        self.name = name.lower()
        self.value = int(value, 0)
        self.source_line = source_line

class IfNode:
    def __init__(self, left, op, right, block, else_block=None, source_line=None):
        self.left = left
        self.op = op
        self.right = right
        self.block = block
        self.else_block = else_block
        self.source_line = source_line

class OutNode:
    def __init__(self, port, data, source_line=None):
        self.port = port
        self.data = data
        self.source_line = source_line

class StringNode:
    def __init__(self, value, source_line=None):
        self.value = value.strip('"')
        self.source_line = source_line
    def __repr__(self): return f"String({self.value})"

class FunctionDefNode:
    def __init__(self, name, params, block, source_line=None):
        self.name = name
        self.params = params
        self.block = block
        self.source_line = source_line

class CallNode:
    def __init__(self, name, args=None, source_line=None):
        self.name = name
        self.args = args if args is not None else []
        self.source_line = source_line

class ReturnNode:
    def __init__(self, value_node=None, source_line=None):
        self.value = value_node
        self.source_line = source_line

class InlineAsmNode:
    def __init__(self, content, source_line=None):
        self.content = content
        self.source_line = source_line
    def __repr__(self): return f"InlineAsm({self.content[:20]}...)"

class WhileNode:
    def __init__(self, left, op, right, block, source_line=None):
        self.left = left
        self.op = op
        self.right = right
        self.block = block
        self.source_line = source_line

class GlobalVarNode:
    def __init__(self, name, size, value, source_line=None):
        self.name = name
        self.size = size
        self.value = value
        self.source_line = source_line

class ArrayNode:
    def __init__(self, elements, size=32, source_line=None):
        self.elements = elements
        self.size = size
        self.source_line = source_line

TOKEN_SPEC = [
    ('STRUCT',       r'struct\b'),
    ('DEF',       r'def\b'),
    ('ASM',       r'asm\b'),
    ('TYPE',       r'uint8\b|uint16\b|uint32\b|float32\b|int32\b'),
    ('DIRECTIVE', r'[#\.][A-Za-z_]+'),
    ('NUMBER',    r'(0x[0-9A-Fa-f]+|\d+)'),
    ('IF',        r'if\b'),
    ('WHILE',        r'while\b'),
    ('ELSE',       r'else\b'),
    ('SHL',        r'<<'),
    ('SHR',        r'>>'),
    ('EQ',        r'=='),
    ('NE',        r'!='),
    ('LE', r'<='),
    ('GE', r'>='),
    ('LT', r'<'),
    ('GT', r'>'),
    ('ASSIGN',    r'='),
    ('DEREF',     r'\$'),
    ('OP',         r'[+\-*/%&|^]'),
    ('SEMICOLON', r';'),
    ('LBRACE',    r'\{'),
    ('RBRACE',    r'\}'),
    ('LBRACK',    r'\['),
    ('RBRACK',    r'\]'),
    ('LPAREN',    r'\('),
    ('RPAREN',    r'\)'),
    ('GOTO',      r'goto'),
    ('OUT', r'out\b'),
    ('FN',      r'void\b'),
    ('RETURN',  r'return\b'),
    ('CHAR', r"'.'"),
    ('STRING',     r'"[^"]*"'),
    ('LABEL',     r'[A-Za-z_][A-Za-z0-9_]*:'),
    ('NAME',       r'[A-Za-z_][A-Za-z0-9_\.]*'),
    ('COMMA',     r','),
    ('WHITESPACE', r'\s+'),
]

def strip_comments(code):
    code = re.sub(r'/\*.*?\*/', lambda m: '\n' * m.group().count('\n'), code, flags=re.DOTALL)
    code = re.sub(r'//.*', '', code)
    return code

def get_combined_source(filepath):
    if not os.path.exists(filepath):
        print(f"[Warning] File {filepath} not found!")
        return f"// Error: {filepath} not found"

    with open(filepath, "r") as f:
        code = f.read()

    code = strip_comments(code)

    include_pattern = r'#include\s+"([^"]+)"'
    
    def replace_match(match):
        filename = match.group(1)
        full_path = os.path.join(os.path.dirname(filepath), filename)
        return get_combined_source(full_path)

    code = re.sub(include_pattern, replace_match, code)
    return code

def handle_conditionals_and_defines(code):
    lines = code.splitlines()
    output = []
    defines = {}
    active_stack = [True]
    condition_met_stack = [True]

    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()

        if stripped.startswith("#define") and active_stack[-1]:
            parts = stripped.split()
            if len(parts) >= 2:
                name = parts[1]
                value = " ".join(parts[2:]) if len(parts) > 2 else ""
                defines[name] = value
            continue

        if stripped.startswith("#ifdef"):
            name = stripped.split()[1] if len(stripped.split()) > 1 else ""
            met = (name in defines)
            condition_met_stack.append(met)
            active_stack.append(met and active_stack[-1])
            continue
            
        elif stripped.startswith("#ifndef"):
            name = stripped.split()[1] if len(stripped.split()) > 1 else ""
            met = (name not in defines)
            condition_met_stack.append(met)
            active_stack.append(met and active_stack[-1])
            continue

        elif stripped.startswith("#else"):
            if len(active_stack) <= 1:
                raise CompilerError(f"Line {line_num}: #else without #ifdef/#ifndef")
            last_met = condition_met_stack[-1]
            parent_active = active_stack[-2]
            active_stack[-1] = (not last_met) and parent_active
            continue

        elif stripped.startswith("#endif"):
            if len(active_stack) <= 1:
                raise CompilerError(f"Line {line_num}: #endif without matching #ifdef")
            active_stack.pop()
            condition_met_stack.pop()
            continue

        if active_stack[-1]:
            output.append(line)

    if len(active_stack) > 1:
        raise CompilerError("Missing #endif at end of file.")

    return "\n".join(output), defines

def apply_defines(code, defines):
    for name in sorted(defines.keys(), key=len, reverse=True):
        value = defines[name]
        code = re.sub(r'\b' + re.escape(name) + r'\b', value, code)
    return code

def process_logic_directives(code):
    exports = re.findall(r'#export\s+([A-Za-z_][A-Za-z0-9_]*)', code)

    levels = {"#info": "[Info]", "#debug": "[Debug]", "#warn": "[Warning]"}
    for prefix, tag in levels.items():
        messages = re.findall(rf'{prefix}\s+"([^"]+)"', code)
        for msg in messages:
            print(f"{tag} {msg}")

    errors = re.findall(r'#error\s+"([^"]+)"', code)
    if errors:
        raise CompilerError(f"[FATAL] #error: {errors[0]}")

    clean_code = re.sub(r'#(export|info|debug|warn|error)\s+.*', '', code)
    
    return clean_code, exports

def preprocess(main_file):
    code = get_combined_source(main_file)
    code, defines = handle_conditionals_and_defines(code)
    code = apply_defines(code, defines)
    final_source, export_list = process_logic_directives(code)
    
    return final_source, export_list

def tokenize(code):
    tokens = []
    line_num = 1
    last_pos = 0

    tok_regex = '|'.join('(?P<%s>%s)' % pair for pair in TOKEN_SPEC)
    for mo in re.finditer(tok_regex, code):
        kind = mo.lastgroup
        value = mo.group()
        start_pos = mo.start()

        if start_pos > last_pos:
            skipped = code[last_pos:start_pos]
            if skipped.strip():
                bad_char = skipped.strip()[0]
                raise CompilerError(f"Illegal character: '{bad_char}'", line=line_num)

        if kind == 'WHITESPACE':
            line_num += value.count('\n')
        else:
            tokens.append((kind, value, line_num))
        
        last_pos = mo.end()

    if last_pos < len(code):
        remaining = code[last_pos:].strip()
        if remaining:
            raise CompilerError(f"Illegal character at end: '{remaining[0]}'", line=line_num)

    return tokens

class RegisterManager:
    def __init__(self):
        self.available_regs = [f"r{i}" for i in range(14)]
        self.cache = {}
        self.usage_map = {reg: False for reg in self.available_regs}

    def get_reg_with_value(self, value):
        for reg, val in self.cache.items():
            if val == value:
                return reg
        return None

    def allocate(self, value=None):
        for reg in self.available_regs:
            if not self.usage_map[reg]:
                self.usage_map[reg] = True
                if reg in self.cache:
                    del self.cache[reg]

                if value is not None and isinstance(value, int):
                    self.cache[reg] = value
                return reg
        raise CompilerError("Out of registers.")

    def free(self, reg):
        if reg in self.usage_map:
            self.usage_map[reg] = False

class Parser:
    def __init__(self, tokens, full_source, external_symbols=None):
        self.tokens = tokens
        self.pos = 0
        self.source_lines = full_source.split('\n')
        self.external_symbols = external_symbols if external_symbols else {}
        self.defined_globals = set()
        self.nesting_level = 0

    def get_source_comment(self, line_num):
        if line_num and line_num <= len(self.source_lines):
            return f"; {self.source_lines[line_num-1].strip()}"
        return "; (source unknown)"

    def error(self, message):
        token = self.peek_token()
        if token:
            raise CompilerError(message, line=token[2], token=token[1])
        last_line = self.tokens[-1][2] if self.tokens else None
        raise CompilerError(message, line=last_line)

    def peek_token(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def eat(self, expected_type=None):
        token = self.peek_token()
        if not token: self.error("Unexpected ending. Perhaps a bracket is missing.")
        if expected_type and token[0] != expected_type:
            self.error(f"Expected {expected_type}, got {token[0]}.")
        self.pos += 1
        return token

    def parse_factor(self, size=None, is_float=False):
        current_size = size
        current_is_float = is_float
        t = self.peek_token()
        if not t: return None

        if t[0] == 'STRING':
            val = self.eat('STRING')[1]
            val = val.strip('"').replace('\\n', '\n').replace('\\r', '\r').replace('\\t', '\t')
            return StringNode(val)

        if t[0] == 'TYPE':
            type_str = self.eat('TYPE')[1]
            if type_str == 'uint8':
                current_size = 8
                current_is_float = False
            elif type_str == 'uint16':
                current_size = 16
                current_is_float = False
            elif type_str == 'float32':
                current_size = 32
                current_is_float = True
            else:
                current_size = 32
                current_is_float = False
            t = self.peek_token()

        if t[0] == 'LPAREN':
            self.eat('LPAREN')
            node = self.parse_expression()
            self.eat('RPAREN')
            return node

        if t[0] == 'CHAR':
            val = ord(self.eat('CHAR')[1][1])
            return NumberNode(val, size=8)
        elif t[0] == 'DEREF':
            if current_size is None:
                self.error("Explicit type required before dereference.")
            self.eat('DEREF')
            addr = self.parse_factor(size=32) 
            return DerefNode(addr, size=current_size)
        elif t[0] == 'NUMBER':
            val_str = self.eat('NUMBER')[1]
            if current_size is None: current_size = 32
            if '.' in val_str or current_is_float:
                try:
                    val_float = float(val_str)
                    return NumberNode(val_float, size=32, is_float=True)
                except:
                    self.error(f"Invalid float: {val_str}")
            else:
                try:
                    val_int = int(val_str, 0)
                except:
                    val_int = 0
                return NumberNode(val_int, size=current_size, is_float=False)

        if t[0] == 'NAME':
            name = self.eat('NAME')[1]
            if self.peek_token() and self.peek_token()[0] == 'LPAREN':
                self.eat('LPAREN')
                args = []
                if self.peek_token() and self.peek_token()[0] != 'RPAREN':
                    args.append(self.parse_expression())
                    while self.peek_token() and self.peek_token()[0] == 'COMMA':
                        self.eat('COMMA')
                        args.append(self.parse_expression())
                self.eat('RPAREN')
                return CallNode(name, args)

            node = NumberNode(name, size=32)

            if self.peek_token() and self.peek_token()[0] == 'LBRACK':
                while self.peek_token() and self.peek_token()[0] == 'LBRACK':
                    self.eat('LBRACK')
                    index_expr = self.parse_expression()
                    self.eat('RBRACK')

                    multiplier = current_size // 8 if current_size else 4
                    if multiplier > 1:
                        index_expr = BinOpNode(index_expr, '*', NumberNode(multiplier, size=32))

                    node = BinOpNode(node, '+', index_expr)
                    node = DerefNode(node, size=current_size if current_size else 32)

            return node

        self.error(f"Unexpected '{t[1]}'")

    def parse_expression(self, size=None, is_float=False):
        node = self.parse_factor(size=size, is_float=is_float)
        while self.peek_token() and self.peek_token()[0] == 'OP':
            op = self.eat('OP')[1]
            right = self.parse_factor(size=size, is_float=is_float)
            op_is_float = is_float or getattr(node, 'is_float', False) or getattr(right, 'is_float', False)
            node = BinOpNode(node, op, right, is_float=op_is_float)
        return node

    def parse_statement(self):
        t = self.peek_token()
        if t is None: return None

        current_line_text = self.get_source_comment(t[2])

        if t[0] == 'DEF':
            if self.nesting_level > 0:
                self.error("Can't define global variables inside nested blocks.")

            self.eat('DEF')
            type_token = self.eat('TYPE')
            is_float = (type_token[1] == 'float32')
            if type_token[1] == 'uint8': size = 8
            elif type_token[1] == 'uint16': size = 16
            else: size = 32

            var_name = self.eat('NAME')[1]

            explicit_array_size = None
            if self.peek_token() and self.peek_token()[0] == 'LBRACK':
                self.eat('LBRACK')
                explicit_array_size = int(self.eat('NUMBER')[1], 0)
                self.eat('RBRACK')

            if var_name in self.defined_globals:
                self.error(f"Variable '{var_name}' already exists.")

            self.defined_globals.add(var_name)

            val_node = None
            next_t = self.peek_token()

            if next_t and next_t[0] == 'ASSIGN':
                self.eat('ASSIGN')
                if self.peek_token() and self.peek_token()[0] == 'LBRACE':
                    self.eat('LBRACE')
                    elements = []
                    if self.peek_token() and self.peek_token()[0] != 'RBRACE':
                        elements.append(self.parse_expression(size=size, is_float=is_float))
                        while self.peek_token() and self.peek_token()[0] == 'COMMA':
                            self.eat('COMMA')
                            elements.append(self.parse_expression(size=size, is_float=is_float))
                    self.eat('RBRACE')

                    if explicit_array_size is not None:
                        while len(elements) < explicit_array_size:
                            elements.append(NumberNode(0.0 if is_float else 0, size=size, is_float=is_float))
                    
                    val_node = ArrayNode(elements, size=size, source_line=current_line_text)
                else:
                    val_node = self.parse_expression(size=size, is_float=is_float)

            elif explicit_array_size is not None:
                elements = [NumberNode(0.0 if is_float else 0, size=size, is_float=is_float) for _ in range(explicit_array_size)]
                val_node = ArrayNode(elements, size=size, source_line=current_line_text)

            else:
                val_node = NumberNode(0.0 if is_float else 0, size=size, is_float=is_float, source_line=current_line_text)

            self.eat('SEMICOLON')

            total_bits = size
            if isinstance(val_node, ArrayNode):
                total_bits = len(val_node.elements) * size

            return GlobalVarNode(var_name, total_bits, val_node, source_line=current_line_text)

        if t[0] == 'ASM':
            self.eat('ASM')
            self.eat('LBRACE')
            asm_content = ""
            while self.peek_token() and self.peek_token()[0] != 'RBRACE':
                token_type, token_value, _ = self.eat()
                
                if token_type == 'SEMICOLON':
                    asm_content += "\n"
                elif token_type == 'LABEL':
                    asm_content += token_value.strip() + "\n"
                else:
                    asm_content += token_value + " "
            
            self.eat('RBRACE')
            return InlineAsmNode(asm_content, source_line=current_line_text)

        if t[0] == 'FN':
            fn_token = self.eat('FN')
            start_line = fn_token[2]
            name = self.eat('NAME')[1]
            self.eat('LPAREN')
            params = []
            if self.peek_token()[0] != 'RPAREN':
                param_token = self.peek_token()
                if param_token[0] == 'NAME' or param_token[0] == 'NUMBER':
                    params.append(self.eat()[1])
                while self.peek_token()[0] == 'COMMA':
                    self.eat('COMMA')
                    next_param = self.peek_token()
                    if next_param[0] in ['NAME', 'NUMBER']:
                        params.append(self.eat()[1])
                    else:
                        self.error("Expected parameter name or number")
            self.eat('RPAREN')
            self.eat('LBRACE')
            self.nesting_level += 1

            block = []
            while self.peek_token() and self.peek_token()[0] != 'RBRACE':
                block.append(self.parse_statement())
            
            if not self.peek_token() or self.peek_token()[0] != 'RBRACE':
                raise CompilerError(f"Unclosed function '{name}'. Started in line {start_line}", line=start_line)

            self.eat('RBRACE')
            self.nesting_level -= 1

            def check_for_return(stmts):
                for s in stmts:
                    if isinstance(s, ReturnNode): return True
                    if isinstance(s, IfNode):
                        if check_for_return(s.block): return True
                        if s.else_block and check_for_return(s.else_block): return True
                return False

            if not check_for_return(block): self.error(f"Missing return at function '{name}'.")

            return FunctionDefNode(name, params, block, source_line=current_line_text)

        if t[0] == 'RETURN':
            self.eat('RETURN')
            value_node = None
            if self.peek_token() and self.peek_token()[0] != 'SEMICOLON':
                value_node = self.parse_expression()
            self.eat('SEMICOLON')
            return ReturnNode(value_node, source_line=current_line_text)

        if t[0] == 'NAME':
            next_t = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
            if next_t and next_t[0] == 'LPAREN':
                name = self.eat('NAME')[1]
                self.eat('LPAREN')
                args = []
                if self.peek_token() and self.peek_token()[0] != 'RPAREN':
                    args.append(self.parse_expression())
                    while self.peek_token() and self.peek_token()[0] == 'COMMA':
                        self.eat('COMMA')
                        args.append(self.parse_expression())
                self.eat('RPAREN')
                self.eat('SEMICOLON')
                return CallNode(name, args, source_line=current_line_text)
            return NumberNode(name, size=current_size if current_size else 32)

        if t[0] == 'LABEL': 
            return LabelNode(self.eat('LABEL')[1], source_line=current_line_text)
        
        if t[0] == 'DIRECTIVE':
            node = self.parse_directive()
            node.source_line = current_line_text
            return node

        if t[0] == 'GOTO':
            node = self.parse_goto()
            node.source_line = current_line_text
            return node

        if t[0] == 'IF':
            node = self.parse_if()
            node.source_line = current_line_text
            return node

        if t[0] == 'WHILE':
            node = self.parse_while()
            node.source_line = current_line_text
            return node

        if t[0] == 'OUT':
            self.eat('OUT')
            port = self.parse_expression()
            self.eat('COMMA')
            data = self.parse_expression()
            self.eat('SEMICOLON')
            return OutNode(port, data, source_line=current_line_text)

        if t[0] == 'TYPE':
            type_token = self.eat('TYPE')
            is_float = (type_token[1] == 'float32')
            if type_token[1] == 'uint8': current_size = 8
            elif type_token[1] == 'uint16': current_size = 16
            else: current_size = 32

            t = self.peek_token()
            if t and t[0] in ['NUMBER', 'DEREF', 'NAME']:
                node = self.parse_assignment(current_size, is_float=is_float)
                self.eat('SEMICOLON')
                return node
            else:
                self.error(f"Expected assignment after type '{type_token[1]}'")

        if t[0] in ['NUMBER', 'DEREF']:
            self.error(f"Explicit type required for assignment at '{t[1]}'")

        if t[0] == 'NAME':
            self.error(f"Explicit type required before variable/address '{t[1]}'")
        
        self.error(f"Syntax error at {t}")

    def parse_assignment(self, size, is_float=False):
        target = self.parse_factor(size=size, is_float=is_float) 
        if isinstance(target, DerefNode):
            target.size = size

        self.eat('ASSIGN')
        value = self.parse_expression(size=size, is_float=is_float)
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
        if_token = self.eat('IF')
        start_line = if_token[2]
        
        left = self.parse_expression()
        op = self.eat()[1]
        right = self.parse_expression()

        is_float = getattr(left, 'is_float', False) or getattr(right, 'is_float', False)
        
        self.eat('LBRACE')
        self.nesting_level += 1
        block = []
        while self.peek_token() and self.peek_token()[0] != 'RBRACE':
            block.append(self.parse_statement())
        self.eat('RBRACE')
        self.nesting_level -= 1

        else_block = None
        if self.peek_token() and self.peek_token()[0] == 'ELSE':
            self.eat('ELSE')
            self.eat('LBRACE')
            self.nesting_level += 1
            else_block = []
            while self.peek_token() and self.peek_token()[0] != 'RBRACE':
                else_block.append(self.parse_statement())
            self.eat('RBRACE')
            self.nesting_level -= 1
            
        node = IfNode(left, op, right, block, else_block)
        node.is_float = is_float
        return node

    def parse_while(self):
        while_token = self.eat('WHILE')
        start_line = while_token[2]
        
        left = self.parse_expression()
        op = self.eat()[1]
        right = self.parse_expression()

        is_float = getattr(left, 'is_float', False) or getattr(right, 'is_float', False)

        self.eat('LBRACE')
        self.nesting_level += 1
        block = []
        while self.peek_token() and self.peek_token()[0] != 'RBRACE':
            block.append(self.parse_statement())
        self.eat('RBRACE')
        self.nesting_level -= 1
            
        node = WhileNode(left, op, right, block)
        node.is_float = is_float
        return node

    def parse_program(self):
        stmts = []
        while self.peek_token(): stmts.append(self.parse_statement())
        return stmts

def float_to_hex(f):
    return hex(struct.unpack('<I', struct.pack('<f', f))[0])

if_label_count = 0
call_label_count = 0

def generate_asm(statements, is_sub_block=False, rm=None, strings_to_embed=None, external_symbols=None, global_vars=None):
    global if_label_count, call_label_count
    if rm is None: rm = RegisterManager()
    if strings_to_embed is None: strings_to_embed = []
    if external_symbols is None: external_symbols = {}
    if global_vars is None: global_vars = []
    asm = []
    functions_asm = []

    if not is_sub_block:
        asm.append(f".bits 32")
        found_org = False
        for s in statements:
            if isinstance(s, DirectiveNode) and s.name == "#org":
                asm.append(f".org {hex(s.value)}")
                found_org = True
        if not found_org: raise CompilerError("Missing #org directive.")

    for stmt in statements:
        if hasattr(stmt, 'source_line') and stmt.source_line:
            asm.append(f"\n{stmt.source_line}")

        if isinstance(stmt, GlobalVarNode):
            if not isinstance(stmt.value, (NumberNode, StringNode, ArrayNode)):
                raise CompilerError("Global variables must be initialized with constants, strings or arrays.")
            global_vars.append(stmt)
            continue

        if isinstance(stmt, FunctionDefNode):
            f_asm = [f"{stmt.name}:"]

            if stmt.params:
                val_reg = rm.allocate()
                addr_reg = rm.allocate()
                ra_reg = rm.allocate()

                f_asm.append(f"pop {ra_reg}")

                for param_name in reversed(stmt.params):
                    f_asm.append(f"pop {val_reg}")
                    f_asm.append(f"mov {addr_reg}, {param_name}")
                    f_asm.append(f"mov.d [{addr_reg}], {val_reg}")

                f_asm.append(f"push {ra_reg}")

                rm.free(val_reg)
                rm.free(addr_reg)
                rm.free(ra_reg)

            body_asm = generate_asm(stmt.block, is_sub_block=True, rm=rm, 
                                   strings_to_embed=strings_to_embed, 
                                   external_symbols=external_symbols,
                                   global_vars=global_vars)
            f_asm.append(body_asm)
            if not f_asm[-1].strip().endswith("ret"):
                f_asm.append("ret")

            functions_asm.append("\n".join(f_asm))
            rm.usage_map = {reg: False for reg in rm.available_regs}
            rm.cache.clear()

        elif isinstance(stmt, ReturnNode):
            if stmt.value:
                val_asm, val_reg = generate_expression_asm(stmt.value, rm, external_symbols, strings_to_embed=strings_to_embed, global_vars=global_vars)
                if val_asm: 
                    asm.append(val_asm)

                asm.append(f"mov r0, {val_reg}")
                rm.free(val_reg)

            asm.append("ret")

        elif isinstance(stmt, CallNode):
            call_asm, res_reg = generate_expression_asm(stmt, rm, external_symbols, is_statement=True, strings_to_embed=strings_to_embed, global_vars=global_vars)
            asm.append(call_asm)
            if res_reg: rm.free(res_reg)

        elif isinstance(stmt, LabelNode):
            asm.append(f"{stmt.name}:")

        elif isinstance(stmt, DirectiveNode):
            continue

        elif isinstance(stmt, InlineAsmNode):
            formatted_asm = stmt.content.replace(' ; ', '\n').replace(';', '\n')
            asm.append(formatted_asm)
            rm.usage_map = {reg: False for reg in rm.available_regs}
            rm.cache.clear()

        elif isinstance(stmt, AssignNode):
            suffix = ".b" if stmt.size == 8 else (".w" if stmt.size == 16 else ".d")

            if isinstance(stmt.value, StringNode):
                str_label = f"str_const_{len(strings_to_embed)}"
                strings_to_embed.append((str_label, stmt.value.value))
                val_reg = rm.allocate() 
                asm.append(f"mov {val_reg}, {str_label}")
            else:
                v_asm, val_reg = generate_expression_asm(stmt.value, rm, external_symbols, strings_to_embed=strings_to_embed, global_vars=global_vars)
                if v_asm: asm.append(v_asm)

            rm.usage_map[val_reg] = True

            if isinstance(stmt.target, DerefNode):
                addr_asm, addr_ptr_reg = generate_expression_asm(stmt.target.target, rm, external_symbols, strings_to_embed=strings_to_embed, global_vars=global_vars)
                if addr_asm: asm.append(addr_asm)

                asm.append(f"mov{suffix} [{addr_ptr_reg}], {val_reg}")
                rm.free(addr_ptr_reg)

            elif isinstance(stmt.target, NumberNode):
                target_val = hex(stmt.target.value) if isinstance(stmt.target.value, int) else stmt.target.value
                
                temp_addr_reg = rm.allocate()
                asm.append(f"mov {temp_addr_reg}, {target_val}")
                asm.append(f"mov{suffix} [{temp_addr_reg}], {val_reg}")
                rm.free(temp_addr_reg)

            else:
                symbol_name = stmt.target if isinstance(stmt.target, str) else stmt.target.name
                addr_reg = rm.allocate()
                asm.append(f"mov {addr_reg}, {symbol_name}")
                asm.append(f"mov{suffix} [{addr_reg}], {val_reg}")
                rm.free(addr_reg)

            rm.free(val_reg)

        elif isinstance(stmt, GotoNode):
            if isinstance(stmt.target, str):
                asm.append(f"jmp {stmt.target}")
            else:
                target_asm, target_reg = generate_expression_asm(stmt.target, rm, external_symbols, strings_to_embed=strings_to_embed, global_vars=global_vars)
                if target_asm: 
                    asm.append(target_asm)

                asm.append(f"jmp {target_reg}")
                rm.free(target_reg)

            rm.usage_map = {reg: False for reg in rm.available_regs}
            rm.cache.clear()

        elif isinstance(stmt, OutNode):
            p_asm, p_reg = generate_expression_asm(stmt.port, rm, external_symbols, strings_to_embed=strings_to_embed, global_vars=global_vars)
            if p_asm: asm.append(p_asm)

            rm.usage_map[p_reg] = True
            
            d_asm, d_reg = generate_expression_asm(stmt.data, rm, external_symbols, strings_to_embed=strings_to_embed, global_vars=global_vars)
            if d_asm: asm.append(d_asm)
            
            asm.append(f"out {p_reg}, {d_reg}")
            rm.free(p_reg)
            rm.free(d_reg)

        elif isinstance(stmt, IfNode):
            if_label_count += 1
            label_else = f"_else_{if_label_count}"
            label_end = f"_endif_{if_label_count}"

            jump_target = label_else if stmt.else_block else label_end

            l_asm, l_reg = generate_expression_asm(stmt.left, rm, external_symbols, strings_to_embed=strings_to_embed, global_vars=global_vars)
            if l_asm: asm.append(l_asm)
            rm.usage_map[l_reg] = True

            r_asm, r_reg = generate_expression_asm(stmt.right, rm, external_symbols, strings_to_embed=strings_to_embed, global_vars=global_vars)
            if r_asm: asm.append(r_asm)
            rm.usage_map[r_reg] = True

            if stmt.op == "==":
                asm.append(f"jne {l_reg}, {r_reg}, {jump_target}")
            elif stmt.op == "!=":
                asm.append(f"je {l_reg}, {r_reg}, {jump_target}")
            elif stmt.op == "<":
                asm.append(f"jge {l_reg}, {r_reg}, {jump_target}")
            elif stmt.op == ">":
                asm.append(f"jle {l_reg}, {r_reg}, {jump_target}")
            elif stmt.op == ">=":
                asm.append(f"jl {l_reg}, {r_reg}, {jump_target}")
            elif stmt.op == "<=":
                asm.append(f"jg {l_reg}, {r_reg}, {jump_target}")

            rm.free(l_reg)
            rm.free(r_reg)

            asm.append(generate_asm(stmt.block, is_sub_block=True, rm=rm, strings_to_embed=strings_to_embed, external_symbols=external_symbols))

            if stmt.else_block:
                asm.append(f"jmp {label_end}")

                asm.append(f"{label_else}:")
                asm.append(generate_asm(stmt.else_block, is_sub_block=True, rm=rm, strings_to_embed=strings_to_embed, external_symbols=external_symbols))

            asm.append(f"{label_end}:")

        elif isinstance(stmt, WhileNode):
            if_label_count += 1
            label_start = f"_while_start_{if_label_count}"
            label_end = f"_while_end_{if_label_count}"

            asm.append(f"{label_start}:")

            l_asm, l_reg = generate_expression_asm(stmt.left, rm, external_symbols, strings_to_embed=strings_to_embed, global_vars=global_vars)
            if l_asm: asm.append(l_asm)
            rm.usage_map[l_reg] = True

            r_asm, r_reg = generate_expression_asm(stmt.right, rm, external_symbols, strings_to_embed=strings_to_embed, global_vars=global_vars)
            if r_asm: asm.append(r_asm)
            rm.usage_map[r_reg] = True

            if stmt.op == "==":
                asm.append(f"jne {l_reg}, {r_reg}, {label_end}")
            elif stmt.op == "!=":
                asm.append(f"je {l_reg}, {r_reg}, {label_end}")
            elif stmt.op == "<":
                asm.append(f"jge {l_reg}, {r_reg}, {label_end}")
            elif stmt.op == ">":
                asm.append(f"jle {l_reg}, {r_reg}, {label_end}")
            elif stmt.op == ">=":
                asm.append(f"jl {l_reg}, {r_reg}, {label_end}")
            elif stmt.op == "<=":
                asm.append(f"jg {l_reg}, {r_reg}, {label_end}")

            rm.free(l_reg)
            rm.free(r_reg)

            asm.append(generate_asm(stmt.block, is_sub_block=True, rm=rm, strings_to_embed=strings_to_embed, external_symbols=external_symbols))

            asm.append(f"jmp {label_start}")

            asm.append(f"{label_end}:")

    if not is_sub_block:
        asm.append("\n; --- End of Main Program ---")
        asm.append("_program_halt:")
        asm.append("jmp _program_halt")
        asm.append("halt")

        if functions_asm:
            asm.append("\n; --- Functions Section ---")
            asm.extend(functions_asm)

        if global_vars:
            asm.append("\n; --- Global Variables Section ---")
            for var in global_vars:
                if isinstance(var.value, StringNode):
                    asm.append(f"{var.name}:")
                    chars = ", ".join([hex(ord(c)) for c in var.value.value])
                    asm.append(f".db {chars}, 0x00")
                
                elif isinstance(var.value, ArrayNode):
                    array_len = len(var.value.elements)
                    asm.append(f"{var.name}_len:")
                    asm.append(f".dw {hex(array_len)}")

                    asm.append(f"{var.name}:")
                    directive = ".db" if var.size == 8 else (".dw" if var.size == 16 else ".dd")
                    element_values = []
                    for el in var.value.elements:
                        val = hex(el.value) if isinstance(el.value, int) else el.value
                        element_values.append(str(val))

                    asm.append(f"{directive} {', '.join(element_values)}")
                
                else:
                    asm.append(f"{var.name}:")
                    cmd = ".db" if var.size == 8 else (".dw" if var.size == 16 else ".dd")

                    val = var.value.value
                    if getattr(var.value, 'is_float', False) and isinstance(val, float):
                        val_out = float_to_hex(val)
                    else:
                        val_out = hex(val) if isinstance(val, int) else val
                        
                    asm.append(f"{cmd} {val_out}")

        if strings_to_embed:
            asm.append("\n; --- String Data Section ---")
            for label, text in strings_to_embed:
                asm.append(f"{label}:")
                chars = ", ".join([hex(ord(c)) for c in text])
                asm.append(f".db {chars}, 0x00")
        
    return "\n".join(asm)

def generate_expression_asm(node, rm, external_symbols=None, is_statement=False, strings_to_embed=None, global_vars=None):
    global if_label_count, call_label_count
    if external_symbols is None: external_symbols = {}
    if strings_to_embed is None: strings_to_embed = []
    if global_vars is None: global_vars = []

    if isinstance(node, StringNode):
        raw_data_label = f"str_data_{len(strings_to_embed)}"
        strings_to_embed.append((raw_data_label, node.value))
        
        reg = rm.allocate()
        return f"mov {reg}, {raw_data_label}", reg

    if isinstance(node, CallNode):
        asm = ""

        for arg in node.args:
            arg_asm, arg_reg = generate_expression_asm(arg, rm, external_symbols, strings_to_embed=strings_to_embed, global_vars=global_vars)
            if arg_asm:
                asm += arg_asm + "\n"
            asm += f"push {arg_reg}\n"
            rm.free(arg_reg)

        target = node.name
        if target in external_symbols:
            target = hex(external_symbols[target])

        asm += f"call {target}\n"

        if is_statement:
            return asm, None
        else:
            res_reg = rm.allocate()
            asm += f"mov {res_reg}, r0"
            return asm, res_reg

    if isinstance(node, NumberNode):
        if getattr(node, 'is_float', False) and isinstance(node.value, float):
            val = float_to_hex(node.value)
        else:
            val = hex(node.value) if isinstance(node.value, int) else node.value

        if isinstance(node.value, int):
            existing_reg = rm.get_reg_with_value(node.value)
            if existing_reg:
                return "", existing_reg

        reg = rm.allocate(node.value)
        return f"mov {reg}, {val}", reg
    
    if isinstance(node, DerefNode):
        suffix = ".b" if node.size == 8 else (".w" if node.size == 16 else ".d")

        addr_asm, addr_reg = generate_expression_asm(node.target, rm, external_symbols, strings_to_embed=strings_to_embed, global_vars=global_vars)
        
        target_reg = rm.allocate()

        asm = f"{addr_asm}\nmov{suffix} {target_reg}, [{addr_reg}]"

        rm.free(addr_reg)
        
        return asm, target_reg

    if isinstance(node, BinOpNode):
        left_asm, left_reg = generate_expression_asm(node.left, rm, external_symbols, strings_to_embed=strings_to_embed, global_vars=global_vars)
        rm.usage_map[left_reg] = True

        right_asm, right_reg = generate_expression_asm(node.right, rm, external_symbols, strings_to_embed=strings_to_embed, global_vars=global_vars)
        rm.usage_map[right_reg] = True

        is_f = getattr(node, 'is_float', False)

        if is_f:
            op_map = {
                "+": "fadd",
                "-": "fsub",
                "*": "fmul",
                "/": "fdiv",
                "%": "fmod"
            }
        else:
            op_map = {
                "+": "add",
                "-": "sub",
                "*": "mul",
                "/": "div",
                "%": "mod",
                "&": "and",
                "|": "or",
                "^": "xor",
                "<<": "shl",
                ">>": "shr"
            }

        if node.op not in op_map:
            raise CompilerError(f"Operator '{node.op}' not available for float type number.")
        op_cmd = op_map[node.op]

        res_asm = ""
        if left_asm: res_asm += left_asm + "\n"
        if right_asm: res_asm += right_asm + "\n"
        res_asm += f"{op_cmd} {left_reg}, {right_reg}"

        rm.free(right_reg)

        if left_reg in rm.cache:
            del rm.cache[left_reg]
            
        return res_asm, left_reg

    if isinstance(node, str):
        var_size = 32
        for gvar in global_vars:
            if gvar.name == node:
                var_size = gvar.size
                break
        
        suffix = ".b" if var_size == 8 else (".w" if var_size == 16 else ".d")
        
        addr_reg = rm.allocate()
        val_reg = rm.allocate()

        asm = f"mov {addr_reg}, {node}\n"
        asm += f"mov{suffix} {val_reg}, [{addr_reg}]"
        
        rm.free(addr_reg)
        return asm, val_reg

    return "", None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python compiler.py <source.c> [flags]")
        print("Flags: -n, -info, -asm, -export <file>, -import <file>")
        sys.exit(1)

    input_file = sys.argv[1]
    flags = set(sys.argv[2:])

    try:

        external_symbols = {}
        if "-import" in flags:
            try:
                idx = sys.argv.index("-import")
                sym_file = sys.argv[idx + 1]
                import json
                with open(sym_file, "r") as f:
                    external_symbols = json.load(f)
                print(f"[Info] {len(external_symbols)} symbols imported.")
            except:
                raise CompilerError("[Error] Could not load symbol file.")

        source_code, export_list = preprocess(input_file)
        tokens = tokenize(source_code)
        parser = Parser(tokens, source_code, external_symbols)
        statements = parser.parse_program()

        target_sector = None
        reserved_sectors = 0
        
        for s in statements:
            if isinstance(s, DirectiveNode):
                if s.name == "#sector":
                    target_sector = s.value
                elif s.name == "#sectors":
                    reserved_sectors = s.value

        if target_sector is None:
            raise CompilerError("Missing or invalid '#sector' directive.")

        if reserved_sectors <= 0:
            raise CompilerError("Missing or invalid '#sectors' directive. Must be at least 1.")

        asm_code = generate_asm(statements, external_symbols=external_symbols)

        timestamp = datetime.datetime.now().strftime('%H%M%S')
        asm_file_name = f"temp_{timestamp}.asm"
        with open(asm_file_name, "w") as f:
            f.write(asm_code)

        bytecode, symbols = assemble(asm_file_name, external_symbols)

        if "-export" in flags:
            idx = sys.argv.index("-export")
            h_file = sys.argv[idx + 1]

            smart_symbols = {}
            for name in export_list:
                if name in symbols:
                    smart_symbols[name] = symbols[name]
                else:
                    raise CompilerError(f"Export-Label '{name}' was not found in source code.")
            
            import json
            with open(h_file, "w") as f:
                json.dump(smart_symbols, f)
            print(f"[Success] {len(smart_symbols)} symbols exported to {h_file}.")

        if "-asm" not in flags:
            os.remove(asm_file_name)

        actual_size = len(bytecode)
        needed_sectors = ((actual_size - 1) // 512 + 1) if actual_size > 0 else 1

        final_sector_count = max(needed_sectors, reserved_sectors)

        if reserved_sectors > 0 and needed_sectors > reserved_sectors:
            raise CompilerError(f"Program needs {needed_sectors} sectors, but only {reserved_sectors} are reserved in #sectors.")

        if "-n" in flags:
            print(f"[Info] Dry run: disk.bin was not modified.")
        else:
            target_size = final_sector_count * 512
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
                print(f"[Success] Wrote {actual_size} bytes to sector {target_sector} in {disk_path}.")
            except FileNotFoundError:
                raise CompilerError(f"disk.bin not found.")

        if "-info" in flags:
            usage = (actual_size / (final_sector_count * 512)) * 100
            print(f"[Stats] Size: {actual_size} bytes / Usage: {usage:.1f}% of allocated space.")

    except CompilerError as e:
        print(e)
        sys.exit(1)
    except Exception as e:
        print(f"\n[Fatal Error] {e}")
        sys.exit(1)