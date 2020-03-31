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

#

parser = argparse.ArgumentParser(description='Scan redcap database and build concatenated drugs entry')
parser.add_argument('records_of_interest', metavar='ID', type=str, nargs='*',
                    help='a list of subject IDs to fetch metadata from')

parser.add_argument('--output', type=str, default='cohort.txt',
                    help='Output file')

args = parser.parse_args()



# fetch API key from ~/.redcap-key ... don't keep in the source
key_filename = os.path.expanduser('~') + '/.redcap-key'
if not os.path.isfile(key_filename):
    print('redcap key file {} not found'.format(key_filename))
    sys.exit(1)
api_key = open(key_filename, 'r').read().strip()
api_url = 'https://externalredcap.isd.kcl.ac.uk/api/'
project = Project(api_url, api_key)

records_of_interest = args.records_of_interest
fields_of_interest = [
                    'participationid',
                    'scan_req_ack',
                    'scan_disabled',
                    'nscan_ga_at_birth_weeks',
                    'nscan_ga_at_scan_weeks',
                    'fscan_ga_at_scan_weeks',
                    'scan_pilot',
                    'date_assessed',
                    'void_participant'
                    ]

events_of_interest = [
                    'administrative_inf_arm_1',
                    'neonatal_scan_arm_1',
                    'fetal_scan_arm_1',
                    '18_month_assessmen_arm_1'
                    ]

big_data = project.export_records(fields=fields_of_interest,
                                  events=events_of_interest,
                                  records=records_of_interest)

fieldnames = [
              'participationid',
              'redcap_event_name',
              'scans_type_fp',
              'scans_type_np',
              'scans_type_f',
              'scans_type_nt',
              'scans_type_npt',
              'scans_type_ntt',
              'assessed'
              ]

with open(args.output, 'w') as outfile:
    csv_writer = csv.DictWriter(outfile, fieldnames=fieldnames,)
    csv_writer.writeheader()
    for participationid, data in itertools.groupby(
            big_data, lambda x: x['participationid']):
        
        out_flags = {key: 0 for key in fieldnames[2:]} 
        for rec in data:
       
            if rec['redcap_event_name'] == 'administrative_inf_arm_1':
                if rec['void_participant']:
                    out_flags={}
                    break
            elif rec['redcap_event_name'] == '18_month_assessmen_arm_1':
                out_flags['assessed'] = 1 if rec['date_assessed'] else 0
                
            else:
                
                if rec['scan_disabled'] != '1' and rec['scan_req_ack'] == '2':
                    if rec['scan_pilot'] == '1':
                        if rec['redcap_event_name'] == 'neonatal_scan_arm_1':
                            out_flags['scans_type_np'] |= 1  # toggle true
                        else:
                            out_flags['scans_type_fp'] |= 1
                    else:
                        if rec['redcap_event_name'] == 'neonatal_scan_arm_1':
                            if float(rec['nscan_ga_at_birth_weeks']) >= 37:
                                out_flags['scans_type_nt'] |= 1  # toggle true
                            
                            else:
                                if float(rec['nscan_ga_at_scan_weeks']) < 37:
                                    out_flags['scans_type_npt'] |= 1  # toggle true
                                else:
                                    out_flags['scans_type_ntt'] |= 1  # toggle true
                            
                        else:
                            out_flags['scans_type_f'] |= 1
            
                       
        if len(out_flags) > 0:
            out_rec = {'participationid': participationid}
            out_rec['redcap_event_name'] = 'administrative_inf_arm_1'
            out_rec.update({key: str(x) for key, x in out_flags.items()})
            print(out_rec)
            csv_writer.writerow(out_rec)
                
        
        

#meta = [x for x in project.export_metadata() if x['field_name']
#        in fields_of_interest]  # filter the junk out

## get the drug choices list
#
#for ment in meta:
#    if ment['field_name'] == 'tri1_drug1':
#        drug_list = ment['select_choices_or_calculations'].split('|')
#        drug_dict = {int(key): val.strip().upper()
#                     for key, val in [x.split(',', 1) for x in drug_list]}
#        break
#
#
#fieldnames = ['participationid', 'redcap_event_name', 'redcap_repeat_instance']
#fieldnames += [x + '_drugs_concat' for x in prefixes]
#
#with open(args.output, 'w') as outfile:
#    csv_writer = csv.DictWriter(outfile, fieldnames=fieldnames,)
#    csv_writer.writeheader()
#
#    for rec in big_data:
#        out_rec = {key: rec[key] for key in fieldnames[0:3]}
#        for period in prefixes:
#            drugs = []
#            for var in [period + '_drug'+str(x) for x in range(1, 21)]:
#                if rec[var]:
#                    drugs += [drug_dict[int(rec[var])]]
#            if rec[period + '_drug_other']:
#                drugs += [rec[period + '_drug_other'].strip().upper()]
#            out_rec[period + '_drugs_concat'] = '|'.join(sorted(drugs))
#
#        print(out_rec)        
#        csv_writer.writerow(out_rec)
#        
#        
# 