"""Compile, inspect or emulate the bounded numeric BASIC bytecode subset."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command',required=True)
    compile_parser = sub.add_parser('compile')
    compile_parser.add_argument('--source',type=Path,required=True)
    compile_parser.add_argument('--symbols',type=Path,required=True)
    compile_parser.add_argument('--editor',type=Path,required=True)
    compile_parser.add_argument('--runtime',type=Path,required=True)
    compile_parser.add_argument('--output',type=Path,required=True,help='New JSON program report')
    simulate_parser = sub.add_parser('simulate')
    simulate_parser.add_argument('--program',type=Path,required=True)
    simulate_parser.add_argument('--values',type=Path,required=True,help='JSON mapping numeric object IDs to initial values')
    simulate_parser.add_argument('--runtime',type=Path,required=True)
    inspect_parser = sub.add_parser('inspect',help='Check bytecode framing, typed stack and jump targets without native dependencies')
    inspect_parser.add_argument('--program',type=Path,required=True,help='JSON report containing code_hex')
    args = parser.parse_args()
    if args.command == 'compile':
        if args.output.exists():
            raise ValueError('Output exists; choose a new report path')
        from conditional_codegen import ConditionalCodegen
        source = args.source.read_text(encoding='utf-8-sig')
        symbols = json.loads(args.symbols.read_text(encoding='utf-8-sig'))
        _, result = ConditionalCodegen(args.editor,args.runtime).compile(source,symbols)
        result['status'] = 'NATIVE_CODEGEN_ONLY_HOST_ACCEPTANCE_REQUIRED'
        with args.output.open('x',encoding='utf-8') as stream:
            json.dump(result,stream,ensure_ascii=False,indent=2)
        print(args.output.resolve())
    elif args.command == 'simulate':
        from vendor_vm import VendorVM
        program = json.loads(args.program.read_text(encoding='utf-8-sig'))
        values = {int(k):float(v) for k,v in json.loads(args.values.read_text(encoding='utf-8-sig')).items()}
        print(json.dumps(VendorVM(values,args.runtime).run(bytes.fromhex(program['code_hex'])),ensure_ascii=False,indent=2))
    else:
        from bytecode_inspect import inspect_program
        program = json.loads(args.program.read_text(encoding='utf-8-sig'))
        print(json.dumps(inspect_program(bytes.fromhex(program['code_hex'])),ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
