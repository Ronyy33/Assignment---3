"""
code_writer - Translates parsed virtual machine instructions (push, pop, math, branching, calls)
into target Hack assembly code commands.
"""

import os

class AssemblyEmitter:
    """
    Emits Hack assembly language translation corresponding to parsed VM commands.
    """
    def __init__(self, destination_path):
        self._file_handle = open(destination_path, "w")
        self._active_vm_filename = ""
        self._active_function_name = ""
        self._unique_label_idx = 0

    def update_active_file(self, full_filepath):
        """Sets the name of the VM file currently being processed."""
        self._active_vm_filename = os.path.basename(full_filepath).replace(".vm", "")

    def close_emitter(self):
        """Closes the assembly output stream."""
        self._file_handle.close()

    def _emit(self, *assembly_lines):
        """Helper to write multiple lines of assembly code to the output stream."""
        for single_line in assembly_lines:
            self._file_handle.write(single_line + "\n")

    def _generate_asm_label(self, label_prefix):
        """Constructs a unique assembly label using a serial counter."""
        assembled_label = f"{label_prefix}.{self._unique_label_idx}"
        self._unique_label_idx += 1
        return assembled_label

    def emit_bootstrap_code(self):
        """Writes the VM translator bootstrap initialization routine."""
        self._emit("// Bootstrap Code")
        self._emit("@256", "D=A", "@SP", "M=D")
        self.emit_function_call("Sys.init", 0)

    # Mathematical / Logical Instructions Emitter

    def emit_arithmetic_command(self, operation_cmd):
        """Translates and writes Hack ASM instructions representing arithmetic operations."""
        self._emit(f"// {operation_cmd}")
        
        if operation_cmd == "add":
            self._emit(*self._create_binary_template("D+M"))
        elif operation_cmd == "sub":
            self._emit(*self._create_binary_template("M-D"))
        elif operation_cmd == "and":
            self._emit(*self._create_binary_template("D&M"))
        elif operation_cmd == "or":
            self._emit(*self._create_binary_template("D|M"))
        elif operation_cmd == "neg":
            self._emit("@SP", "A=M-1", "M=-M")
        elif operation_cmd == "not":
            self._emit("@SP", "A=M-1", "M=!M")
        elif operation_cmd in ("eq", "gt", "lt"):
            self._emit(*self._create_compare_template(operation_cmd))

    def _create_binary_template(self, operator_formula):
        """Constructs general assembly sequence for popping two variables and running an operation."""
        return [
            "@SP", "AM=M-1", "D=M",
            "A=A-1",
            f"M={operator_formula}"
        ]

    def _create_compare_template(self, comparison_op):
        """Constructs assembly logic for relational tests (eq, gt, lt) with branching labels."""
        jump_instruction = {"eq": "JEQ", "gt": "JGT", "lt": "JLT"}[comparison_op]
        true_case_label = self._generate_asm_label(f"IF_{comparison_op.upper()}")
        end_case_label = self._generate_asm_label(f"END_{comparison_op.upper()}")

        return [
            "@SP", "AM=M-1", "D=M",
            "A=A-1",
            "D=M-D",
            f"@{true_case_label}", f"D;{jump_instruction}",
            "@SP", "A=M-1", "M=0",
            f"@{end_case_label}", "0;JMP",
            f"({true_case_label})",
            "@SP", "A=M-1", "M=-1",
            f"({end_case_label})"
        ]

    # Memory Access Emitters

    def emit_push_pop_command(self, cmd_category, segment_name, index_offset):
        """Translates VM stack operations push / pop into native memory operations."""
        from vm_parser import CMD_PUSH
        
        self._emit(f"// {'push' if cmd_category == CMD_PUSH else 'pop'} {segment_name} {index_offset}")
        
        target_segments = {
            "local": "LCL",
            "argument": "ARG",
            "this": "THIS",
            "that": "THAT"
        }

        if cmd_category == CMD_PUSH:
            if segment_name == "constant":
                self._emit(f"@{index_offset}", "D=A")
            elif segment_name in target_segments:
                self._emit(f"@{index_offset}", "D=A", f"@{target_segments[segment_name]}", "A=D+M", "D=M")
            elif segment_name == "temp":
                self._emit(f"@{5 + index_offset}", "D=M")
            elif segment_name == "pointer":
                target_ptr = "THIS" if index_offset == 0 else "THAT"
                self._emit(f"@{target_ptr}", "D=M")
            elif segment_name == "static":
                self._emit(f"@{self._active_vm_filename}.{index_offset}", "D=M")
            
            # Finalize push: place D in stack and increment SP pointer
            self._emit("@SP", "A=M", "M=D", "@SP", "M=M+1")

        # Command is CMD_POP
        else:
            if segment_name in target_segments:
                self._emit(f"@{index_offset}", "D=A", f"@{target_segments[segment_name]}", "D=D+M", "@R13", "M=D")
                self._emit("@SP", "AM=M-1", "D=M", "@R13", "A=M", "M=D")
            elif segment_name == "temp":
                self._emit("@SP", "AM=M-1", "D=M", f"@{5 + index_offset}", "M=D")
            elif segment_name == "pointer":
                target_ptr = "THIS" if index_offset == 0 else "THAT"
                self._emit("@SP", "AM=M-1", "D=M", f"@{target_ptr}", "M=D")
            elif segment_name == "static":
                self._emit("@SP", "AM=M-1", "D=M", f"@{self._active_vm_filename}.{index_offset}", "M=D")

    # Control Flow & Branching Emitters

    def emit_branch_label(self, label_name):
        """Writes a local or global assembly destination label."""
        assembled_label = f"{self._active_function_name}${label_name}" if self._active_function_name else label_name
        self._emit(f"({assembled_label})")

    def emit_goto_command(self, label_name):
        """Writes an unconditional jump statement to the target label."""
        assembled_label = f"{self._active_function_name}${label_name}" if self._active_function_name else label_name
        self._emit(f"@{assembled_label}", "0;JMP")

    def emit_if_goto_command(self, label_name):
        """Writes a conditional jump statement based on popping the stack."""
        assembled_label = f"{self._active_function_name}${label_name}" if self._active_function_name else label_name
        self._emit("@SP", "AM=M-1", "D=M", f"@{assembled_label}", "D;JNE")

    def emit_function_declaration(self, function_name, local_vars_count):
        """Declares a function entry point and clears local variables space to 0."""
        self._active_function_name = function_name
        self._emit(f"({function_name})")
        # Initialize locals space to 0 on stack
        for _ in range(local_vars_count):
            self._emit("@SP", "A=M", "M=0", "@SP", "M=M+1")

    def emit_function_call(self, function_name, args_count):
        """Generates frame setup, segment backups, and jumps to invoke a subroutine call."""
        return_label = self._generate_asm_label(f"{function_name}$ret")
        
        # Write return address target on the stack
        self._emit(f"@{return_label}", "D=A", "@SP", "A=M", "M=D", "@SP", "M=M+1")
        # Save calling function frame registers: LCL, ARG, THIS, THAT
        for frame_seg in ["LCL", "ARG", "THIS", "THAT"]:
            self._emit(f"@{frame_seg}", "D=M", "@SP", "A=M", "M=D", "@SP", "M=M+1")
        
        # Calculate new ARG segment position: SP - 5 - args_count
        self._emit("@SP", "D=M", f"@{5 + args_count}", "D=D-A", "@ARG", "M=D")
        # Re-align LCL segment to start of local stack pointer
        self._emit("@SP", "D=M", "@LCL", "M=D")
        # Unconditional transfer of control to subroutine
        self._emit(f"@{function_name}", "0;JMP")
        # Return address label placeholder
        self._emit(f"({return_label})")

    def emit_return_statement(self):
        """Restores callers stack frame environment and branches back to the caller's return target."""
        # store endFrame in R14: endFrame (R14) = LCL
        self._emit("@LCL", "D=M", "@R14", "M=D")
        # store return address in R15: retAddr (R15) = *(endFrame - 5)
        self._emit("@5", "A=D-A", "D=M", "@R15", "M=D")
        
        # Assign return value to caller's argument index: *ARG = pop()
        self._emit("@SP", "AM=M-1", "D=M", "@ARG", "A=M", "M=D")
        # Reposition SP pointer back to caller's frame: SP = ARG + 1
        self._emit("@ARG", "D=M+1", "@SP", "M=D")
        
        # Incrementally recover frames LCL, ARG, THIS, THAT pointers
        for restore_idx, frame_seg in enumerate(["THAT", "THIS", "ARG", "LCL"], 1):
            self._emit(f"@{restore_idx}", "D=A", "@R14", "A=M-D", "D=M", f"@{frame_seg}", "M=D")
            
        # Complete sub-routine jump: return to caller
        self._emit("@R15", "A=M", "0;JMP")