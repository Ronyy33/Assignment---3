# Jack Compiler & 2D Convolution

## Requirements

- Python 3

## Project Structure

```
├── jack/   
│   ├── Conv.jack       # 2D Convolution class
│   └── Main.jack       # Main driver class
├── src/  
│   ├── JackCompiler.py       # Main entry point driver
│   ├── JackTokenizer.py      # Lexical tokenizer (JackLexicalLexer class)
│   ├── CompilationEngine.py  # Syntactic parser + VM generator (SyntaxAnalyzer class)
│   ├── SymbolTable.py        # Symbol table (LexicalScopeTable class)
│   ├── VMWriter.py           # VM bytecode writer (BytecodeWriter class)
│   ├── vm_translator.py      # VM-to-ASM translator main driver
│   ├── vm_parser.py          # VM command parser (InstructionReader class)
│   └── code_writer.py        # ASM code writer (AssemblyEmitter class)
├── out/  
    ├── ConvT.xml       # Token XML
    ├── MainT.xml
    ├── Conv.xml        # Parse tree XML
    ├── Main.xml
    ├── Conv.vm         # VM bytecode
    ├── Main.vm
    └── out.asm         # Final Hack assembly
```

## How to Run

### 1. Compile Jack to VM

```bash
python src/JackCompiler.py jack/Conv.jack
python src/JackCompiler.py jack/Main.jack
```

This produces token XML, parse tree XML, and VM code in the `out/` directory.

### 2. Translate VM to Assembly

```bash
python src/vm_translator.py out/
```

This produces `out/out.asm` using the VM translator.

### 3. Run on CPU Emulator

1. Open the Nand2Tetris CPU Emulator.
2. Load `out/out.asm`.
3. Set the speed to "Fast" and run.
4. The convolution output will be printed to the screen.
