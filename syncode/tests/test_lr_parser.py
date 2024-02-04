import sys, os
import time
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + '/../')
from incremental_parser import IncrementalParser
from grammars.python_parser import PythonIncrementalParser
from common import run_tests

def test_tiny():
    inc_parser = IncrementalParser('syncode/grammars/tiny_grammar.lark', parser='lr')
    partial_code = "ccdd"
    out = inc_parser.parser.parse(partial_code)
    print(out)

def test_calc():
    # 17 states become 31 from LALR(1) to LR(1)
    inc_parser = IncrementalParser('syncode/grammars/calc_grammar.lark', parser='lr')
    partial_code = "113 + 235 + 1111"
    out = inc_parser.parser.parse(partial_code)
    inc_parser.get_acceptable_next_terminals(partial_code)
    assert out.children[0].children[0].children[1].children[0] == '235'

def test_time():
    """
    Results:
    Time taken for building LR(1): 102.65705108642578
    Time taken for building LALR(1): 0.3684959411621094
    LR(1) states: 752
    LALR(1) states: 4926
    Time taken for parsing with LR(1): 0.14716744422912598
    Time taken for parsing with LALR(1): 1.5615639686584473
    """
    time1 = time.time()
    inc_lr_parser = PythonIncrementalParser(parser='lr')
    time2 = time.time()
    print("Time taken for building LR(1):", time2 - time1)
    inc_lalr_parser = PythonIncrementalParser(parser='lalr')
    time3 = time.time()
    print("Time taken for building LALR(1):", time3 - time2)
    
    print(len(inc_lr_parser.parser.parser.parser._parse_table.states))
    print(len(inc_lalr_parser.parser.parser.parser._parse_table.states))

    prompt = 'from typing import List\n\n\ndef has_close_elements(numbers: List[float], threshold: float) -> bool:\n\t""" Check if in given list of numbers, are any two numbers closer to each other than\n\tgiven threshold.\n\t>>> has_close_elements([1.0, 2.0, 3.0], 0.5)\n\tFalse\n\t>>> has_close_elements([1.0, 2.8, 3.0, 4.0, 5.0, 2.0], 0.3)\n\tTrue\n'

    generated_code = '\t"""\n\tfor i in range(len(numbers) -1, -1, -1):\n\t\tfor j in range(i+1, len(numbers) -1, -1):\n\t\t\tif abs(numbers[i] - numbers[j] ) < threshold:\n\t\t\t\treturn True\n\treturn False\n\n\ndef has_close_elements_with_threshold(numbers: List[float] , threshold: float) -> bool:\n\ta="shu'

    i = 0
    while i<len(generated_code):
        i += 2
        r = inc_lalr_parser.get_acceptable_next_terminals(prompt + generated_code[:i])
    assert r.remainder == '"shu'
    assert r.next_ac_indents == None
    time4 = time.time()
    print("Time taken for parsing with LALR(1):", time4 - time3)

    i = 0
    while i<len(generated_code):
        i += 2
        r = inc_lr_parser.get_acceptable_next_terminals(prompt + generated_code[:i])
    assert r.remainder == '"shu'
    assert r.next_ac_indents == None
    time5 = time.time()
    print("Time taken for parsing with LR(1):", time5 - time4)

def test_correct():
    inc_lr_parser = PythonIncrementalParser(parser='lr')
    inc_lalr_parser = PythonIncrementalParser(parser='lalr')

    prompt = 'from typing import List\n\n\ndef has_close_elements(numbers: List[float], threshold: float) -> bool:\n\t""" Check if in given list of numbers, are any two numbers closer to each other than\n\tgiven threshold.\n\t>>> has_close_elements([1.0, 2.0, 3.0], 0.5)\n\tFalse\n\t>>> has_close_elements([1.0, 2.8, 3.0, 4.0, 5.0, 2.0], 0.3)\n\tTrue\n'

    generated_code = '\t"""\n\tfor i in range(len(numbers) -1, -1, -1):\n\t\tfor j in range(i+1, len(numbers) -1, -1):\n\t\t\tif abs(numbers[i] - numbers[j] ) < threshold:\n\t\t\t\treturn True\n\treturn False\n\n\ndef has_close_elements_with_threshold(numbers: List[float] , threshold: float) -> bool:\n\ta="shu'

    i = 0
    while i<len(generated_code):
        i += 2
        r1 = inc_lalr_parser.get_acceptable_next_terminals(prompt + generated_code[:i])
        r2 = inc_lr_parser.get_acceptable_next_terminals(prompt + generated_code[:i])
        assert r1 == r2, (r1, r2)

# Not adding test_time, test_correct as it may take about 3-4 minutes to run
# TODO: Add them when parser caching is added
        
tests = [test_calc, test_tiny]
# tests = [test_time]
# tests = [test_correct]
run_tests(tests) 