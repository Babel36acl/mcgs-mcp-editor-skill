"""Optional native-code tests; no vendor/project fixtures are redistributed."""
import operator
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'mcgs-mcp-editor/scripts'))
EDITOR = os.environ.get('MCGS_EDITOR')
RUNTIME = os.environ.get('MCGS_RUNTIME')


@unittest.skipUnless(EDITOR and RUNTIME,'Set MCGS_EDITOR and MCGS_RUNTIME to run version-pinned native tests')
class NativeTests(unittest.TestCase):
    def test_all_comparisons(self):
        from conditional_codegen import ConditionalCodegen
        from vendor_vm import VendorVM
        for token, compare in [('=',operator.eq),('<>',operator.ne),('<',operator.lt),
                               ('>',operator.gt),('<=',operator.le),('>=',operator.ge)]:
            code,_ = ConditionalCodegen(EDITOR,RUNTIME).compile(
                f'If Input {token} 10 Then\nResult = 100\nElse\nResult = 200\nEndIf', {'Input':1,'Result':2})
            for value in (9.,10.,11.):
                with self.subTest(operator=token,value=value):
                    result = VendorVM({1:value,2:0.},RUNTIME).run(code)
                    self.assertEqual(result['writes'],[{'object_id':2,'value':100. if compare(value,10.) else 200.}])
                    self.assertEqual(result['values'][1],value)

    def test_nested_addition_and_no_else(self):
        from conditional_codegen import ConditionalCodegen
        from vendor_vm import VendorVM
        source = 'If Input > 0 Then\nResult = Input + 1\nIf Result > 10 Then\nResult = 1\nEndIf\nEndIf'
        code,_ = ConditionalCodegen(EDITOR,RUNTIME).compile(source,{'Input':1,'Result':2})
        for x,y in [(0.,-1.),(1.,2.),(10.,1.)]:
            self.assertEqual(VendorVM({1:x,2:-1.},RUNTIME).run(code)['values'],{1:x,2:y})

    def test_int32_limits_and_reject(self):
        from conditional_codegen import ConditionalCodegen, parse_source
        from vendor_vm import VendorVM
        for number in (-2147483648,0,2147483647):
            code,_ = ConditionalCodegen(EDITOR,RUNTIME).compile(f'Result = {number}',{'Result':2})
            self.assertEqual(VendorVM({2:-1.},RUNTIME).run(code)['values'][2],float(number))
        for source in ['Result = 2147483648','Result = 1.5','Result = Unknown',
                       'If Result = 1 Then\nResult = 2','Result = 1 / 0','Else\nResult = 2']:
            with self.subTest(source=source),self.assertRaises(ValueError):
                parse_source(source,{'Result':2})


if __name__ == '__main__':
    unittest.main()
