# -*- coding: utf-8 -*-
"""
Created on Wed Sep 11 11:17:05 2019

Test program to play with argparse

@author: ndr15
"""
import urllib3
import sys
import os
import argparse
from redcap import Project, RedcapError
from openpyxl import Workbook, load_workbook
from openpyxl.styles import PatternFill, Border, Side, Alignment, Protection, Font
from openpyxl.worksheet.pagebreak import Break
import csv
import re

parser = argparse.ArgumentParser(description='RedCap REST client')
parser.add_argument('--dictionary', type=str,
                    default='Codebook for Error Check.xlsx {Working Copy]',
                    help='''Dictionary file with variables to check
                    If dictionary file is an Excel workbook then specification
                    can be followed by an optional worksheet name enclosed in
                    square brackets ([]).  If no worksheet name is given then
                    the first sheet in the workbook will be used.  If file
                    does not have an extension .xlx, .xlsx, .xlsb or .xlsm
                    then it will be processed as an ordinary comma seperated
                    test file''')
parser.add_argument('--output', type=argparse.FileType('w'),
                    default='dHCPmissing.txt',
                    help='Output file')
parser.add_argument('--pilot', action='count', default=0,
                    help='''--p means include pilot scans in deciding whether
                    to processs a record but ignore any data in it.
                    --pp means process the data from pilot scans too''')
parser.add_argument('--void', action='store_false',
                    help='include void participant records')
parser.add_argument('--disabled', action='store_false',
                    help='include disabled scan records')
parser.add_argument('--noscan', action='store_false',
                    help='include records with no scans at all')
parser.add_argument('--xlimits', action='store_true',
                    help='''override maximum and minimum limits on variable
                    values in the meta data with values from the dictionary''')
parser.add_argument('records_of_interest', metavar='ID', type=str, nargs='*',
                    help='a list of subject IDs to fetch metadata from')
args = parser.parse_args()


"""
Check and see if the dictionary file is an Excel spreadsheet.  If it isn't,
assume it's a comma seperated file.  Excel file specification will be of the
form filespec.xl* optionally folled by [Worksheet]. [] are used to contain
the worksheet name beacuse those characters won't occur in the full filespec.
If no worksheet is specified then program will use the active sheet in the
workbook.
If file extension isn't .xl* then assume it's a comma seperated file with the
column headers in the first row
"""

fpat = re.compile(r'\S.+((.xlsb)|(.xlsm)|(.xlsx)|(.xls))(?=(\s*\[(.*?)\]))?')
match = fpat.match(args.dictionary)

# now build the dictionary
dictionary = {}
if match:  # if we matched then it's an Excel file
    print ('reading Excel File')
    # read the data dictionary
    dict_cols = {}
    infile = load_workbook(match.group(0))
    if match.group(7):
        source = infile[match.group(7)]
    else:
        source = infile.active
    dg = source.iter_rows(min_row=1, values_only=True)
    header = next(dg, None)
    '''
    Build a dictionary of dicionaries.  Top level uses the variable name
    from ist column as a key with value equal to a dictionary of all the
    other variables in the row with each getting a key equal to the column
    heading
    '''
    ig_col = header.index('Ignore') if 'Ignore' in header else -999

    for rec in dg:
        if ig_col >= 0:
            if rec[ig_col] in ['Yes', 1, True]:
                continue
        dic_entry = {}
        for i in range(1, len(header)):
            dic_entry[header[i]] = rec[i]

        dictionary[rec[0]] = dic_entry

else:
    print('reading .csv file')
    with open(match.group(0), 'r') as infile:
        inreader = csv.reader(infile)
        headers = next(inreader, None)
        ig_col = header.index('Ignore') if 'Ignore' in header else -999
        dictionary = {}
        for rec in inreader:
            if ig_col > 0:
                if rec[ig_col] in ['Yes', 1, True]:
                    continue
            dic_entry = {}
            for i in range(1, len(header)):
                dic_entry[header[i]] = rec[i]
            dictionary[rec[0]] = dic_entry

# fetch API key from ~/.redcap-key ... don't keep in the source
key_filename = os.path.expanduser('~') + '/.redcap-key'
if not os.path.isfile(key_filename):
    print('redcap key file {} not found'.format(key_filename))
    sys.exit(1)
api_key = open(key_filename, 'r').read().strip()

api_url = 'https://externalredcap.isd.kcl.ac.uk/api/'
project = Project(api_url, api_key)

fields_of_interest = list(dictionary.keys())
try:
    big_data = project.export_records(fields=fields_of_interest,
                                      records=args.records_of_interest,
                                      format='json')

except RedcapError:
    print('Redcap export too large')

#_token_re = re.compile(r'''
#                       '((?:\\.|.)*?)'|    # match quoted string 'abc123'
#                       (((\[.\])+)|       # match [event][variable][ins]
#                       (datediff)|
#                       (not)|
#                       (and)|
#                       (or)|
#                       (if)|
#                       (in)|
#                       (!=)|
#                       (<>)|
#                       (=>)|
#                       (>=)|
#                       (<=)|
#                       (=<)|
#                       (+)|
#                       (-)|
#                       (\*)|
#                       (/)|
#                       (\^)|
#                      ''')
#                       