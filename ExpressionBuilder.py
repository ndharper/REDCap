# -*- coding: utf-8 -*-
"""
Created on Thu Oct 10 14:45:32 2019

@author: ndr15
"""


import urllib3
import sys
import os
import subprocess
import glob
import io
urllib3.disable_warnings()
from redcap import Project, RedcapError
from requests import post
from pathlib import Path
import smtplib
import datetime
import pycurl
import certifi
import json
import argparse
from openpyxl import Workbook, load_workbook
from openpyxl.styles import PatternFill, Border, Side, Alignment, Protection, Font
from openpyxl.worksheet.pagebreak import Break
from copy import copy
import re
import csv
from BinaryTree import BinaryTree
from operator import itemgetter

class Stack:
     def __init__(self):
         self.items = []

     def isEmpty(self):
         return self.items == []

     def push(self, item):
         self.items.append(item)

     def pop(self):
         return self.items.pop()

     def peek(self):
         return self.items[len(self.items)-1]

     def size(self):
         return len(self.items)


from enum import Enum



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
|=                      # logical equal to
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
|stdev                  # standard deviation of list
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
            r = ()  # empty tuple
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


def return_rcap(tup, entry, data, dictionary):
    """
    return the value pointed to by [<event>]<[instance]
    this will need more work to accomodate full smart variables
    but that can wait until we've replaced PyCap
    """
    if len(tup) == 1:
        res = process_fields()
    for e in tup:
        if e in dictionary:
            var = e
            break
        for ev in data:
            id ev[redcap_event_name] == e
            break
        if tup[-1]    
    

s = """[m_sib_adhd_sch_12f] = '1' or [m_sib_adhd_sch_12f] = '2' or
[m_sib_adhd_sch_12f] = '3' or [xyz][m_sib_adhd_sch_12f] = '4' or
[m_sib_adhd_sch_12f] = '5' or [m_sib_adhd_sch_12f][2] = '6' or
[m_sib_adhd_sch_12f] = '7' or [abc][m_sib_adhd_sch_12f][3] = '8' or
[m_sib_adhd_sch_12f] = '9' or [m_sib_adhd_sch_12f] = '10'
"""
left_bracket = ('(', 0)  # highest precedence
TreeRoot = BinaryTree(left_bracket)  # dummy an initial left bracket tuple node
CurrentNode = TreeRoot

for a in tokenise(s):
    if a == Token.CONST:  # operand
        CurrentNode = CurrentNode.insertBelowCross(a)

    elif a == Token.RCAP_VAR:  # Redcap variable
        """
        decode the redcap variable.  Value is a tuple equating to
        [<event>]<variable>[<redcap_repeat_instance>|<smart variable>]
        """
        rvar = return_rcap(a)
            

