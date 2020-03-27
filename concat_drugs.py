# -*- coding: utf-8 -*-
"""
Created on Tue Feb  4 15:00:05 2020

@author: ndr15
"""



# !/usr/bin/python3
from redcap import Project, RedcapError
import itertools
import argparse
import csv
from copy import copy
import re
import urllib3
import sys
import os
from email.message import EmailMessage
#

parser = argparse.ArgumentParser(description='Scan redcap database and build concatenated drugs entry')
parser.add_argument('records_of_interest', metavar='ID', type=str, nargs='*',
                    help='a list of subject IDs to fetch metadata from')
parser.add_argument('--output', type=str, default='concatenated_drugs.txt',
                    help='Output file')

args = parser.parse_args()
records_of_interest = args.records_of_interest

prefixes = ['tri1', 'tri2', 'tri3', 'tri4', 'xbaby']
suffixes = ['_drug' + str(x) for x in range(1, 21)] + ['_drug_other']
fields_of_interest = [i + j for i in prefixes for j in suffixes]
events_of_interest = ['neonatal_scan_arm_1', 'fetal_scan_arm_1']


# fetch API key from ~/.redcap-key ... don't keep in the source
key_filename = os.path.expanduser('~') + '/.redcap-key'
if not os.path.isfile(key_filename):
    print('redcap key file {} not found'.format(key_filename))
    sys.exit(1)
api_key = open(key_filename, 'r').read().strip()
api_url = 'https://externalredcap.isd.kcl.ac.uk/api/'
project = Project(api_url, api_key)

big_data = project.export_records(records=records_of_interest,
                                  fields=fields_of_interest,
                                  events=events_of_interest)
meta = [x for x in project.export_metadata() if x['field_name']
        in fields_of_interest]  # filter the junk out

# get the drug choices list

for ment in meta:
    if ment['field_name'] == 'tri1_drug1':
        drug_list = ment['select_choices_or_calculations'].split('|')
        drug_dict = {int(key): val.strip().upper()
                     for key, val in [x.split(',', 1) for x in drug_list]}
        break


fieldnames = ['participationid', 'redcap_event_name', 'redcap_repeat_instance']
fieldnames += [x + '_drugs_concat' for x in prefixes]

with open(args.output, 'w') as outfile:
    csv_writer = csv.DictWriter(outfile, fieldnames=fieldnames,)
    csv_writer.writeheader()

    for rec in big_data:
        out_rec = {key: rec[key] for key in fieldnames[0:3]}
        for period in prefixes:
            drugs = []
            for var in [period + '_drug'+str(x) for x in range(1, 21)]:
                if rec[var]:
                    drugs += [drug_dict[int(rec[var])]]
            if rec[period + '_drug_other']:
                drugs += [rec[period + '_drug_other'].strip().upper()]
            out_rec[period + '_drugs_concat'] = '|'.join(sorted(drugs))

        print(out_rec)        
        csv_writer.writerow(out_rec)
        
        
 