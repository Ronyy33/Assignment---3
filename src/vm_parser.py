# Command Types
C_ARITHMETIC = "C_ARITHMETIC"
C_PUSH       = "C_PUSH"
C_POP        = "C_POP"
C_LABEL      = "C_LABEL"
C_GOTO       = "C_GOTO"
C_IF         = "C_IF"
C_FUNCTION   = "C_FUNCTION"
C_RETURN     = "C_RETURN"
C_CALL       = "C_CALL"

class Parser:
    def __init__(self, filepath):
        self.commands = []
        self.current_index = -1
        self.current_command = []

        # Read and clean lines
        with open(filepath, 'r') as f:
            for line in f:
                # Remove comments
                clean_line = line.split('//')[0].strip()
                if clean_line:
                    self.commands.append(clean_line.split())

    def has_more_commands(self):
        return (self.current_index + 1) < len(self.commands)

    def advance(self):
        self.current_index += 1
        self.current_command = self.commands[self.current_index]

    def command_type(self):
        cmd = self.current_command[0]
        
        arithmetic_cmds = ["add", "sub", "neg", "eq", "gt", "lt", "and", "or", "not"]
        if cmd in arithmetic_cmds:
            return C_ARITHMETIC
        
        types = {
            "push":     C_PUSH,
            "pop":      C_POP,
            "label":    C_LABEL,
            "goto":     C_GOTO,
            "if-goto":  C_IF,
            "function": C_FUNCTION,
            "call":     C_CALL,
            "return":   C_RETURN
        }
        return types.get(cmd)

    def arg1(self):
        if self.command_type() == C_ARITHMETIC:
            return self.current_command[0]
        return self.current_command[1]

    def arg2(self):
        return int(self.current_command[2])
