#!/usr/bin/env python


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

# fetch API key from ~/.redcap-key ... don't keep in the source
key_filename = os.path.expanduser('~') + '/.redcap-key'
if not os.path.isfile(key_filename):
    print('redcap key file {} not found'.format(key_filename))
    sys.exit(1)
api_key = open(key_filename, 'r').read().strip()
api_url = 'https://externalredcap.isd.kcl.ac.uk/api/'
project = Project(api_url, api_key)

parser = argparse.ArgumentParser(
    description='Extract the 18 Month Follow up Data')
parser.add_argument('records_of_interest', metavar='ID', type=str, nargs='*',
                    help='a list of subject IDs to fetch metadata from')



args = parser.parse_args()


records_of_interest= args.records_of_interest

# records_of_interest.append(sys.argv[1])
outfile_name = sys.argv[1]+".json"

print(records_of_interest,outfile_name)

fields_of_interest = ['participationid', 'scan_validation', 'scan_validation_req_ack','scan_appt_date', 'fscan_appt_date','scan_req_ack','ga_at_scan','xscan_gestation','scan_ga_at_birth','xscan_baby_weight','baby_gender']
events_of_interest = ['fetal_scan_arm_1', 'neonatal_scan_arm_1','baby_born_arm_1']
print(records_of_interest,fields_of_interest)

project = Project(api_url,api_key)
# Set the connection & location constants
#prefix folder structure with r to avoid unicode codec error



data = project.export_records(records=records_of_interest,fields=fields_of_interest,events=events_of_interest,format='json')

#print(data)

# with open(outfile_name,'w') as outfile:
# 	json.dump(data,outfile)
	
	