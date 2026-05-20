import re
import os

# Jack language keywords
KEYWORDS = {
    'class', 'constructor', 'function', 'method', 'field', 'static',
    'var', 'int', 'char', 'boolean', 'void', 'true', 'false', 'null',
    'this', 'let', 'do', 'if', 'else', 'while', 'return'
}

# Jack language symbols
SYMBOLS = {'{', '}', '(', ')', '[', ']', '.', ',', ';',
           '+', '-', '*', '/', '&', '|', '<', '>', '=', '~'}

# XML escape map
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


class JackTokenizer:
    def __init__(self, filepath):
        self.filepath = filepath
        self.basename = os.path.splitext(os.path.basename(filepath))[0]
        self.dirpath = os.path.dirname(filepath)
        with open(filepath, 'r') as f:
            self.source = f.read()

    def _strip_comments(self, source):
        result = []
        i = 0
        n = len(source)
        in_string = False

        while i < n:
            # String literals
            if source[i] == '"' and not in_string:
                in_string = True
                result.append(source[i])
                i += 1
            elif source[i] == '"' and in_string:
                in_string = False
                result.append(source[i])
                i += 1
            elif in_string:
                result.append(source[i])
                i += 1
            # Block comment: /* ... */ or /** ... */
            elif i + 1 < n and source[i] == '/' and source[i + 1] == '*':
                i += 2
                while i + 1 < n and not (source[i] == '*' and source[i + 1] == '/'):
                    i += 1
                i += 2  # skip past */
            # Single-line comment: //
            elif i + 1 < n and source[i] == '/' and source[i + 1] == '/':
                i += 2
                while i < n and source[i] != '\n':
                    i += 1
            else:
                result.append(source[i])
                i += 1

        return ''.join(result)

    def _tokenize_source(self, clean_source):
        tokens = []
        i = 0
        n = len(clean_source)

        while i < n:
            c = clean_source[i]

            # Skip whitespace
            if c in ' \t\n\r':
                i += 1
                continue

            # Symbol
            if c in SYMBOLS:
                tokens.append(('symbol', c))
                i += 1
                continue

            # Integer constant
            if c.isdigit():
                j = i
                while j < n and clean_source[j].isdigit():
                    j += 1
                tokens.append(('integerConstant', clean_source[i:j]))
                i = j
                continue

            # String constant
            if c == '"':
                j = i + 1
                while j < n and clean_source[j] != '"':
                    j += 1
                tokens.append(('stringConstant', clean_source[i + 1:j]))
                i = j + 1  # skip closing quote
                continue

            # Keyword or identifier
            if c.isalpha() or c == '_':
                j = i
                while j < n and (clean_source[j].isalnum() or clean_source[j] == '_'):
                    j += 1
                word = clean_source[i:j]
                if word in KEYWORDS:
                    tokens.append(('keyword', word))
                else:
                    tokens.append(('identifier', word))
                i = j
                continue

            # Unknown character - skip
            i += 1

        return tokens

    def tokenize(self, out_dir=None):
        clean = self._strip_comments(self.source)
        tokens = self._tokenize_source(clean)

        if out_dir is None:
            out_dir = self.dirpath
        xml_path = os.path.join(out_dir, self.basename + 'T.xml')
        self._write_xml(tokens, xml_path)

        return tokens

    def _write_xml(self, tokens, xml_path):
        lines = ['<tokens>']
        for token_type, token_value in tokens:
            escaped = xml_escape(token_value)
            lines.append(f'<{token_type}> {escaped} </{token_type}>')
        lines.append('</tokens>')

        with open(xml_path, 'w') as f:
            f.write('\n'.join(lines) + '\n')
