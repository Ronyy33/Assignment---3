"""
vm_parser - Parses single .vm files, breaking each line into clean list of tokens
and identifying VM instruction types and arguments.
"""

# Unique constants representing VM command types
CMD_ARITHMETIC = "CMD_ARITHMETIC"
CMD_PUSH       = "CMD_PUSH"
CMD_POP        = "CMD_POP"
CMD_LABEL      = "CMD_LABEL"
CMD_GOTO       = "CMD_GOTO"
CMD_IF         = "CMD_IF"
CMD_FUNCTION   = "CMD_FUNCTION"
CMD_RETURN     = "CMD_RETURN"
CMD_CALL       = "CMD_CALL"


class InstructionReader:
    """
    Parses a single virtual machine VM instruction source file.
    """
    def __init__(self, vm_file_path):
        self._instructions_list = []
        self._cursor_index = -1
        self._active_instruction = []

        # Read and sanitize commands
        with open(vm_file_path, 'r') as file_obj:
            for source_line in file_obj:
                # Strip comments beginning with //
                sanitized_line = source_line.split('//')[0].strip()
                if sanitized_line:
                    self._instructions_list.append(sanitized_line.split())

    def has_remaining_commands(self):
        """Checks if there are more instructions left to parse."""
        return (self._cursor_index + 1) < len(self._instructions_list)

    def next_command(self):
        """Advances cursor to the next instruction in sequence."""
        self._cursor_index += 1
        self._active_instruction = self._instructions_list[self._cursor_index]

    def get_command_type(self):
        """Determines the specific command type category of the active instruction."""
        base_cmd = self._active_instruction[0]
        
        # Arithmetic set checks
        if base_cmd in ("add", "sub", "neg", "eq", "gt", "lt", "and", "or", "not"):
            return CMD_ARITHMETIC
        
        command_mappings = {
            "push":     CMD_PUSH,
            "pop":      CMD_POP,
            "label":    CMD_LABEL,
            "goto":     CMD_GOTO,
            "if-goto":  CMD_IF,
            "function": CMD_FUNCTION,
            "call":     CMD_CALL,
            "return":   CMD_RETURN
        }
        return command_mappings.get(base_cmd)

    def get_first_arg(self):
        """Returns the first argument of the active command."""
        if self.get_command_type() == CMD_ARITHMETIC:
            return self._active_instruction[0]
        return self._active_instruction[1]

    def get_second_arg(self):
        """Returns the second argument of the active command."""
        return int(self._active_instruction[2])
