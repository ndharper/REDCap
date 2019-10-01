# -*- coding: utf-8 -*-
"""
Created on Thu Sep 19 13:29:37 2019
@author: nicholas harper
Tokenise a REDCap expression.  These are found in redcap field calculations
and branching logic and are used with xternal database testing.  Alorithm
derived from Gareth Reese's post
https://codereview.stackexchange.com/questions/186024/basic-equation-tokenizer
looks for additional syntax not found in REDCap:
    strings can be enslosed in single or double quotes and can contain the
    opposite quite unescaped
    includes unary not operator
    includes in function.  Returns true if value is found in list
    comma seperator for if and in functions
    allows for operator aliases, e.g <= and =>
"""
from enum import Enum
import re
import sys


_token_re = re.compile(r"""
                        # Constants
((?<![\\])['"])(?P<strc>(?:.(?!(?<![\\])\1))*.?)\1 # 'string' or "string"
|(?P<fcons>\d*\.\d*)                               # floating point number
|(?P<icons>\d+)                                    # fixed point number
|(?P<truec>true)                                   # boolean True
|(?P<falsec>false)                                 # boolean False
                        # REDCap variables.
                        # Allow for optional event and instance
|(?P<Rvar>((\[.*?\])(?:\s*)){1,3})                 # from 1 to 3 [xxx]
                    # Operators
|(?P<ops>not            # unitary not function
|and                    # logical and
|or                     # logical or
|!=                     # logical not equal
|<>                     # logical not equal
|=>                     # logical greater than or equal
|>=                     # logical greater than or equal
|<=                     # logical less than or equal
|=<                     # logical less than or equal
|>                      # logical greater than
|<                      # logical less than
|\+                     # arithmetic or unary add
|\-                     # arithmetic or unary minus
|\*                     # arithmetic multiply
|/                      # arithmetic divide
|\^)                    # raise to power
                    # Functions
|(?P<funcs>datediff     # datediff - 5 parameters
|sum                    # sum - followed by list
|abs                    # absolute value
|min                    # minimum - argument is list
|max                    # max - argument is list
|sqrt                   # square root
|mean                   # mean - argument is list
|median                 # median - argument is list
|stdev                  # standartd deviation of list
|roundup                # roundup - argument and places
|rounddown              # rounddown
|round                  # round
|if                     # if(cond,exp_true,exp_false)
|in)                    # isin - followed by list
                    # seperators group
|(?P<seps>\,            # separator func or list memb
|\(                     # open bracket
|\))                    # close bracket
                    # anything else - error
|(?P<errs>\S[a-zA-Z0-9_\.]*)
                      """, re.VERBOSE)


s = """if(datediff('01-01-1600',[mother_dob],'M',trash'dmy',true)< 1000,\
round(datediff('01-01-1600',[enrolment_arm_1][mother_dob][2],\
'M','dmy',true),0)-999, round(datediff([mother_dob],\
[agreededd],'y','dmy',true),0))+73.2 rubish"""


class Token(Enum):
    """ enumeration token types """
    CONST = 0         # string constant (was enclosed in quotes in source)
    RCAP_VAR = 1      # REDCap variable
    OPER = 2          # an operator
    FUNCT = 3         # a function
    SEP = 4           # seperator: comma, ( or )
    ERR = 5           # anything else is an error


def tokenise(s):
    ''' return the tokens one by one'''
    for match in _token_re.finditer(s):
        # various types of constant
        if match.group('strc'):
            yield Token.CONST, match.group('strc')
        elif match.group('fcons'):
            yield Token.CONST, float(match.group('fcons'))
        elif match.group('icons'):
            yield Token.CONST, int(match.group('icons'))
        elif match.group('truec'):
            yield Token.CONST, True
        elif match.group('falsec'):
            yield Token.CONST, False
        # REDCap variables
        # will have variable name encased in square brackets
        # optionally preceeded by an event name, optionally succeeded by
        # and instance number, also encased in square brackets
        elif match.group('Rvar'):   # might get one or more arguments
            # force whitespace between adjacent [..]terms and then split on it
            ss = match.group('Rvar').replace('][', '] [').split()
            r = ()  # empty tuiple
            for a in ss:  # fill it with the terms, discarding brackets
                r = r + (a[1:-1],)  # create a tuple of arguments
            yield Token.RCAP_VAR, r
        # operators
        elif match.group('ops'):
            yield Token.OPER, match.group('ops')
        # functions
        elif match.group('funcs'):
            yield Token.FUNCT, match.group('funcs')
        # seperators
        elif match.group('seps'):
            yield Token.SEP, match.group('seps')
        # unrecognised.  error
        else:
            print('Parsing error: expected a token '
                  'but found {} at position {}'.format(match.group('errs'),
                                                       match.span(),
                                                       file=sys.stderr))
            yield Token.ERR, match.group('errs')
