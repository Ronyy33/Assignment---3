"""
JackTokenizer - Performs lexical analysis on a Jack source file,
stripping comments and extracting semantic tokens into an XML tree structure.
"""

import re
import os

JACK_LANGUAGE_KEYWORDS = {
    'class', 'constructor', 'function', 'method', 'field', 'static',
    'var', 'int', 'char', 'boolean', 'void', 'true', 'false', 'null',
    'this', 'let', 'do', 'if', 'else', 'while', 'return'
}

JACK_LANGUAGE_SYMBOLS = {
    '{', '}', '(', ')', '[', ']', '.', ',', ';',
    '+', '-', '*', '/', '&', '|', '<', '>', '=', '~'
}


def sanitize_xml_chars(raw_text):
    """
    Escapes special characters in text to make it XML safe.
    """
    escaped_text = raw_text.replace('&', '&amp;')
    escaped_text = escaped_text.replace('<', '&lt;')
    escaped_text = escaped_text.replace('>', '&gt;')
    escaped_text = escaped_text.replace('"', '&quot;')
    return escaped_text


class JackLexicalLexer:
    """
    Class responsible for loading a .jack file, removing comments/whitespaces,
    and classifying individual lexical tokens.
    """
    def __init__(self, target_filepath):
        self._source_file_path = target_filepath
        self._source_base_name = os.path.splitext(os.path.basename(target_filepath))[0]
        self._source_dir_path = os.path.dirname(target_filepath)
        
        with open(target_filepath, 'r') as file_handle:
            self._raw_source_content = file_handle.read()

    def _remove_code_comments(self, content_str):
        """
        Strips inline and multiline block comments while preserving string literals.
        """
        output_buffer = []
        char_idx = 0
        total_len = len(content_str)
        inside_string_lit = False

        while char_idx < total_len:
            curr_char = content_str[char_idx]

            # Detect double quotes bounding a string constant
            if curr_char == '"':
                inside_string_lit = not inside_string_lit
                output_buffer.append(curr_char)
                char_idx += 1
            elif inside_string_lit:
                output_buffer.append(curr_char)
                char_idx += 1
            # Check for block comments: /* or /**
            elif char_idx + 1 < total_len and curr_char == '/' and content_str[char_idx + 1] == '*':
                char_idx += 2
                while char_idx + 1 < total_len and not (content_str[char_idx] == '*' and content_str[char_idx + 1] == '/'):
                    char_idx += 1
                char_idx += 2  # skip closing */
            # Check for line comments: //
            elif char_idx + 1 < total_len and curr_char == '/' and content_str[char_idx + 1] == '/':
                char_idx += 2
                while char_idx < total_len and content_str[char_idx] != '\n':
                    char_idx += 1
            else:
                output_buffer.append(curr_char)
                char_idx += 1

        return ''.join(output_buffer)

    def _extract_tokens(self, cleaned_content):
        """
        Iterates over the cleaned source string to build classified token pairs.
        """
        token_list = []
        char_idx = 0
        total_len = len(cleaned_content)

        while char_idx < total_len:
            curr_char = cleaned_content[char_idx]

            # Skip standard formatting/whitespace characters
            if curr_char in ' \t\n\r':
                char_idx += 1
                continue

            # Check if it is a structural symbol
            if curr_char in JACK_LANGUAGE_SYMBOLS:
                token_list.append(('symbol', curr_char))
                char_idx += 1
                continue

            # Check if it is a numeric digit
            if curr_char.isdigit():
                scan_idx = char_idx
                while scan_idx < total_len and cleaned_content[scan_idx].isdigit():
                    scan_idx += 1
                token_list.append(('integerConstant', cleaned_content[char_idx:scan_idx]))
                char_idx = scan_idx
                continue

            # Check if it is a string constant literal
            if curr_char == '"':
                scan_idx = char_idx + 1
                while scan_idx < total_len and cleaned_content[scan_idx] != '"':
                    scan_idx += 1
                token_list.append(('stringConstant', cleaned_content[char_idx + 1:scan_idx]))
                char_idx = scan_idx + 1
                continue

            # Check if it is a keyword or general word identifier
            if curr_char.isalpha() or curr_char == '_':
                scan_idx = char_idx
                while scan_idx < total_len and (cleaned_content[scan_idx].isalnum() or cleaned_content[scan_idx] == '_'):
                    scan_idx += 1
                word_token = cleaned_content[char_idx:scan_idx]
                
                if word_token in JACK_LANGUAGE_KEYWORDS:
                    token_list.append(('keyword', word_token))
                else:
                    token_list.append(('identifier', word_token))
                char_idx = scan_idx
                continue

            # Advance past unhandled/invalid chars
            char_idx += 1

        return token_list

    def execute_tokenization(self, out_dir=None):
        """
        Orchestrates comment stripping, token extraction, and writing the XML token tree.
        """
        sanitized_code = self._remove_code_comments(self._raw_source_content)
        parsed_tokens = self._extract_tokens(sanitized_code)

        if out_dir is None:
            out_dir = self._source_dir_path
            
        xml_output_file = os.path.join(out_dir, self._source_base_name + 'T.xml')
        self._export_xml_tokens(parsed_tokens, xml_output_file)

        return parsed_tokens

    def _export_xml_tokens(self, tokens, output_xml_path):
        """
        Serializes the generated tokens into the required <tokens> XML file format.
        """
        xml_lines_buffer = ['<tokens>']
        for type_tag, value_content in tokens:
            escaped_val = sanitize_xml_chars(value_content)
            xml_lines_buffer.append(f'<{type_tag}> {escaped_val} </{type_tag}>')
        xml_lines_buffer.append('</tokens>')

        with open(output_xml_path, 'w') as xml_file:
            xml_file.write('\n'.join(xml_lines_buffer) + '\n')
