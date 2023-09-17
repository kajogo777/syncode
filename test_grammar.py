import sys
import traceback
import torch
from incremental_parser import IncrementalParser
from transformers import (
    LlamaTokenizer,
)

tokenizer = LlamaTokenizer.from_pretrained("/share/models/llama_model/hf/7B")

def test_vocab_terminals():
    token_to_terminal = {}
    token_type_count = {}
    inc_parser = IncrementalParser()

    for i in range(tokenizer.vocab_size):
        token = tokenizer.decode(i)
        token_type = inc_parser.get_matching_terminal(token)
        if token_type is not None:
            token_to_terminal[token] = token_type

            # Count the number of tokens of each type
            if token_type not in token_type_count:
                token_type_count[token_type] = 0

            token_type_count[token_type] += 1

    print(token_type_count)
    print(f"Found {len(token_to_terminal)}/{tokenizer.vocab_size} tokens that form a terminal.")


def test_parser1():
    inc_parser = IncrementalParser()
    code = f"""
a = 3
b = 4
c = 5

def f():
    ""\"
    funcdef!!!
    ""\"
    a = 4
    c = 3
    
    # Random comment
    if i == 2:
        2 + 3
        t + 1
        pass
    else:
        return
    
    return sss
"""
    inc_parser.get_acceptable_next_terminals(code)


def test_parser2():
    inc_parser = IncrementalParser()
    partial_code = 'from typing import List\n\n\ndef has_close_elements(numbers: List[float], threshold: float) -> bool:\n\t\n\ta=3+5\n\tb='
    _, next_ac_terminals, _ = inc_parser.get_acceptable_next_terminals(partial_code)
    assert 'FLOAT_NUMBER' in next_ac_terminals

def test_parser3():
    inc_parser = IncrementalParser()
    partial_code = 'from typing import List\n\n\ndef has_close_elements(numbers: List[float], threshold: float) -> bool:\n\t\n\tfor i in range(len(numbers) -1, -1, -1) :\n\t\tfor j in range(i+1, len(numbers) ,1) :\n\t\t\tif abs(numbers[i] - numbers[j] ) < threshold :\n\t\t\t\treturn True\n'
    _, next_ac_terminals, _ = inc_parser.get_acceptable_next_terminals(partial_code)
    print(next_ac_terminals)
    assert '_TAB' in next_ac_terminals

def test_parser4():
    inc_parser = IncrementalParser()
    partial_code = 'from typing import List\n\n\ndef has_close_elements(numbers: List[float], threshold: float) -> bool:\n\t\n\tfor i in range(len(numbers) -1, -1, -1) :\n\t\tfor j in range(i+1, len(numbers) ,1) :\n\t\t\tif abs(numbers[i] - numbers[j] ) < threshold :\n'
    _, next_ac_terminals, _ = inc_parser.get_acceptable_next_terminals(partial_code)
    assert '_TAB' in next_ac_terminals

def test_parser5():
    inc_parser = IncrementalParser()
    partial_code = 'from typing import List\n\n\ndef has_close_elements(numbers: List[float], threshold: float) -> bool:\n\t\n\tfor i in range(len(numbers) -1, -1, -1) :\n\t\tfor j in range(i+1, len(numbers) ,1) :\n\t\t\tif abs(numbers[i] - numbers[j] ) < threshold :\n\t\t\t\treturn True\n\t\t\t\t'
    # There cannot be another tab after this
    _, next_ac_terminals, _ = inc_parser.get_acceptable_next_terminals(partial_code)
    assert '_TAB' not in next_ac_terminals

def test_parser6():
    inc_parser = IncrementalParser()
    partial_code = 'from typing import List\n\n\ndef has_close_elements(numbers: List[float], threshold: float) -> bool:\n\t\n\tfor i in range(len(numbers) -1, -1, -1) :\n\t\tfor j in range(i+1, len(numbers) ,1) :\n\t\t\tif abs(numbers[i] - numbers[j] ) < threshold :\n\t\t\t\treturn True\n\n\n\t\t\t\t'
    # There cannot be another tab after this
    _, next_ac_terminals, _ = inc_parser.get_acceptable_next_terminals(partial_code)
    assert '_TAB' not in next_ac_terminals

def test_parser6():
    inc_parser = IncrementalParser()
    partial_code = 'from typing import List\n\n\ndef has_close_elements(numbers: List[float], threshold: float) -> bool:\n\t\n\tfor i in range(len(numbers) -1, -1, -1) :\n\t\tfor j in range(i+1, len(numbers) ,1) :\n\t\t\tif abs(numbers[i] - numbers[j] ) < threshold :\n\t\t\t\treturn True\n\n\t\t\t\n\t\t'
    # There can be another tab after this
    _, next_ac_terminals, _ = inc_parser.get_acceptable_next_terminals(partial_code)
    assert '_TAB' in next_ac_terminals

def test_parser7():
    inc_parser = IncrementalParser()
    partial_code = 'from typing import List\n\n\ndef has_close_elements(numbers: List[float], threshold: float) -> bool:\n\tfor i in range(len(numbers) -1, -1, -1) :\n\t\tif numbers[i] - numbers[i+1] < threshold:\n\t\t\treturn True\n\treturn False\n'
    _, next_ac_terminals, _ = inc_parser.get_acceptable_next_terminals(partial_code)
    assert '_TAB' in next_ac_terminals
    assert '_NL' in next_ac_terminals

def test_parser8():
    inc_parser = IncrementalParser()
    partial_code = 'from typing import List\n\n\ndef separate_paren_groups(paren_string: str) -> List[str]:\n\tpar = []\n\tfor i in par:\n\t\tif i == \''
    _, next_ac_terminals, cur_term_str = inc_parser.get_acceptable_next_terminals(partial_code)
    assert cur_term_str == " '"

def test_parser9():
    inc_parser = IncrementalParser()
    partial_code = 'from typing import List\n\n\ndef separate_paren_groups(paren_string: str) -> List[str]:\n\tpar = []\n\tfor i in par:\n\t\tif i == \'Hello'
    _, next_ac_terminals, cur_term_str = inc_parser.get_acceptable_next_terminals(partial_code)
    print(cur_term_str)
    assert cur_term_str == " 'Hello"

def test_parser10():
    inc_parser = IncrementalParser()
    partial_code = 'from typing import List\n\n\ndef has_close_elements(numbers: List[float], threshold: float) -> bool:\n\t""" Check if in given list of numbers, are any two numbers closer to each other than\n\tgiven threshold.\n\t>>> has_close_elements([1.0, 2.0, 3.0], 0.5)\n\tFalse\n\t>>> has_close_elements([1.0, 2.8, 3.0, 4.0, 5.0, 2.0], 0.3)\n\tTrue\n\t"""\n\tfor i in range(len(numbers) -1, -1, -1):\n\t\tfor j in range(i+1, len(numbers) -1, -1):\n\t\t\tif abs(numbers[i] - numbers[j] ) < threshold:\n\t\t\t\treturn True\n\treturn False\n\n\ndef has_close_elements_with_threshold(numbers: List[float] , threshold: float) -> bool:\n\t""'
    cur_ac_terminals, next_ac_terminals, cur_term_str = inc_parser.get_acceptable_next_terminals(partial_code)
    assert cur_term_str == '""'


def test_incremental_parser():
    inc_parser = IncrementalParser()
    partial_code = 'from typing import List\n\n\ndef has_close_elements(numbers: List[float], threshold: float) -> bool:\n\t""" Check if in given list of numbers, are any two numbers closer to each other than\n\tgiven threshold.\n\t>>> has_close_elements([1.0, 2.0, 3.0], 0.5)\n\tFalse\n\t>>> has_close_elements([1.0, 2.8, 3.0, 4.0, 5.0, 2.0], 0.3)\n\tTrue\n\t"""\n\tfor i in range(len(numbers) -1, -1, -1):\n\t\tfor j in range(i+1, len(numbers) -1, -1):\n\t\t\tif abs(numbers[i] - numbers[j] ) < threshold:\n\t\t\t\treturn True\n\treturn False\n\n\ndef has_close_elements_with_threshold(numbers: List[float] , threshold: float) -> bool:\n\t""'
    cur_ac_terminals, next_ac_terminals, cur_term_str = inc_parser.get_acceptable_next_terminals(partial_code[:len(partial_code)-10])
    cur_ac_terminals, next_ac_terminals, cur_term_str = inc_parser.get_acceptable_next_terminals(partial_code)
    assert cur_term_str == '""'

def test_incremental_parser2():
    inc_parser = IncrementalParser()
    prompt = 'from typing import List\n\n\ndef has_close_elements(numbers: List[float], threshold: float) -> bool:\n\t""" Check if in given list of numbers, are any two numbers closer to each other than\n\tgiven threshold.\n\t>>> has_close_elements([1.0, 2.0, 3.0], 0.5)\n\tFalse\n\t>>> has_close_elements([1.0, 2.8, 3.0, 4.0, 5.0, 2.0], 0.3)\n\tTrue\n'

    generated_code = '\t"""\n\tfor i in range(len(numbers) -1, -1, -1):\n\t\tfor j in range(i+1, len(numbers) -1, -1):\n\t\t\tif abs(numbers[i] - numbers[j] ) < threshold:\n\t\t\t\treturn True\n\treturn False\n\n\ndef has_close_elements_with_threshold(numbers: List[float] , threshold: float) -> bool:\n\ta="shu'

    i = 0
    while i<len(generated_code):
        i += 2
        _, _, cur_term_str = inc_parser.get_acceptable_next_terminals(prompt + generated_code[:i])
    assert cur_term_str == '"shu'

def test_get_matching_terminals():
    inc_parser = IncrementalParser()
    assert inc_parser.get_matching_terminal("\t") == "_TAB"
    assert inc_parser.get_matching_terminal(tokenizer.decode(torch.tensor([12]), skip_special_tokens=True)) == "_TAB"
    
    assert inc_parser.get_matching_terminal("\n") == "_NL"
    assert inc_parser.get_matching_terminal(tokenizer.decode(torch.tensor([13]), skip_special_tokens=True)) == "_NL"
    
    # Keywords
    assert inc_parser.get_matching_terminal("def") == "DEF"
    assert inc_parser.get_matching_terminal("in") == "IN"
    assert inc_parser.get_matching_terminal("if") == "IF"
    assert inc_parser.get_matching_terminal("else") == "ELSE"
    assert inc_parser.get_matching_terminal("elif") == "ELIF"
    assert inc_parser.get_matching_terminal("for") == "FOR"
    assert inc_parser.get_matching_terminal("while") == "WHILE"
    assert inc_parser.get_matching_terminal("try") == "TRY"
    assert inc_parser.get_matching_terminal("except") == "EXCEPT"
    assert inc_parser.get_matching_terminal("finally") == "FINALLY"
    assert inc_parser.get_matching_terminal("with") == "WITH"
    assert inc_parser.get_matching_terminal("class") == "CLASS"

    # Regex
    assert inc_parser.get_matching_terminal("1234") == "DEC_NUMBER"
    assert inc_parser.get_matching_terminal("12.34") == "FLOAT_NUMBER"
    assert inc_parser.get_matching_terminal("pqr") == "NAME"
    assert inc_parser.get_matching_terminal("\'ssss\'") == "STRING"
    assert inc_parser.get_matching_terminal('\"ssss\"') == "STRING"
    assert inc_parser.get_matching_terminal('\"""ssss\"""') == "COMMENT"
    assert inc_parser.get_matching_terminal('\"""ssss') == None


tests = [test_get_matching_terminals, test_vocab_terminals, test_parser1, test_parser2, test_parser3, test_parser4, test_parser5, test_parser6, test_parser7, test_parser8, test_parser9, test_incremental_parser, test_incremental_parser2]

test_result = {}

for test in tests:
    print(f"Running test {test.__name__}")
    # try:
    test()
    print(f"Test {test.__name__} passed.")
    test_result[test.__name__] = 'passed'
    # except AssertionError:
    #     _, _, tb = sys.exc_info()
    #     traceback.print_tb(tb) # Fixed format
    #     tb_info = traceback.extract_tb(tb)
    #     filename, line, func, text = tb_info[-1]
    #     print('An error occurred on line {} in statement {}'.format(line, text))
    #     test_result[test.__name__] = 'failed'
    # except Exception as e:
    #     print(f"Test {test.__name__} failed.")
    #     print(e)
    #     test_result[test.__name__] = 'failed'
    
    print("-"*80)

tests_passed = 0
for test_name, result in test_result.items():
    if result == 'passed':
        tests_passed += 1
        # Use green color for passed tests
        print(f"\033[92m{test_name}: {result}\033[0m")
    else:
        # Use red color for failed tests
        print(f"\033[91m{test_name}: {result}\033[0m")
print(f"Passed {tests_passed}/{len(tests)} tests.")
