import os
import datetime
import sys
import re
from assembler import assemble

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
    def __init__(self, left, op, right, block, else_block=None):
        self.left = left
        self.op = op
        self.right = right
        self.block = block
        self.else_block = else_block

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

class FunctionDefNode:
    def __init__(self, name, block):
        self.name = name
        self.block = block

class CallNode:
    def __init__(self, name, args=None):
        self.name = name
        self.args = args if args is not None else []

class ReturnNode:
    def __init__(self, value_node=None):
        self.value = value_node

class InlineAsmNode:
    def __init__(self, content):
        self.content = content
    def __repr__(self): return f"InlineAsm({self.content[:20]}...)"

TOKEN_SPEC = [
    ('ASM',       r'asm\b'),
    ('TYPE',       r'uint8\b|uint16\b'),
    ('DIRECTIVE', r'#[A-Za-z_]+'),
    ('NUMBER',    r'(0x[0-9A-Fa-f]+|\d+)'),
    ('IF',        r'if\b'),
    ('ELSE',       r'else\b'),
    ('EQ',        r'=='),
    ('NE',        r'!='),
    ('LT', r'<'),
    ('GT', r'>'),
    ('ASSIGN',    r'='),
    ('DEREF',     r'\$'),
    ('OP',        r'[+\-*/%]'),
    ('SEMICOLON', r';'),
    ('LBRACE',    r'\{'),
    ('RBRACE',    r'\}'),
    ('LPAREN',    r'\('),
    ('RPAREN',    r'\)'),
    ('GOTO',      r'goto'),
    ('OUT', r'out\b'),
    ('LOAD', r'load\b'),
    ('SAVE', r'save\b'),
    ('FN',      r'void\b'),
    ('RETURN',  r'return\b'),
    ('CHAR', r"'.'"),
    ('STRING',     r'"[^"]*"'),
    ('LABEL',     r'[A-Za-z_][A-Za-z0-9_]*:'),
    ('NAME',      r'[A-Za-z_][A-Za-z0-9_]*'),
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

def apply_defines(code):
    defines = {}
    found = re.findall(r'#define\s+([A-Za-z_][A-Za-z0-9_]*)\s+([^\s\n]+)', code)
    for name, value in found:
        defines[name] = value

    code = re.sub(r'#define\s+.*', '', code)

    for name in sorted(defines.keys(), key=len, reverse=True):
        value = defines[name]
        code = re.sub(r'\b' + name + r'\b', value, code)
    
    return code

def preprocess(main_file):
    full_raw_code = get_combined_source(main_file)
    final_source = apply_defines(full_raw_code)
    
    return final_source

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
                
                if value is not None:
                    self.cache[reg] = value
                return reg
        raise CompilerError("Out of registers.")

    def free(self, reg):
        if reg in self.usage_map:
            self.usage_map[reg] = False

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

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

    def parse_factor(self, size=16):
        current_size = size
        t = self.peek_token()
        if not t: return None

        if t[0] == 'STRING':
            val = self.eat('STRING')[1]
            val = val.strip('"').replace('\\n', '\n').replace('\\r', '\r').replace('\\t', '\t')
            return StringNode(val)

        if t[0] == 'TYPE':
            type_str = self.eat('TYPE')[1]
            current_size = 8 if type_str == 'uint8' else 16
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
            self.eat('DEREF')
            addr = self.parse_factor(size=16)
            return DerefNode(addr, size=current_size)
        elif t[0] == 'NUMBER':
            val_str = self.eat('NUMBER')[1]
            return NumberNode(val_str, size=current_size)
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
            return name

        self.error(f"Unexpected '{t[1]}'")

        self.error(f"Unexpected '{token[1]}'")

    def parse_expression(self):
        node = self.parse_factor()
        while self.peek_token() and self.peek_token()[0] == 'OP':
            op = self.eat('OP')[1]
            node = BinOpNode(node, op, self.parse_factor())
        return node

    def parse_statement(self):
        t = self.peek_token()
        if t is None: return None

        if t[0] == 'ASM':
            self.eat('ASM')
            self.eat('LBRACE')
            asm_content = ""
            while self.peek_token() and self.peek_token()[0] != 'RBRACE':
                token_type, token_value, _ = self.eat()
                if token_type == 'SEMICOLON':
                    asm_content += "\n"
                else:
                    asm_content += token_value + " "
            self.eat('RBRACE')
            return InlineAsmNode(asm_content)

        if t[0] == 'FN':
            fn_token = self.eat('FN')
            start_line = fn_token[2]
            name = self.eat('NAME')[1]
            self.eat('LPAREN')
            self.eat('RPAREN')
            self.eat('LBRACE')

            block = []
            while self.peek_token() and self.peek_token()[0] != 'RBRACE':
                block.append(self.parse_statement())
            
            if not self.peek_token() or self.peek_token()[0] != 'RBRACE':
                raise CompilerError(f"Unclosed function '{name}'. Started in line {start_line}", line=start_line)

            self.eat('RBRACE')

            def check_for_return(stmts):
                for s in stmts:
                    if isinstance(s, ReturnNode):
                        return True
                    if isinstance(s, IfNode):
                        if check_for_return(s.block):
                            return True
                        if s.else_block and check_for_return(s.else_block):
                            return True
                return False

            if not check_for_return(block): self.error(f"Missing return at function '{name}'.")

            return FunctionDefNode(name, block)

        if t[0] == 'RETURN':
            self.eat('RETURN')
            value_node = None
            if self.peek_token() and self.peek_token()[0] != 'SEMICOLON':
                value_node = self.parse_expression()
            
            self.eat('SEMICOLON')
            return ReturnNode(value_node)

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
                return CallNode(name, args)

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
        
        self.error(f"Syntax error at {t}")

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
        if_token = self.eat('IF')
        start_line = if_token[2]
        
        left = self.parse_expression()
        op = self.eat()[1]
        right = self.parse_expression()
        
        self.eat('LBRACE')
        block = []
        while self.peek_token() and self.peek_token()[0] != 'RBRACE':
            block.append(self.parse_statement())
        self.eat('RBRACE')

        else_block = None
        if self.peek_token() and self.peek_token()[0] == 'ELSE':
            self.eat('ELSE')
            self.eat('LBRACE')
            else_block = []
            while self.peek_token() and self.peek_token()[0] != 'RBRACE':
                else_block.append(self.parse_statement())
            self.eat('RBRACE')
            
        return IfNode(left, op, right, block, else_block)

    def parse_program(self):
        stmts = []
        while self.peek_token(): stmts.append(self.parse_statement())
        return stmts

if_label_count = 0
call_label_count = 0

def generate_asm(statements, is_sub_block=False, rm=None, strings_to_embed=None):
    global if_label_count, call_label_count
    if rm is None: rm = RegisterManager()
    if strings_to_embed is None: strings_to_embed = []
    asm = []
    functions_asm = []

    if not is_sub_block:
        found_org = False
        for s in statements:
            if isinstance(s, DirectiveNode) and s.name == "#org":
                asm.append(f".org {hex(s.value)}")
                found_org = True
        if not found_org: asm.append(".org 0x0400")

    for stmt in statements:
        if isinstance(stmt, FunctionDefNode):
            f_asm = []
            f_asm.append(f"{stmt.name}:")
            f_asm.append(generate_asm(stmt.block, is_sub_block=True, rm=rm, strings_to_embed=strings_to_embed))
            functions_asm.append("\n".join(f_asm))
            rm.cache.clear()

        elif isinstance(stmt, ReturnNode):
            if stmt.value:
                val_asm, val_reg = generate_expression_asm(stmt.value, rm)
                if val_asm: asm.append(val_asm)

                ra_reg = rm.allocate()
                asm.append(f"pop {ra_reg}")
                asm.append(f"push {val_reg}")
                asm.append(f"push {ra_reg}")
                
                rm.free(ra_reg)
                rm.free(val_reg)

            asm.append("pop r15")

        elif isinstance(stmt, CallNode):
            call_asm, res_reg = generate_expression_asm(stmt, rm)
            asm.append(call_asm)
            asm.append(f"pop {res_reg}") 
            rm.free(res_reg)

        elif isinstance(stmt, LabelNode):
            asm.append(f"{stmt.name}:")

        elif isinstance(stmt, DirectiveNode):
            continue

        elif isinstance(stmt, InlineAsmNode):
            asm.append("; --- Inline Assembly ---")
            formatted_asm = stmt.content.replace(' ; ', '\n').replace(';', '\n')
            asm.append(formatted_asm)
            asm.append("; -----------------------")
            rm.usage_map = {reg: False for reg in rm.available_regs}
            rm.cache.clear()

        elif isinstance(stmt, AssignNode):
            if isinstance(stmt.value, StringNode):
                str_label = f"str_const_{len(strings_to_embed)}"
                strings_to_embed.append((str_label, stmt.value.value))
                val_reg = rm.allocate() 
                asm.append(f"movi {val_reg}, {str_label}")
            else:
                v_asm, val_reg = generate_expression_asm(stmt.value, rm)
                if v_asm: asm.append(v_asm)

            rm.usage_map[val_reg] = True

            if isinstance(stmt.target, NumberNode):
                target_reg = rm.get_reg_with_value(stmt.target.value)
                if not target_reg:
                    target_reg = rm.allocate(stmt.target.value)
                    asm.append(f"movi {target_reg}, {hex(stmt.target.value)}")
            
            elif isinstance(stmt.target, DerefNode):
                addr_asm, addr_ptr_reg = generate_expression_asm(stmt.target.target, rm)
                if addr_asm: asm.append(addr_asm)
                
                target_reg = rm.allocate()
                m0_reg = rm.get_reg_with_value(0)
                if not m0_reg:
                    m0_reg = rm.allocate(0)
                    asm.append(f"movi {m0_reg}, 0")
                
                asm.append(f"peek {target_reg}, {addr_ptr_reg}, {m0_reg}")
                rm.free(addr_ptr_reg)

            rm.usage_map[target_reg] = True
            mode = 1 if stmt.size == 8 else 0
            mode_reg = rm.get_reg_with_value(mode)
            if not mode_reg:
                mode_reg = rm.allocate(mode)
                asm.append(f"movi {mode_reg}, {mode}")

            asm.append(f"poke {val_reg}, {target_reg}, {mode_reg}")
            rm.usage_map = {reg: False for reg in rm.available_regs}
            rm.cache.clear()

        elif isinstance(stmt, GotoNode):
            if isinstance(stmt.target, str):
                asm.append(f"movi r15, {stmt.target}")
            else:
                target_asm, target_reg = generate_expression_asm(stmt.target, rm)
                if target_asm: asm.append(target_asm)
                asm.append(f"mov r15, {target_reg}")
            rm.usage_map = {reg: False for reg in rm.available_regs}
            rm.cache.clear()

        elif isinstance(stmt, OutNode):
            p_asm, p_reg = generate_expression_asm(stmt.port, rm)
            if p_asm: asm.append(p_asm)

            rm.usage_map[p_reg] = True
            
            d_asm, d_reg = generate_expression_asm(stmt.data, rm)
            if d_asm: asm.append(d_asm)
            
            asm.append(f"out {p_reg}, {d_reg}")
            rm.usage_map = {reg: False for reg in rm.available_regs}
            rm.cache.clear()

        elif isinstance(stmt, (LoadNode, SaveNode)):
            s_asm, s_reg = generate_expression_asm(stmt.sector, rm)
            if s_asm: asm.append(s_asm)
            rm.usage_map[s_reg] = True

            a_asm, a_reg = generate_expression_asm(stmt.address, rm)
            if a_asm: asm.append(a_asm)
            rm.usage_map[a_reg] = True

            m_reg = rm.get_reg_with_value(0)
            if not m_reg:
                m_reg = rm.allocate(0)
                asm.append(f"movi {m_reg}, 0")
                
            cmd = "load" if isinstance(stmt, LoadNode) else "save"
            asm.append(f"{cmd} {s_reg}, {a_reg}, {m_reg}")
            rm.usage_map = {reg: False for reg in rm.available_regs}
            rm.cache.clear()

        elif isinstance(stmt, IfNode):
            if_label_count += 1
            label_else = f"_else_{if_label_count}"
            label_end = f"_endif_{if_label_count}"

            jump_target = label_else if stmt.else_block else label_end

            l_asm, l_reg = generate_expression_asm(stmt.left, rm)
            if l_asm: asm.append(l_asm)
            rm.usage_map[l_reg] = True

            r_asm, r_reg = generate_expression_asm(stmt.right, rm)
            if r_asm: asm.append(r_asm)
            rm.usage_map[r_reg] = True

            t_reg = rm.allocate()
            asm.append(f"movi {t_reg}, {jump_target}")

            if stmt.op == "==":
                asm.append(f"jne {l_reg}, {r_reg}, {t_reg}")
            elif stmt.op == "!=":
                asm.append(f"je {l_reg}, {r_reg}, {t_reg}")
            elif stmt.op == "<":
                asm.append(f"div {l_reg}, {r_reg}")
                zero_reg = rm.allocate(0)
                asm.append(f"movi {zero_reg}, 0")
                asm.append(f"jne {l_reg}, {zero_reg}, {t_reg}")
                rm.free(zero_reg)
            elif stmt.op == ">":
                asm.append(f"div {r_reg}, {l_reg}")
                zero_reg = rm.allocate(0)
                asm.append(f"movi {zero_reg}, 0")
                asm.append(f"jne {r_reg}, {zero_reg}, {t_reg}")
                rm.free(zero_reg)

            rm.free(l_reg)
            rm.free(r_reg)
            rm.free(t_reg)

            asm.append(generate_asm(stmt.block, is_sub_block=True, rm=rm, strings_to_embed=strings_to_embed))

            if stmt.else_block:
                skip_reg = rm.allocate()
                asm.append(f"movi {skip_reg}, {label_end}")
                asm.append(f"mov r15, {skip_reg}")
                rm.free(skip_reg)
                
                asm.append(f"{label_else}:")
                asm.append(generate_asm(stmt.else_block, is_sub_block=True, rm=rm, strings_to_embed=strings_to_embed))

            asm.append(f"{label_end}:")

            rm.usage_map = {reg: False for reg in rm.available_regs}
            rm.cache.clear()

    if not is_sub_block:
        asm.append("\n; --- End of Main Program ---")
        asm.append("movi r15, 0xFFFF")

        if functions_asm:
            asm.append("\n; --- Functions Section ---")
            asm.extend(functions_asm)

        if strings_to_embed:
            asm.append("\n; --- String Data Section ---")
            for label, text in strings_to_embed:
                asm.append(f"{label}:")
                chars = ", ".join([hex(ord(c)) for c in text])
                asm.append(f".db {chars}, 0x00")
        
    return "\n".join(asm)

def generate_expression_asm(node, rm):
    global call_label_count

    if isinstance(node, CallNode):
        global call_label_count
        call_label_count += 1
        asm = ""

        for arg in node.args:
            arg_asm, arg_reg = generate_expression_asm(arg, rm)
            asm += arg_asm + "\n"
            asm += f"push {arg_reg}\n"
            rm.free(arg_reg)

        ret_label = f"_ret_{call_label_count}_{node.name}"
        reg_ret = rm.allocate()
        asm += f"movi {reg_ret}, {ret_label}\n"
        asm += f"push {reg_ret}\n"
        rm.free(reg_ret)

        asm += f"movi r15, {node.name}\n"
        asm += f"{ret_label}:\n"

        res_reg = rm.allocate()
        asm += f"pop {res_reg}"
        
        return asm, res_reg

    if isinstance(node, NumberNode):
        val = hex(node.value)
        existing_reg = rm.get_reg_with_value(node.value)
        if existing_reg:
            return "", existing_reg

        reg = rm.allocate(node.value)
        return f"movi {reg}, {val}", reg
    
    if isinstance(node, DerefNode):
        mode = 1 if node.size == 8 else 0
        addr_asm, addr_reg = generate_expression_asm(node.target, rm)
        
        target_reg = rm.allocate()
        mode_reg = rm.get_reg_with_value(mode)
        mode_asm = ""
        if not mode_reg:
            mode_reg = rm.allocate(mode)
            mode_asm = f"movi {mode_reg}, {mode}\n"

        asm = f"{addr_asm}\n{mode_asm}peek {target_reg}, {addr_reg}, {mode_reg}"
        rm.free(addr_reg)
        return asm, target_reg

    if isinstance(node, BinOpNode):
        left_asm, left_reg = generate_expression_asm(node.left, rm)
        rm.usage_map[left_reg] = True 

        right_asm, right_reg = generate_expression_asm(node.right, rm)
        rm.usage_map[right_reg] = True 

        if node.op == "%":
            mod_instrs = []
            temp_a = rm.allocate()

            mod_instrs.append(f"mov {temp_a}, {left_reg}")
            mod_instrs.append(f"div {left_reg}, {right_reg}")
            mod_instrs.append(f"mul {left_reg}, {right_reg}")
            mod_instrs.append(f"sub {temp_a}, {left_reg}")
            mod_instrs.append(f"mov {left_reg}, {temp_a}")
            
            rm.free(temp_a)
            res_asm = f"{left_asm}\n{right_asm}\n" + "\n".join(mod_instrs)
        else:
            op_cmd = {"+": "add", "-": "sub", "*": "mul", "/": "div"}[node.op]
            res_asm = f"{left_asm}\n{right_asm}\n{op_cmd} {left_reg}, {right_reg}"

        rm.free(left_reg) 
        rm.free(right_reg)
        rm.usage_map[left_reg] = True
        
        if left_reg in rm.cache: del rm.cache[left_reg]
        return res_asm, left_reg

    return "", None

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python compiler.py <source.c> <sector>")
        sys.exit(1)

    input_file = sys.argv[1]
    target_sector = int(sys.argv[2])

    try:
        source_code = preprocess(input_file)

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
            print(f"[Warning] {input_file} needs {min_needed_sectors} sectors, but #sectors is only {max_sectors}.")

        target_size = final_sector_count * 512
        padded_bytecode = bytecode.ljust(target_size, b'\x00')

        with open("disk.bin", "r+b") as f:
            f.seek(target_sector * 512)
            f.write(padded_bytecode)
        print(f"[Success] Wrote {actual_size} Bytes to {input_file} in {final_sector_count} Sectors.")

    except CompilerError as e:
        print(e)
        sys.exit(1)
    except FileNotFoundError:
        print("[Error] disk.bin is missing.")
        sys.exit(1)
    except Exception as e:
        print(f"\n[Unknown Error] {e}")
        sys.exit(1)