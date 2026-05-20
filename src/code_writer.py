import os

class CodeWriter:
    def __init__(self, output_path):
        self.file = open(output_path, "w")
        self.vm_filename = ""
        self.current_function = ""
        self.label_id = 0

    def set_file_name(self, filepath):
        self.vm_filename = os.path.basename(filepath).replace(".vm", "")

    def close(self):
        self.file.close()

    def _write(self, *lines):
        for line in lines:
            self.file.write(line + "\n")

    def _get_new_label(self, prefix):
        label = f"{prefix}.{self.label_id}"
        self.label_id += 1
        return label

    def write_init(self):
        self._write("// Bootstrap Code")
        self._write("@256", "D=A", "@SP", "M=D")
        self.write_call("Sys.init", 0)

    # Arithmetic Functions

    def write_arithmetic(self, command):
        self._write(f"// {command}")
        
        if command == "add":
            self._write(*self._binary_template("D+M"))
        elif command == "sub":
            self._write(*self._binary_template("M-D"))
        elif command == "and":
            self._write(*self._binary_template("D&M"))
        elif command == "or":
            self._write(*self._binary_template("D|M"))
        elif command == "neg":
            self._write("@SP", "A=M-1", "M=-M")
        elif command == "not":
            self._write("@SP", "A=M-1", "M=!M")
        elif command in ("eq", "gt", "lt"):
            self._write(*self._compare_template(command))

    def _binary_template(self, operation):
        return [
            "@SP", "AM=M-1", "D=M",
            "A=A-1",
            f"M={operation}"
        ]

    def _compare_template(self, command):
        jmp = {"eq": "JEQ", "gt": "JGT", "lt": "JLT"}[command]
        true_label = self._get_new_label(f"IF_{command.upper()}")
        done_label = self._get_new_label(f"END_{command.upper()}")

        return [
            "@SP", "AM=M-1", "D=M",
            "A=A-1",
            "D=M-D",
            f"@{true_label}", f"D;{jmp}",
            "@SP", "A=M-1", "M=0",
            f"@{done_label}", "0;JMP",
            f"({true_label})",
            "@SP", "A=M-1", "M=-1",
            f"({done_label})"
        ]

    # Memory Access Functions

    def write_push_pop(self, command, segment, index):
        from vm_parser import C_PUSH
        
        self._write(f"// {'push' if command == C_PUSH else 'pop'} {segment} {index}")
        
        segments = {"local":"LCL", "argument":"ARG", "this":"THIS", "that":"THAT"}

        if command == C_PUSH:
            if segment == "constant":
                self._write(f"@{index}", "D=A")
            elif segment in segments:
                self._write(f"@{index}", "D=A", f"@{segments[segment]}", "A=D+M", "D=M")
            elif segment == "temp":
                self._write(f"@{5 + index}", "D=M")
            elif segment == "pointer":
                sym = "THIS" if index == 0 else "THAT"
                self._write(f"@{sym}", "D=M")
            elif segment == "static":
                self._write(f"@{self.vm_filename}.{index}", "D=M")
            self._write("@SP", "A=M", "M=D", "@SP", "M=M+1")

        # C_POP
        else:
            if segment in segments:
                self._write(f"@{index}", "D=A", f"@{segments[segment]}", "D=D+M", "@R13", "M=D")
                self._write("@SP", "AM=M-1", "D=M", "@R13", "A=M", "M=D")
            elif segment == "temp":
                self._write("@SP", "AM=M-1", "D=M", f"@{5 + index}", "M=D")
            elif segment == "pointer":
                sym = "THIS" if index == 0 else "THAT"
                self._write("@SP", "AM=M-1", "D=M", f"@{sym}", "M=D")
            elif segment == "static":
                self._write("@SP", "AM=M-1", "D=M", f"@{self.vm_filename}.{index}", "M=D")

    # Program Flow Functions

    def write_label(self, label):
        full_label = f"{self.current_function}${label}" if self.current_function else label
        self._write(f"({full_label})")

    def write_goto(self, label):
        full_label = f"{self.current_function}${label}" if self.current_function else label
        self._write(f"@{full_label}", "0;JMP")

    def write_if(self, label):
        full_label = f"{self.current_function}${label}" if self.current_function else label
        self._write("@SP", "AM=M-1", "D=M", f"@{full_label}", "D;JNE")

    def write_function(self, name, num_locals):
        self.current_function = name
        self._write(f"({name})")
        # Locals to 0
        for _ in range(num_locals):
            self._write("@SP", "A=M", "M=0", "@SP", "M=M+1")

    def write_call(self, name, num_args):
        ret_addr = self._get_new_label(f"{name}$ret")
        
        # Return address
        self._write(f"@{ret_addr}", "D=A", "@SP", "A=M", "M=D", "@SP", "M=M+1")
        # LCL, ARG, THIS, THAT
        for seg in ["LCL", "ARG", "THIS", "THAT"]:
            self._write(f"@{seg}", "D=M", "@SP", "A=M", "M=D", "@SP", "M=M+1")
        
        # ARG = SP - 5 - num_args
        self._write("@SP", "D=M", f"@{5 + num_args}", "D=D-A", "@ARG", "M=D")
        # LCL = SP
        self._write("@SP", "D=M", "@LCL", "M=D")
        # Jump
        self._write(f"@{name}", "0;JMP")
        # Return label
        self._write(f"({ret_addr})")

    def write_return(self):
        # endFrame (R14) = LCL
        self._write("@LCL", "D=M", "@R14", "M=D")
        # retAddr (R15) = *(endFrame - 5)
        self._write("@5", "A=D-A", "D=M", "@R15", "M=D")
        
        # *ARG = pop()
        self._write("@SP", "AM=M-1", "D=M", "@ARG", "A=M", "M=D")
        # SP = ARG + 1
        self._write("@ARG", "D=M+1", "@SP", "M=D")
        
        # Restore
        for i, seg in enumerate(["THAT", "THIS", "ARG", "LCL"], 1):
            self._write(f"@{i}", "D=A", "@R14", "A=M-D", "D=M", f"@{seg}", "M=D")
            
        # Jump
        self._write("@R15", "A=M", "0;JMP")