"""
JackCompiler - Driver script to run tokenization and parsing over Jack source code files.
"""

import sys
import os

from JackTokenizer import JackLexicalLexer
from CompilationEngine import SyntaxAnalyzer


def process_compilation(jack_file_path, destination_dir):
    """
    Compiles a single Jack source file into XML parse tree and VM bytecode.
    """
    base_file_name = os.path.splitext(os.path.basename(jack_file_path))[0]
    
    # Initialize and execute lexical analyzer
    lexer_instance = JackLexicalLexer(jack_file_path)
    extracted_tokens = lexer_instance.execute_tokenization(out_dir=destination_dir)

    # Initialize and execute syntax analyzer
    syntax_analyzer = SyntaxAnalyzer(extracted_tokens, base_file_name, out_dir=destination_dir)
    syntax_analyzer.parse_class()


def main():
    """
    Entry point for the Jack Compiler. Parses arguments and processes source files.
    """
    if len(sys.argv) != 2:
        sys.exit(1)

    argument_path = sys.argv[1].rstrip('/\\')
    
    # Locate directories
    source_dir_path = os.path.dirname(os.path.abspath(argument_path))
    output_dir_path = os.path.join(os.path.dirname(source_dir_path), 'out')

    os.makedirs(output_dir_path, exist_ok=True)
    process_compilation(argument_path, output_dir_path)


if __name__ == '__main__':
    main()
