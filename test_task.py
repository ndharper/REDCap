# -*- coding: utf-8 -*-
"""
Created on Tue Feb  4 15:00:05 2020

@author: ndr15
"""


def check_dhcp_checksum(n):
    check = 0
    mul = 1
    for i in n:
        ca = int(i) * mul
        check += ca - (ca > 9) * 9
        mul ^= 3  # toggle between 1 and 2
    return check


# !/usr/bin/python3
from redcap import Project, RedcapError
import itertools
import argparse
from copy import copy
import re
import urllib3
import sys
import os
import smtplib
from email.message import EmailMessage

cc = re.compile(r'CC\d{5}[A-CX][NX]\d{2}')  # Regex for CC number
# set up emails

# user_id = os.environ.get('EMAIL_UID')
# password = os.environ.get('EMAIL_PASS')
# sender = os.environ.get('EMAIL')
user_id = 'k1477427@kcl.ac.uk'
password = 'Rosebud35'
sender = 'nicholas.harper@kcl.ac.uk'
smpt_server = 'smtp.office365.com'
port = 587
parser = argparse.ArgumentParser(description='Generate dHCP bad IDs list')
parser.add_argument('mail_recipients', metavar='ID', type=str, nargs='*',
                    help='list of email recipients seperated by comma',
                    default=sender)
args = parser.parse_args()
recipients = args.mail_recipients


# # fetch API key from ~/.redcap-key ... don't keep in the source
# key_filename = os.path.expanduser('~') + '/.redcap-key'
# if not os.path.isfile(key_filename):
#     print('redcap key file {} not found'.format(key_filename))
#     sys.exit(1)
# api_key = open(key_filename, 'r').read().strip()
# api_url = 'https://externalredcap.isd.kcl.ac.uk/api/'
# project = Project(api_url, api_key)
# fields_of_interest = ['participationid', 'void_enrol']
# events_of_interest = ['enrolment_arm_1']

# big_data = project.export_records(fields=fields_of_interest,
#                                   events=events_of_interest)
# out = ''  # output message
# for rec in big_data:  # loop through all records
#     idno = rec['participationid']
#     if rec['void_enrol'] != '1':  # don't check trash records
#         if cc.fullmatch(idno):  # match regex?
#             check = check_dhcp_checksum(idno[2:7])  # yes.  how about checksum?
#             if check != int(idno[-2:]):
#                 out += f'{idno}: Bad checksum {idno[-2:0]}should be {check:02}\n'
#         else:
#             out += f'{idno}: Bad format\n'

# # print and email the errors
# if len(out) > 0:
#     print(out, file=sys.stderr)

out = 'testing123'
with smtplib.SMTP(smpt_server, port) as smtp:
    smtp.starttls()
    smtp.login(user_id, password)

    subject = 'scheduler test message'
    msg = f'Subject: {subject}\n\n{out}'
    print(type(recipients), recipients)
    smtp.sendmail(sender, recipients, msg)
