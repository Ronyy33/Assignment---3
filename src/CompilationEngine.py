"""
CompilationEngine - Analyzes tokens produced by JackLexicalLexer,
validates syntax structure against the Jack grammar, builds an XML parse tree,
and outputs target stack VM bytecode commands.
"""

import os
from SymbolTable import LexicalScopeTable, SCOPE_STATIC, SCOPE_FIELD, SCOPE_ARG, SCOPE_VAR
from VMWriter import BytecodeWriter

BINARY_MATH_COMMANDS = {
    '+': 'add',
    '-': 'sub',
    '=': 'eq',
    '>': 'gt',
    '<': 'lt',
    '&': 'and',
    '|': 'or',
}

UNARY_MATH_COMMANDS = {
    '-': 'neg',
    '~': 'not',
}


def escape_xml_entities(raw_str):
    """
    Translates reserved characters into safe XML entity references.
    """
    escaped = raw_str.replace('&', '&amp;')
    escaped = escaped.replace('<', '&lt;')
    escaped = escaped.replace('>', '&gt;')
    escaped = escaped.replace('"', '&quot;')
    return escaped


class SyntaxAnalyzer:
    """
    Recursive-descent syntactic parser for the Jack language.
    Generates syntax tree XML and corresponding VM bytecode.
    """

    def __init__(self, token_list, base_class_name, out_dir='.'):
        self._tokens_stream = token_list
        self._current_index = 0
        self._current_class_name = base_class_name
        self._output_dir_path = out_dir

        # XML parsing logs
        self._xml_output_buffer = []
        self._xml_indentation_level = 0

        # Scope Table Manager
        self._scope_table = LexicalScopeTable()

        # Output Bytecode Writer
        bytecode_file_path = os.path.join(out_dir, base_class_name + '.vm')
        self._code_emitter = BytecodeWriter(bytecode_file_path)

        # Labels generator counter
        self._generated_label_counter = 0

        # Subroutine scopes trackers
        self._current_subroutine_type = ''
        self._current_subroutine_name = ''

    def _get_active_token(self):
        """Returns the current token without consuming it."""
        if self._current_index < len(self._tokens_stream):
            return self._tokens_stream[self._current_index]
        return None, None

    def _lookahead_next_token(self):
        """Peeks at the next token in the stream without advancing."""
        if self._current_index + 1 < len(self._tokens_stream):
            return self._tokens_stream[self._current_index + 1]
        return None, None

    def _consume_next(self):
        """Advances past the current token and returns it."""
        token = self._tokens_stream[self._current_index]
        self._current_index += 1
        return token

    def _require_token(self, expected_type=None, expected_value=None):
        """
        Consumes the current token, enforcing type/value validation rules.
        """
        tok_type, tok_val = self._get_active_token()

        if expected_type and tok_type != expected_type:
            raise SyntaxError(
                f"Validation Error: Expected '{expected_type}' but got '{tok_type}' "
                f"(value='{tok_val}') at token index {self._current_index}"
            )
        if expected_value:
            if isinstance(expected_value, (list, tuple, set)):
                if tok_val not in expected_value:
                    raise SyntaxError(
                        f"Validation Error: Expected value to be in {expected_value} "
                        f"but got '{tok_val}' at index {self._current_index}"
                    )
            elif tok_val != expected_value:
                raise SyntaxError(
                    f"Validation Error: Expected value '{expected_value}' but got '{tok_val}' "
                    f"at index {self._current_index}"
                )

        self._append_terminal_xml(tok_type, tok_val)
        self._current_index += 1
        return tok_type, tok_val

    def _matches_token(self, expected_type=None, expected_value=None):
        """
        Checks if the current token matches the given type/value constraints.
        """
        tok_type, tok_val = self._get_active_token()
        if expected_type and tok_type != expected_type:
            return False
        if expected_value:
            if isinstance(expected_value, (list, tuple, set)):
                return tok_val in expected_value
            return tok_val == expected_value
        return True

    def _append_terminal_xml(self, token_type, token_value):
        """Formats and logs a terminal node to the XML structure."""
        spacing = '  ' * self._xml_indentation_level
        escaped_value = escape_xml_entities(token_value)
        self._xml_output_buffer.append(f'{spacing}<{token_type}> {escaped_value} </{token_type}>')

    def _open_xml_element(self, element_tag):
        """Indents and logs a new non-terminal container element."""
        spacing = '  ' * self._xml_indentation_level
        self._xml_output_buffer.append(f'{spacing}<{element_tag}>')
        self._xml_indentation_level += 1

    def _close_xml_element(self, element_tag):
        """Outdents and closes a non-terminal container element."""
        self._xml_indentation_level -= 1
        spacing = '  ' * self._xml_indentation_level
        self._xml_output_buffer.append(f'{spacing}</{element_tag}>')

    def _write_xml_file(self):
        """Saves the buffered XML parser representation to disk."""
        target_path = os.path.join(self._output_dir_path, self._current_class_name + '.xml')
        with open(target_path, 'w') as file_stream:
            file_stream.write('\n'.join(self._xml_output_buffer) + '\n')

    def _create_unique_label(self, label_prefix):
        """Generates a unique assembly label for branch instructions."""
        new_label = f'{label_prefix}{self._generated_label_counter}'
        self._generated_label_counter += 1
        return new_label

    def parse_class(self):
        """Parses a full Jack class declaration."""
        self._open_xml_element('class')

        self._require_token('keyword', 'class')
        _, actual_class_name = self._require_token('identifier')
        self._current_class_name = actual_class_name
        self._require_token('symbol', '{')

        # Compile any static or field variable declarations
        while self._matches_token('keyword', ('static', 'field')):
            self.parse_class_var_declaration()

        # Compile constructors, methods, and functions
        while self._matches_token('keyword', ('constructor', 'function', 'method')):
            self.parse_subroutine_declaration()

        self._require_token('symbol', '}')

        self._close_xml_element('class')
        self._write_xml_file()
        self._code_emitter.close_writer()

    def parse_class_var_declaration(self):
        """Parses class variable declarations: static or field."""
        self._open_xml_element('classVarDec')

        _, variable_scope = self._require_token('keyword', ('static', 'field'))
        kind = SCOPE_STATIC if variable_scope == 'static' else SCOPE_FIELD

        # Parse type specifier
        data_type = self._require_data_type()

        # Parse first variable identifier name
        _, variable_name = self._require_token('identifier')
        self._scope_table.register_symbol(variable_name, data_type, kind)

        # Parse other variables declared in the same line
        while self._matches_token('symbol', ','):
            self._require_token('symbol', ',')
            _, variable_name = self._require_token('identifier')
            self._scope_table.register_symbol(variable_name, data_type, kind)

        self._require_token('symbol', ';')

        self._close_xml_element('classVarDec')

    def parse_subroutine_declaration(self):
        """Parses subroutine declarations: method, function, or constructor."""
        self._open_xml_element('subroutineDec')

        # Clean local/subroutine scope symbols
        self._scope_table.reset_subroutine_scope()

        _, subroutine_kind = self._require_token('keyword', ('constructor', 'function', 'method'))
        self._current_subroutine_type = subroutine_kind

        # Map 'this' pointer as first argument index 0 for instance methods
        if subroutine_kind == 'method':
            self._scope_table.register_symbol('this', self._current_class_name, SCOPE_ARG)

        # Parse return type
        self._require_data_type()

        # Parse subroutine identifier name
        _, subroutine_name = self._require_token('identifier')
        self._current_subroutine_name = subroutine_name

        self._require_token('symbol', '(')
        self.parse_parameter_list()
        self._require_token('symbol', ')')

        # Parse the remaining body blocks
        self.parse_subroutine_body(subroutine_kind, subroutine_name)

        self._close_xml_element('subroutineDec')

    def parse_parameter_list(self):
        """Parses list of formal subroutine arguments."""
        self._open_xml_element('parameterList')

        if not self._matches_token('symbol', ')'):
            # Compile first formal argument type & name
            arg_type = self._require_data_type()
            _, arg_name = self._require_token('identifier')
            self._scope_table.register_symbol(arg_name, arg_type, SCOPE_ARG)

            # Compile additional optional arguments
            while self._matches_token('symbol', ','):
                self._require_token('symbol', ',')
                arg_type = self._require_data_type()
                _, arg_name = self._require_token('identifier')
                self._scope_table.register_symbol(arg_name, arg_type, SCOPE_ARG)

        self._close_xml_element('parameterList')

    def parse_subroutine_body(self, subroutine_kind, subroutine_name):
        """Parses statements and local variables within a subroutine body."""
        self._open_xml_element('subroutineBody')

        self._require_token('symbol', '{')

        # Parse all local variable declarations (var)
        while self._matches_token('keyword', 'var'):
            self.parse_local_var_declaration()

        local_vars_count = self._scope_table.get_count_for_kind(SCOPE_VAR)
        fully_qualified_subroutine_name = f'{self._current_class_name}.{subroutine_name}'
        self._code_emitter.emit_function(fully_qualified_subroutine_name, local_vars_count)

        # Constructor setup: allocate space on heap using Memory.alloc
        if subroutine_kind == 'constructor':
            fields_count = self._scope_table.get_count_for_kind(SCOPE_FIELD)
            self._code_emitter.emit_push('constant', fields_count)
            self._code_emitter.emit_call('Memory.alloc', 1)
            self._code_emitter.emit_pop('pointer', 0)

        # Instance Method setup: assign 'this' pointer from standard argument index 0
        elif subroutine_kind == 'method':
            self._code_emitter.emit_push('argument', 0)
            self._code_emitter.emit_pop('pointer', 0)

        # Execute parser engine over code body statements
        self.parse_statement_group()

        self._require_token('symbol', '}')

        self._close_xml_element('subroutineBody')

    def parse_local_var_declaration(self):
        """Parses local variable declarations inside methods/functions."""
        self._open_xml_element('varDec')

        self._require_token('keyword', 'var')
        data_type = self._require_data_type()

        _, local_var_name = self._require_token('identifier')
        self._scope_table.register_symbol(local_var_name, data_type, SCOPE_VAR)

        while self._matches_token('symbol', ','):
            self._require_token('symbol', ',')
            _, local_var_name = self._require_token('identifier')
            self._scope_table.register_symbol(local_var_name, data_type, SCOPE_VAR)

        self._require_token('symbol', ';')

        self._close_xml_element('varDec')

    def _require_data_type(self):
        """Utility parser to match int, char, boolean, void or class names."""
        token_type, token_value = self._get_active_token()
        if token_type == 'keyword' and token_value in ('int', 'char', 'boolean', 'void'):
            self._require_token('keyword')
            return token_value
        else:
            _, identifier_type = self._require_token('identifier')
            return identifier_type

    def parse_statement_group(self):
        """Parses general blocks of code statements."""
        self._open_xml_element('statements')

        while self._matches_token('keyword', ('let', 'if', 'while', 'do', 'return')):
            _, keyword_val = self._get_active_token()
            if keyword_val == 'let':
                self.parse_let_statement()
            elif keyword_val == 'if':
                self.parse_if_statement()
            elif keyword_val == 'while':
                self.parse_while_statement()
            elif keyword_val == 'do':
                self.parse_do_statement()
            elif keyword_val == 'return':
                self.parse_return_statement()

        self._close_xml_element('statements')

    def parse_let_statement(self):
        """Parses standard variable assignation let statements."""
        self._open_xml_element('letStatement')

        self._require_token('keyword', 'let')
        _, target_var_name = self._require_token('identifier')

        is_array_assignment = False
        
        # Check if indexing an array: let name[expression] = ...
        if self._matches_token('symbol', '['):
            is_array_assignment = True
            self._require_token('symbol', '[')

            # Look up array base memory segment and offset index
            segment = self._scope_table.get_segment_of(target_var_name)
            index = self._scope_table.get_index_of(target_var_name)
            self._code_emitter.emit_push(segment, index)

            # Evaluate inner expression index
            self.parse_expression()
            self._require_token('symbol', ']')

            # Compute actual offset address
            self._code_emitter.emit_arithmetic('add')

        self._require_token('symbol', '=')
        self.parse_expression()
        self._require_token('symbol', ';')

        if is_array_assignment:
            # Pop value of expression to temp, set array index in THAT, and pop to THAT 0
            self._code_emitter.emit_pop('temp', 0)
            self._code_emitter.emit_pop('pointer', 1)
            self._code_emitter.emit_push('temp', 0)
            self._code_emitter.emit_pop('that', 0)
        else:
            segment = self._scope_table.get_segment_of(target_var_name)
            index = self._scope_table.get_index_of(target_var_name)
            self._code_emitter.emit_pop(segment, index)

        self._close_xml_element('letStatement')

    def parse_if_statement(self):
        """Parses branching blocks: if / else statements."""
        self._open_xml_element('ifStatement')

        label_if_false = self._create_unique_label('IF_FALSE')
        label_if_end = self._create_unique_label('IF_END')

        self._require_token('keyword', 'if')
        self._require_token('symbol', '(')
        self.parse_expression()
        self._require_token('symbol', ')')

        # Negate condition outcome and jump past true block if false
        self._code_emitter.emit_arithmetic('not')
        self._code_emitter.emit_if_goto(label_if_false)

        self._require_token('symbol', '{')
        self.parse_statement_group()
        self._require_token('symbol', '}')

        # Handle optional else block
        if self._matches_token('keyword', 'else'):
            self._code_emitter.emit_goto(label_if_end)
            self._code_emitter.emit_label(label_if_false)

            self._require_token('keyword', 'else')
            self._require_token('symbol', '{')
            self.parse_statement_group()
            self._require_token('symbol', '}')

            self._code_emitter.emit_label(label_if_end)
        else:
            self._code_emitter.emit_label(label_if_false)

        self._close_xml_element('ifStatement')

    def parse_while_statement(self):
        """Parses while statement loops."""
        self._open_xml_element('whileStatement')

        loop_label = self._create_unique_label('WHILE_EXP')
        end_label = self._create_unique_label('WHILE_END')

        self._code_emitter.emit_label(loop_label)

        self._require_token('keyword', 'while')
        self._require_token('symbol', '(')
        self.parse_expression()
        self._require_token('symbol', ')')

        # Check loop condition: exit if false
        self._code_emitter.emit_arithmetic('not')
        self._code_emitter.emit_if_goto(end_label)

        self._require_token('symbol', '{')
        self.parse_statement_group()
        self._require_token('symbol', '}')

        # Recheck loop condition
        self._code_emitter.emit_goto(loop_label)
        self._code_emitter.emit_label(end_label)

        self._close_xml_element('whileStatement')

    def parse_do_statement(self):
        """Parses do statement subroutine calls (ignores return values)."""
        self._open_xml_element('doStatement')

        self._require_token('keyword', 'do')
        self._parse_subroutine_call()
        self._require_token('symbol', ';')

        # Pop out dummy return value to preserve clean stack
        self._code_emitter.emit_pop('temp', 0)

        self._close_xml_element('doStatement')

    def parse_return_statement(self):
        """Parses return statements in functions/methods/constructors."""
        self._open_xml_element('returnStatement')

        self._require_token('keyword', 'return')

        if not self._matches_token('symbol', ';'):
            self.parse_expression()
        else:
            # Returns 0 as dummy value for void methods/functions
            self._code_emitter.emit_push('constant', 0)

        self._require_token('symbol', ';')
        self._code_emitter.emit_return()

        self._close_xml_element('returnStatement')

    def parse_expression(self):
        """Parses mathematical expression statements."""
        self._open_xml_element('expression')

        self.parse_term()

        # Parse continuous operator expressions (left to right evaluation)
        while self._matches_token('symbol', ('+', '-', '*', '/', '&', '|', '<', '>', '=')):
            _, math_operator = self._require_token('symbol')
            self.parse_term()

            # Compile non-primitive operators via OS Math class
            if math_operator == '*':
                self._code_emitter.emit_call('Math.multiply', 2)
            elif math_operator == '/':
                self._code_emitter.emit_call('Math.divide', 2)
            else:
                self._code_emitter.emit_arithmetic(BINARY_MATH_COMMANDS[math_operator])

        self._close_xml_element('expression')

    def parse_term(self):
        """Parses atomic expression terms: literals, identifiers, nested blocks."""
        self._open_xml_element('term')

        token_type, token_val = self._get_active_token()

        if token_type == 'integerConstant':
            self._require_token('integerConstant')
            self._code_emitter.emit_push('constant', int(token_val))

        elif token_type == 'stringConstant':
            self._require_token('stringConstant')
            # Build string characters one-by-one
            self._code_emitter.emit_push('constant', len(token_val))
            self._code_emitter.emit_call('String.new', 1)
            for character in token_val:
                self._code_emitter.emit_push('constant', ord(character))
                self._code_emitter.emit_call('String.appendChar', 2)

        elif token_type == 'keyword' and token_val in ('true', 'false', 'null', 'this'):
            self._require_token('keyword')
            if token_val == 'true':
                self._code_emitter.emit_push('constant', 0)
                self._code_emitter.emit_arithmetic('not')
            elif token_val in ('false', 'null'):
                self._code_emitter.emit_push('constant', 0)
            elif token_val == 'this':
                self._code_emitter.emit_push('pointer', 0)

        elif token_type == 'symbol' and token_val == '(':
            self._require_token('symbol', '(')
            self.parse_expression()
            self._require_token('symbol', ')')

        elif token_type == 'symbol' and token_val in ('-', '~'):
            self._require_token('symbol')
            self.parse_term()
            self._code_emitter.emit_arithmetic(UNARY_MATH_COMMANDS[token_val])

        elif token_type == 'identifier':
            _, subsequent_val = self._lookahead_next_token()

            # Array access
            if subsequent_val == '[':
                _, var_name = self._require_token('identifier')
                self._require_token('symbol', '[')

                segment = self._scope_table.get_segment_of(var_name)
                index = self._scope_table.get_index_of(var_name)
                self._code_emitter.emit_push(segment, index)

                self.parse_expression()
                self._require_token('symbol', ']')

                self._code_emitter.emit_arithmetic('add')
                self._code_emitter.emit_pop('pointer', 1)
                self._code_emitter.emit_push('that', 0)

            # Subroutine invocation
            elif subsequent_val in ('(', '.'):
                self._parse_subroutine_call()

            # Normal variable access
            else:
                _, var_name = self._require_token('identifier')
                segment = self._scope_table.get_segment_of(var_name)
                index = self._scope_table.get_index_of(var_name)
                self._code_emitter.emit_push(segment, index)

        self._close_xml_element('term')

    def parse_expression_list(self):
        """Parses parameter expressions in a subroutine call, returns total arguments count."""
        self._open_xml_element('expressionList')

        args_count = 0

        if not self._matches_token('symbol', ')'):
            self.parse_expression()
            args_count = 1

            while self._matches_token('symbol', ','):
                self._require_token('symbol', ',')
                self.parse_expression()
                args_count += 1

        self._close_xml_element('expressionList')
        return args_count

    def _parse_subroutine_call(self):
        """Internal helper to parse both local and external class/object method calls."""
        _, initial_identifier = self._require_token('identifier')

        if self._matches_token('symbol', '.'):
            self._require_token('symbol', '.')
            _, subroutine_name = self._require_token('identifier')

            # Check if identifier references an existing variable in scope (instance method call)
            if self._scope_table.has_symbol(initial_identifier):
                obj_type = self._scope_table.get_type_of(initial_identifier)
                segment = self._scope_table.get_segment_of(initial_identifier)
                index = self._scope_table.get_index_of(initial_identifier)
                self._code_emitter.emit_push(segment, index)

                self._require_token('symbol', '(')
                args_count = self.parse_expression_list()
                self._require_token('symbol', ')')

                self._code_emitter.emit_call(f'{obj_type}.{subroutine_name}', args_count + 1)
            # Static function / OS utility call
            else:
                self._require_token('symbol', '(')
                args_count = self.parse_expression_list()
                self._require_token('symbol', ')')

                self._code_emitter.emit_call(f'{initial_identifier}.{subroutine_name}', args_count)

        elif self._matches_token('symbol', '('):
            # Implicit local method call over 'this' pointer
            self._code_emitter.emit_push('pointer', 0)

            self._require_token('symbol', '(')
            args_count = self.parse_expression_list()
            self._require_token('symbol', ')')

            self._code_emitter.emit_call(
                f'{self._current_class_name}.{initial_identifier}', args_count + 1
            )
