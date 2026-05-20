import os
from SymbolTable import SymbolTable, STATIC, FIELD, ARG, VAR
from VMWriter import VMWriter

# Operator
OP_COMMANDS = {
    '+': 'add',
    '-': 'sub',
    '=': 'eq',
    '>': 'gt',
    '<': 'lt',
    '&': 'and',
    '|': 'or',
}

# Unary operator
UNARY_OP_COMMANDS = {
    '-': 'neg',
    '~': 'not',
}

# XML escape
XML_ESCAPES = {
    '<': '&lt;',
    '>': '&gt;',
    '&': '&amp;',
    '"': '&quot;',
}


def xml_escape(text):
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('"', '&quot;')
    return text


class CompilationEngine:

    def __init__(self, tokens, class_name, out_dir='.'):
        self.tokens = tokens
        self.pos = 0
        self.class_name = class_name
        self.out_dir = out_dir

        # XML output
        self.xml_lines = []
        self.xml_indent = 0

        # Symbol table
        self.symbol_table = SymbolTable()

        # VM writer
        vm_path = os.path.join(out_dir, class_name + '.vm')
        self.vm_writer = VMWriter(vm_path)

        # Label counter
        self.label_counter = 0

        # Current subroutine type
        self.current_subroutine_type = ''
        self.current_subroutine_name = ''

    def _current_token(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return (None, None)

    def _peek_token(self):
        if self.pos + 1 < len(self.tokens):
            return self.tokens[self.pos + 1]
        return (None, None)

    def _advance(self):
        token = self.tokens[self.pos]
        self.pos += 1
        return token

    def _eat(self, expected_type=None, expected_value=None):
        token_type, token_value = self._current_token()

        if expected_type and token_type != expected_type:
            raise SyntaxError(
                f"Expected token type '{expected_type}' but got '{token_type}' "
                f"(value='{token_value}') at position {self.pos}"
            )
        if expected_value and token_value != expected_value:
            if isinstance(expected_value, (list, tuple, set)):
                if token_value not in expected_value:
                    raise SyntaxError(
                        f"Expected one of {expected_value} but got '{token_value}' "
                        f"at position {self.pos}"
                    )
            else:
                raise SyntaxError(
                    f"Expected '{expected_value}' but got '{token_value}' "
                    f"at position {self.pos}"
                )

        self._write_xml_terminal(token_type, token_value)
        self.pos += 1
        return token_type, token_value

    def _is_token(self, token_type=None, token_value=None):
        ct, cv = self._current_token()
        if token_type and ct != token_type:
            return False
        if token_value:
            if isinstance(token_value, (list, tuple, set)):
                return cv in token_value
            return cv == token_value
        return True

    def _write_xml_terminal(self, token_type, token_value):
        indent = '  ' * self.xml_indent
        escaped = xml_escape(token_value)
        self.xml_lines.append(f'{indent}<{token_type}> {escaped} </{token_type}>')

    def _xml_open(self, tag):
        indent = '  ' * self.xml_indent
        self.xml_lines.append(f'{indent}<{tag}>')
        self.xml_indent += 1

    def _xml_close(self, tag):
        self.xml_indent -= 1
        indent = '  ' * self.xml_indent
        self.xml_lines.append(f'{indent}</{tag}>')

    def _save_xml(self):
        xml_path = os.path.join(self.out_dir, self.class_name + '.xml')
        with open(xml_path, 'w') as f:
            f.write('\n'.join(self.xml_lines) + '\n')

    def _new_label(self, prefix):
        label = f'{prefix}{self.label_counter}'
        self.label_counter += 1
        return label

    def compile_class(self):
        self._xml_open('class')

        self._eat('keyword', 'class')
        _, class_name = self._eat('identifier')
        self.class_name = class_name
        self._eat('symbol', '{')

        # classVarDec*
        while self._is_token('keyword', ('static', 'field')):
            self.compile_class_var_dec()

        # subroutineDec*
        while self._is_token('keyword', ('constructor', 'function', 'method')):
            self.compile_subroutine_dec()

        self._eat('symbol', '}')

        self._xml_close('class')
        self._save_xml()
        self.vm_writer.close()

    def compile_class_var_dec(self):
        self._xml_open('classVarDec')

        _, kind_str = self._eat('keyword', ('static', 'field'))
        kind = STATIC if kind_str == 'static' else FIELD

        # type
        var_type = self._eat_type()

        # varName
        _, var_name = self._eat('identifier')
        self.symbol_table.define(var_name, var_type, kind)

        # (',' varName)*
        while self._is_token('symbol', ','):
            self._eat('symbol', ',')
            _, var_name = self._eat('identifier')
            self.symbol_table.define(var_name, var_type, kind)

        self._eat('symbol', ';')

        self._xml_close('classVarDec')

    def compile_subroutine_dec(self):
        self._xml_open('subroutineDec')

        # Reset symbol table
        self.symbol_table.start_subroutine()

        _, subroutine_type = self._eat('keyword', ('constructor', 'function', 'method'))
        self.current_subroutine_type = subroutine_type

        # this -> argument 0 for methods
        if subroutine_type == 'method':
            self.symbol_table.define('this', self.class_name, ARG)

        # return type
        self._eat_type()

        # subroutineName
        _, subroutine_name = self._eat('identifier')
        self.current_subroutine_name = subroutine_name

        self._eat('symbol', '(')
        self.compile_parameter_list()
        self._eat('symbol', ')')

        # subroutineBody
        self.compile_subroutine_body(subroutine_type, subroutine_name)

        self._xml_close('subroutineDec')

    def compile_parameter_list(self):
        self._xml_open('parameterList')

        if not self._is_token('symbol', ')'):
            # First parameter
            var_type = self._eat_type()
            _, var_name = self._eat('identifier')
            self.symbol_table.define(var_name, var_type, ARG)

            # (',' type varName)*
            while self._is_token('symbol', ','):
                self._eat('symbol', ',')
                var_type = self._eat_type()
                _, var_name = self._eat('identifier')
                self.symbol_table.define(var_name, var_type, ARG)

        self._xml_close('parameterList')

    def compile_subroutine_body(self, subroutine_type, subroutine_name):
        self._xml_open('subroutineBody')

        self._eat('symbol', '{')

        # varDec*
        while self._is_token('keyword', 'var'):
            self.compile_var_dec()

        n_locals = self.symbol_table.var_count(VAR)
        full_name = f'{self.class_name}.{subroutine_name}'
        self.vm_writer.write_function(full_name, n_locals)

        if subroutine_type == 'constructor':
            n_fields = self.symbol_table.var_count(FIELD)
            self.vm_writer.write_push('constant', n_fields)
            self.vm_writer.write_call('Memory.alloc', 1)
            self.vm_writer.write_pop('pointer', 0)

        elif subroutine_type == 'method':
            self.vm_writer.write_push('argument', 0)
            self.vm_writer.write_pop('pointer', 0)

        # statements
        self.compile_statements()

        self._eat('symbol', '}')

        self._xml_close('subroutineBody')

    def compile_var_dec(self):
        self._xml_open('varDec')

        self._eat('keyword', 'var')
        var_type = self._eat_type()

        _, var_name = self._eat('identifier')
        self.symbol_table.define(var_name, var_type, VAR)

        while self._is_token('symbol', ','):
            self._eat('symbol', ',')
            _, var_name = self._eat('identifier')
            self.symbol_table.define(var_name, var_type, VAR)

        self._eat('symbol', ';')

        self._xml_close('varDec')

    def _eat_type(self):
        ct, cv = self._current_token()
        if ct == 'keyword' and cv in ('int', 'char', 'boolean', 'void'):
            self._eat('keyword')
            return cv
        else:
            _, type_name = self._eat('identifier')
            return type_name

    def compile_statements(self):
        self._xml_open('statements')

        while self._is_token('keyword', ('let', 'if', 'while', 'do', 'return')):
            _, kw = self._current_token()
            if kw == 'let':
                self.compile_let()
            elif kw == 'if':
                self.compile_if()
            elif kw == 'while':
                self.compile_while()
            elif kw == 'do':
                self.compile_do()
            elif kw == 'return':
                self.compile_return()

        self._xml_close('statements')

    def compile_let(self):
        self._xml_open('letStatement')

        self._eat('keyword', 'let')
        _, var_name = self._eat('identifier')

        is_array = False
        # Array indexing: varName[expression]
        if self._is_token('symbol', '['):
            is_array = True
            self._eat('symbol', '[')

            # Push base address of array
            segment = self.symbol_table.kind_of(var_name)
            index = self.symbol_table.index_of(var_name)
            self.vm_writer.write_push(segment, index)

            # Compile index expression
            self.compile_expression()
            self._eat('symbol', ']')

            # arr + index
            self.vm_writer.write_arithmetic('add')

        self._eat('symbol', '=')
        self.compile_expression()
        self._eat('symbol', ';')

        if is_array:
            # a[i] = expr
            self.vm_writer.write_pop('temp', 0)
            self.vm_writer.write_pop('pointer', 1)
            self.vm_writer.write_push('temp', 0)
            self.vm_writer.write_pop('that', 0)
        else:
            segment = self.symbol_table.kind_of(var_name)
            index = self.symbol_table.index_of(var_name)
            self.vm_writer.write_pop(segment, index)

        self._xml_close('letStatement')

    def compile_if(self):
        self._xml_open('ifStatement')

        label_false = self._new_label('IF_FALSE')
        label_end = self._new_label('IF_END')

        self._eat('keyword', 'if')
        self._eat('symbol', '(')
        self.compile_expression()
        self._eat('symbol', ')')

        # if ~(condition) goto FALSE
        self.vm_writer.write_arithmetic('not')
        self.vm_writer.write_if(label_false)

        self._eat('symbol', '{')
        self.compile_statements()
        self._eat('symbol', '}')

        # Else clause
        if self._is_token('keyword', 'else'):
            self.vm_writer.write_goto(label_end)
            self.vm_writer.write_label(label_false)

            self._eat('keyword', 'else')
            self._eat('symbol', '{')
            self.compile_statements()
            self._eat('symbol', '}')

            self.vm_writer.write_label(label_end)
        else:
            self.vm_writer.write_label(label_false)

        self._xml_close('ifStatement')

    def compile_while(self):
        self._xml_open('whileStatement')

        label_loop = self._new_label('WHILE_EXP')
        label_end = self._new_label('WHILE_END')

        self.vm_writer.write_label(label_loop)

        self._eat('keyword', 'while')
        self._eat('symbol', '(')
        self.compile_expression()
        self._eat('symbol', ')')

        # if ~(condition) goto END
        self.vm_writer.write_arithmetic('not')
        self.vm_writer.write_if(label_end)

        self._eat('symbol', '{')
        self.compile_statements()
        self._eat('symbol', '}')

        self.vm_writer.write_goto(label_loop)
        self.vm_writer.write_label(label_end)

        self._xml_close('whileStatement')

    def compile_do(self):
        self._xml_open('doStatement')

        self._eat('keyword', 'do')

        self._compile_subroutine_call()

        self._eat('symbol', ';')

        # Discard the return value
        self.vm_writer.write_pop('temp', 0)

        self._xml_close('doStatement')

    def compile_return(self):
        self._xml_open('returnStatement')

        self._eat('keyword', 'return')

        if not self._is_token('symbol', ';'):
            self.compile_expression()
        else:
            # Void function: push 0 as dummy return value
            self.vm_writer.write_push('constant', 0)

        self._eat('symbol', ';')
        self.vm_writer.write_return()

        self._xml_close('returnStatement')

    def compile_expression(self):
        self._xml_open('expression')

        self.compile_term()

        # (op term)*
        while self._is_token('symbol', ('+', '-', '*', '/', '&', '|', '<', '>', '=')):
            _, op = self._eat('symbol')
            self.compile_term()

            if op == '*':
                self.vm_writer.write_call('Math.multiply', 2)
            elif op == '/':
                self.vm_writer.write_call('Math.divide', 2)
            else:
                self.vm_writer.write_arithmetic(OP_COMMANDS[op])

        self._xml_close('expression')

    def compile_term(self):
        self._xml_open('term')

        ct, cv = self._current_token()

        if ct == 'integerConstant':
            self._eat('integerConstant')
            self.vm_writer.write_push('constant', int(cv))

        elif ct == 'stringConstant':
            self._eat('stringConstant')

            self.vm_writer.write_push('constant', len(cv))
            self.vm_writer.write_call('String.new', 1)
            for ch in cv:
                self.vm_writer.write_push('constant', ord(ch))
                self.vm_writer.write_call('String.appendChar', 2)

        elif ct == 'keyword' and cv in ('true', 'false', 'null', 'this'):
            self._eat('keyword')
            if cv == 'true':
                self.vm_writer.write_push('constant', 0)
                self.vm_writer.write_arithmetic('not')
            elif cv in ('false', 'null'):
                self.vm_writer.write_push('constant', 0)
            elif cv == 'this':
                self.vm_writer.write_push('pointer', 0)

        elif ct == 'symbol' and cv == '(':
            # '(' expression ')'
            self._eat('symbol', '(')
            self.compile_expression()
            self._eat('symbol', ')')

        elif ct == 'symbol' and cv in ('-', '~'):
            # unaryOp term
            self._eat('symbol')
            self.compile_term()
            self.vm_writer.write_arithmetic(UNARY_OP_COMMANDS[cv])

        elif ct == 'identifier':
            next_type, next_val = self._peek_token()

            if next_val == '[':
                _, var_name = self._eat('identifier')
                self._eat('symbol', '[')

                segment = self.symbol_table.kind_of(var_name)
                index = self.symbol_table.index_of(var_name)
                self.vm_writer.write_push(segment, index)

                self.compile_expression()
                self._eat('symbol', ']')

                self.vm_writer.write_arithmetic('add')
                self.vm_writer.write_pop('pointer', 1)
                self.vm_writer.write_push('that', 0)

            elif next_val == '(' or next_val == '.':
                self._compile_subroutine_call()

            else:
                _, var_name = self._eat('identifier')
                segment = self.symbol_table.kind_of(var_name)
                index = self.symbol_table.index_of(var_name)
                self.vm_writer.write_push(segment, index)

        self._xml_close('term')

    def compile_expression_list(self):
        self._xml_open('expressionList')

        n_args = 0

        if not self._is_token('symbol', ')'):
            self.compile_expression()
            n_args = 1

            while self._is_token('symbol', ','):
                self._eat('symbol', ',')
                self.compile_expression()
                n_args += 1

        self._xml_close('expressionList')
        return n_args

    def _compile_subroutine_call(self):
        _, first_name = self._eat('identifier')

        if self._is_token('symbol', '.'):
            self._eat('symbol', '.')
            _, subroutine_name = self._eat('identifier')

            if self.symbol_table.contains(first_name):
                obj_type = self.symbol_table.type_of(first_name)
                segment = self.symbol_table.kind_of(first_name)
                index = self.symbol_table.index_of(first_name)
                self.vm_writer.write_push(segment, index)

                self._eat('symbol', '(')
                n_args = self.compile_expression_list()
                self._eat('symbol', ')')

                self.vm_writer.write_call(f'{obj_type}.{subroutine_name}', n_args + 1)
            else:
                self._eat('symbol', '(')
                n_args = self.compile_expression_list()
                self._eat('symbol', ')')

                self.vm_writer.write_call(f'{first_name}.{subroutine_name}', n_args)

        elif self._is_token('symbol', '('):
            self.vm_writer.write_push('pointer', 0)

            self._eat('symbol', '(')
            n_args = self.compile_expression_list()
            self._eat('symbol', ')')

            self.vm_writer.write_call(
                f'{self.class_name}.{first_name}', n_args + 1
            )
