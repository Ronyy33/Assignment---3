"""
VMWriter - Handles emitting stack-based VM bytecode commands to a target output file.
"""

class BytecodeWriter:
    """
    Generates standard Nand2Tetris VM code instructions.
    """
    def __init__(self, out_file_path):
        self._output_stream = open(out_file_path, 'w')

    def emit_push(self, mem_segment, offset_index):
        """Writes a VM push instruction."""
        self._output_stream.write(f'push {mem_segment} {offset_index}\n')

    def emit_pop(self, mem_segment, offset_index):
        """Writes a VM pop instruction."""
        self._output_stream.write(f'pop {mem_segment} {offset_index}\n')

    def emit_arithmetic(self, math_operator):
        """Writes a VM arithmetic/logical command."""
        self._output_stream.write(f'{math_operator}\n')

    def emit_label(self, label_str):
        """Writes a VM label command."""
        self._output_stream.write(f'label {label_str}\n')

    def emit_goto(self, label_str):
        """Writes a VM unconditional goto command."""
        self._output_stream.write(f'goto {label_str}\n')

    def emit_if_goto(self, label_str):
        """Writes a VM conditional if-goto command."""
        self._output_stream.write(f'if-goto {label_str}\n')

    def emit_call(self, func_name, args_count):
        """Writes a VM subroutine call command."""
        self._output_stream.write(f'call {func_name} {args_count}\n')

    def emit_function(self, func_name, locals_count):
        """Writes a VM function declaration command."""
        self._output_stream.write(f'function {func_name} {locals_count}\n')

    def emit_return(self):
        """Writes a VM return command."""
        self._output_stream.write('return\n')

    def close_writer(self):
        """Flushes and closes the output stream."""
        self._output_stream.close()
