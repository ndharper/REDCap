# -*- coding: utf-8 -*-
"""
Created on Tue Feb  4 15:00:05 2020
@author: ndr15
Scan database and create an output list of participants
along with flags to show what type of scans they had, whether
withdrawn, whether they had folow up assessment
Modified Thu Apr 2 11:00:00 2020
output a count of scans rather than a 0/1 flag
"""


# !/usr/bin/python3
from redcap import Project
import itertools
import argparse
import csv


import sys
print(sys.executable)
import os

#

parser = argparse.ArgumentParser(
    description='Scan redcap database and build concatenated drugs entry')
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
    'void_participant']

events_of_interest = [
    'administrative_inf_arm_1',
    'neonatal_scan_arm_1',
    'fetal_scan_arm_1',
    '18_month_assessmen_arm_1'
]

big_data = project.export_records(fields=fields_of_interest,
                                  events=events_of_interest,
                                  records=records_of_interest)
# output fields
fieldnames = [
    'participationid',      # participant
    'redcap_event_name',    # always 'administrative_inf_arm_1'
    'scans_type_fp',        # number of fetal pilot scans
    'scans_type_np',        # number of neonatal pilot scans
    'scans_type_f',         # number of fetal scans
    'scans_type_nt',        # number of neonatal term scans
    'scans_type_npt',       # number of pre-term scans
    'scans_type_ntt',       # number of pre-ter-at-term scans
    'assessed'              # 18 month follow up '0' or '1'
]

with open(args.output, 'w') as outfile:
    csv_writer = csv.DictWriter(outfile, fieldnames=fieldnames,)
    csv_writer.writeheader()
    for participationid, data in itertools.groupby(
            big_data, lambda x: x['participationid']):

        out_flags = {key: 0 for key in fieldnames[2:]}
        for rec in data:
            if rec['redcap_event_name'] == 'administrative_inf_arm_1':
                if rec['void_participant'] == '1':  # if void record ignore
                    out_flags = {}
                    break
            elif rec['redcap_event_name'] == '18_month_assessmen_arm_1':
                out_flags['assessed'] = 1 if rec['date_assessed'] else 0

            else:
                if rec['scan_disabled'] != '1':  # ignored disabled scans
                    if rec['scan_pilot'] == '1':  # pilot scans
                        if rec['redcap_event_name'] == 'neonatal_scan_arm_1':
                            out_flags['scans_type_np'] += 1  # neonatal pilot
                        else:
                            out_flags['scans_type_fp'] += 1  # fetal pilot
                    else:  # not a pilot
                        if rec['scan_req_ack'] == '2':  # ignore if not validated
                            try:
                                if rec['redcap_event_name'] == 'neonatal_scan_arm_1':
                                    if float(rec['nscan_ga_at_birth_weeks']) >= 37:
                                        # term scans
                                        out_flags['scans_type_nt'] += 1

                                    else:
                                        if float(rec['nscan_ga_at_scan_weeks']) < 37:
                                            out_flags['scans_type_npt'] += 1
                                        else:
                                            out_flags['scans_type_ntt'] += 1
                                else:
                                    out_flags['scans_type_f'] += 1
                            except ValueError:
                                print(f'{participationid} bad gestational age')


        if len(out_flags) > 0:  # will be unless we came out after finding void rec
            out_rec = {'participationid': participationid}
            out_rec['redcap_event_name'] = 'administrative_inf_arm_1'
            out_rec.update({key: str(x) for key, x in out_flags.items()})
            print(out_rec)
            csv_writer.writerow(out_rec)

