import sys
import os
from vm_parser import Parser, C_ARITHMETIC, C_PUSH, C_POP, C_LABEL, C_GOTO, C_IF, C_FUNCTION, C_RETURN, C_CALL
from code_writer import CodeWriter

def main():
    if len(sys.argv) != 2:
        return

    input_path = sys.argv[1].rstrip('/\\')
    vm_files = []
    output_path = ""

    if os.path.isfile(input_path):
        vm_files = [input_path]
        output_path = input_path.replace(".vm", ".asm")
        is_directory = False
    elif os.path.isdir(input_path):
        vm_files = [os.path.join(input_path, f) for f in os.listdir(input_path) if f.endswith(".vm")]
        dir_name = os.path.basename(input_path)
        output_path = os.path.join(input_path, dir_name + ".asm")
        is_directory = True
    else:
        return
    
    writer = CodeWriter(output_path)

    if is_directory:
        writer.write_init()

    for vm_file in vm_files:
        writer.set_file_name(vm_file)
        parser = Parser(vm_file)

        while parser.has_more_commands():
            parser.advance()
            cmd_type = parser.command_type()

            if cmd_type == C_ARITHMETIC:
                writer.write_arithmetic(parser.arg1())
            elif cmd_type in (C_PUSH, C_POP):
                writer.write_push_pop(cmd_type, parser.arg1(), parser.arg2())
            elif cmd_type == C_LABEL:
                writer.write_label(parser.arg1())
            elif cmd_type == C_GOTO:
                writer.write_goto(parser.arg1())
            elif cmd_type == C_IF:
                writer.write_if(parser.arg1())
            elif cmd_type == C_FUNCTION:
                writer.write_function(parser.arg1(), parser.arg2())
            elif cmd_type == C_CALL:
                writer.write_call(parser.arg1(), parser.arg2())
            elif cmd_type == C_RETURN:
                writer.write_return()

    writer.close()

if __name__ == "__main__":
    main()
