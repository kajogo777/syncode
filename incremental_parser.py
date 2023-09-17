import copy
import time
import re
import lark
from lark.indenter import Indenter
from lark.lexer import Token
from lark import Lark


class IncrementalParser:
    def __init__(self):
        self.parser = Lark.open( # This is the standard Lark parser
            "python_grammar.lark",
            parser="lalr",
            lexer="basic",
            start="file_input",
            postlex=PythonIndenter(),
            propagate_positions=True,
        )
        self.cur_ac_terminals = None
        self.next_ac_terminals = None
        self.cur_pos = 0 # Current cursor position in the lexer tokens list
        self.lexer_pos = 0 # Current lexer position in the code
        self.dedent_queue = []
        self.cur_indentation_level = 0
        self.interactive = self.parser.parse_interactive('')
        self.parser_token_seq = []
        self.log_time = False

        # To enable going back to old state of the parser
        self.prev_lexer_tokens = None
        self.cur_pos_to_interactive = {}

    def get_acceptable_next_terminals(self, code):
        # Stores the sequence of tokens that the parser has seen in the order  
        last_terminal_complete = True
        interactive = self.interactive
        lexer_tokens = self._lex_code(code)

        # Restore the previous state of the parser
        if self.prev_lexer_tokens is not None:
            i = 0
            while i < len(self.prev_lexer_tokens) and lexer_tokens[i] == self.prev_lexer_tokens[i]:
                i += 1
            self.cur_pos = i
            # print('********Restoring parser state 1!', self.cur_pos-1)
            if (self.cur_pos-1) in self.cur_pos_to_interactive:
                # print('*******Restoring parser state 2!', self.cur_pos-1)
                # print(self.cur_pos_to_interactive[self.cur_pos-1][0].state_stack)
                self._restore_parser_state(self.cur_pos-1)

        self.prev_lexer_tokens = lexer_tokens

        # Parse the tokens
        parsing_start_time = time.time()
        try:
            while self.cur_pos < len(lexer_tokens):
                token = lexer_tokens[self.cur_pos]
                self.cur_pos += 1
                # print(self.cur_pos, repr(token), interactive.parser_state.state_stack, len(lexer_tokens))

                if token.type == '_INDENT':
                    self.cur_indentation_level += 1
                
                if token.type == '_DEDENT':
                    # Do not shoot dedent tokens unless there is some code on the next line
                    self.dedent_queue.append(token)
                    continue
                else:
                    # Shoot all the dedent tokens that are in the queue
                    while not len(self.dedent_queue)==0:
                        dedent_token = self.dedent_queue.pop()
                        self.cur_indentation_level -= 1
                        interactive.feed_token(dedent_token)
                        self.parser_token_seq.append(dedent_token)

                # TODO: Check if there is an overhead of computing accept tokens
                interactive.feed_token(token)

                # Store the current state of the parser
                self._store_parser_state(self.cur_pos-1, interactive.parser_state.copy(), self.cur_indentation_level, interactive.accepts())
                
                self.parser_token_seq.append(token)
        except lark.exceptions.UnexpectedToken as e:
            pass

        if self.log_time:
            print('Time taken for parsing:', (time.time() - parsing_start_time))

        # Compute current terminal string
        if self.lexer_pos < len(code):
            last_terminal_complete = False
            current_term_str = code[self.lexer_pos:]
            # print('current_term_str 1:', current_term_str)
        else:
            current_term_str = self.parser_token_seq[-1].value
            # print('current_term_str 2:', current_term_str, self.parser_token_seq)

        if last_terminal_complete:            
            if self.parser_token_seq[-1].type == '_NL':
                next_ac_terminals = self.next_ac_terminals
                # Compute next line accepted indentation levels
                max_next_indentation_level = 0
                # print('next_ac_terminals:', next_ac_terminals)

                if '_INDENT' in next_ac_terminals:
                    max_next_indentation_level = self.cur_indentation_level + 1
                elif '_DEDENT' in next_ac_terminals and len(next_ac_terminals)==1:
                    max_next_indentation_level = self.cur_indentation_level - 1
                elif '_DEDENT' in next_ac_terminals and len(next_ac_terminals)>1:
                    max_next_indentation_level = self.cur_indentation_level

                cur_tabs = self.parser_token_seq[-1].value.split('\n')[-1].count('\t')

                # Remove the _INDENT and _DEDENT tokens from the acceptable tokens
                # since we inform the indentation level through the _TAB token
                if '_INDENT' in next_ac_terminals:
                    next_ac_terminals.remove('_INDENT')
                if '_DEDENT' in next_ac_terminals:
                    next_ac_terminals.remove('_DEDENT')

                # '_NL' is always accepted in this case
                next_ac_terminals.add('_NL')

                if cur_tabs < max_next_indentation_level:
                    # print('Expect a tab!')
                    next_ac_terminals.add('_TAB')
                # elif cur_tabs > max_next_indentation_level:
                #     raise Exception('Invalid indentation level! max_next_indentation_level: {}, cur_tabs: {}'.format(max_next_indentation_level, cur_tabs))
        else:
            # Since current terminal is incomplete, next token should add to current terminal
            next_ac_terminals = None

        return self.cur_ac_terminals, self.next_ac_terminals, current_term_str
    
    def _store_parser_state(self, pos, parser_state, indentation_level, accepts):
        self.cur_pos_to_interactive[pos] = (parser_state, indentation_level, accepts)
        self.cur_ac_terminals = copy.deepcopy(self.next_ac_terminals)
        self.next_ac_terminals = copy.deepcopy(accepts)

    def _restore_parser_state(self, pos):
        self.interactive.parser_state, self.cur_indentation_level, self.cur_ac_terminals = self.cur_pos_to_interactive[pos]

    def get_matching_terminal(self, s):
        # Special cases
        if s == '\t':
            return '_TAB'
        
        # Non-regex direct matches
        for t in self.parser.terminals:
            if t.pattern.type == 'str' and t.pattern.value == s:
                return t.name
        
        # Regex matches
        for t in self.parser.terminals:
            if t.pattern.type == 're' and re.fullmatch(t.pattern.value, s):
                return t.name

        # TODO: Use priorities to resolve conflicts
        return None

    def prefix_terminal_match(self, s, v):
        # Returns all terminals such that s+v matches the prefix of the terminal
        s = s+v
        import regex
        for t in self.parser.terminals:
            not_supported = ['_NL', 'COMMENT', 'STRING', 'IMAG_NUMBER']
            if t.pattern.type == 're' and t.name not in not_supported:
                # print('Pattern:', t.pattern.value, s, t.name)
                match = regex.Regex(t.pattern.value).d(s)
                # print(match)
                if match != None:
                    return t.name
        return None        

    def _lex_code(self, code):
        # Collect Lexer tokens
        lexer_tokens = []
        interactive = self.parser.parse_interactive(code)
        # interactive = self.interactive
        lexing_start_time = time.time()
        lexer_state = interactive.lexer_thread.state
        indenter = self.parser.lexer_conf.postlex

        # Reset the indentation level
        indenter.indent_level = [0]
        indenter.paren_level = 0
        # print('Starting indent level:', indenter.indent_level)

        try:
            while lexer_state.line_ctr.char_pos < len(lexer_state.text):
                blexer = interactive.lexer_thread.lexer.lexer
                token = blexer.next_token(lexer_state)
                self.lexer_pos = lexer_state.line_ctr.char_pos
               
                # Perform postlexing indentation
                if token.type == indenter.NL_type:
                    # print('NL token:', indenter.indent_level)
                    lexer_tokens += indenter.handle_NL(token)
                else:
                    lexer_tokens.append(token)

                if token.type in indenter.OPEN_PAREN_types:
                        indenter.paren_level += 1
                elif token.type in indenter.CLOSE_PAREN_types:
                        indenter.paren_level -= 1
                        assert indenter.paren_level >= 0
        except lark.exceptions.UnexpectedCharacters as e:
            pass
        except EOFError as e:
            # print('EOF Error!')
            # print(code)
            # print(lexer_state.line_ctr.char_pos, len(lexer_state.text))
            pass
            # raise e
        # Add the remaining dedent tokens at the end
        # while len(indenter.indent_level) > 1:
        #     indenter.indent_level.pop()
        #     lexer_tokens.append(Token(indenter.DEDENT_type, ''))
        if self.log_time:
            print('Time taken for lexing:', time.time() - lexing_start_time)
        # print(lexer_tokens)
        return lexer_tokens


class PythonIndenter(Indenter):
        NL_type = "_NL"
        OPEN_PAREN_types = ["LPAR", "LSQB", "LBRACE"]
        CLOSE_PAREN_types = ["RPAR", "RSQB", "RBRACE"]
        INDENT_type = "_INDENT"
        DEDENT_type = "_DEDENT"
        tab_len = 4
