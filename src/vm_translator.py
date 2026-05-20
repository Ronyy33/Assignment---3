"""
vm_translator - Main entry point orchestration driver for the stack VM to Hack ASM translator.
"""

import sys
import os
from vm_parser import (
    InstructionReader, CMD_ARITHMETIC, CMD_PUSH, CMD_POP, CMD_LABEL,
    CMD_GOTO, CMD_IF, CMD_FUNCTION, CMD_RETURN, CMD_CALL
)
from code_writer import AssemblyEmitter


def execute_translation():
    """
    Main driver running argument verification, setup, and parsing orchestrations.
    """
    if len(sys.argv) != 2:
        return

    arg_path = sys.argv[1].rstrip('/\\')
    files_to_translate = []
    output_asm_path = ""

    if os.path.isfile(arg_path):
        files_to_translate = [arg_path]
        output_asm_path = arg_path.replace(".vm", ".asm")
        is_dir_mode = False
    elif os.path.isdir(arg_path):
        files_to_translate = [os.path.join(arg_path, f) for f in os.listdir(arg_path) if f.endswith(".vm")]
        root_dir_name = os.path.basename(arg_path)
        output_asm_path = os.path.join(arg_path, root_dir_name + ".asm")
        is_dir_mode = True
    else:
        return
    
    # Initialize Assembly Emitter
    asm_emitter = AssemblyEmitter(output_asm_path)

    # Emit bootstrap runtime code if translating a directory
    if is_dir_mode:
        asm_emitter.emit_bootstrap_code()

    # Process each VM file sequentially
    for target_vm_file in files_to_translate:
        asm_emitter.update_active_file(target_vm_file)
        reader = InstructionReader(target_vm_file)

        # Loop through instructions
        while reader.has_remaining_commands():
            reader.next_command()
            command_type = reader.get_command_type()

            if command_type == CMD_ARITHMETIC:
                asm_emitter.emit_arithmetic_command(reader.get_first_arg())
            elif command_type in (CMD_PUSH, CMD_POP):
                asm_emitter.emit_push_pop_command(command_type, reader.get_first_arg(), reader.get_second_arg())
            elif command_type == CMD_LABEL:
                asm_emitter.emit_branch_label(reader.get_first_arg())
            elif command_type == CMD_GOTO:
                asm_emitter.emit_goto_command(reader.get_first_arg())
            elif command_type == CMD_IF:
                asm_emitter.emit_if_goto_command(reader.get_first_arg())
            elif command_type == CMD_FUNCTION:
                asm_emitter.emit_function_declaration(reader.get_first_arg(), reader.get_second_arg())
            elif command_type == CMD_CALL:
                asm_emitter.emit_function_call(reader.get_first_arg(), reader.get_second_arg())
            elif command_type == CMD_RETURN:
                asm_emitter.emit_return_statement()

    asm_emitter.close_emitter()


if __name__ == "__main__":
    execute_translation()
