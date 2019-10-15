# -*- coding: utf-8 -*-
"""
Created on Tue Oct 15 11:16:54 2019
Test the iterator to extract data from big_data
@author: ndr15
"""
import itertools


def _participant_(rec):
    return rec['participationid']


def return_data(big_data):
    grouped_data = itertools.groupby(big_data, _participant_)

    for key, gen in grouped_data:

        data = list(gen)
        scans = 0
        selector = []  # will use to filter data later
        for rec in data:
            selector.append(True)
            # void participant
            if args.void and rec['redcap_event_name'] ==\
                    'administrative_inf_arm_1' and \
                    rec['void_participant'] == '1':
#                print('void participant {}'.format(rec['participationid']))
                data = []  # chuck everything out
                break  # we're done with this participant

            # check the scan records for void or disabled
            if rec['redcap_event_name'] in ['neonatal_scan_arm_1',
                                            'fetal_scan_arm_1']:
#                print('{} {} pilot {} disabled {}'.format(rec['participationid'],rec['redcap_event_name'],
#                      rec['scan_pilot'], rec['scan_disabled']))
#                print(rec['participationid'],rec['redcap_event_name'],args.pilot,
#                      rec['scan_pilot'],args.disabled, rec['scan_disabled'])
#                print(rec['participationid'],rec['redcap_event_name'],
#                      (args.disabled and rec['scan_disabled'] == '1') or
#                      (args.pilot == 0 and rec['scan_pilot'] == '1'))
                if (args.disabled and rec['scan_disabled'] == '1') or\
                 (args.pilot == 0 and rec['scan_pilot'] == '1'):
                    selector[-1] = False  # de-select this record
                    print('bum scan {} {} disabled {} pilot {}'.format(rec['participationid'],
                          rec['redcap_event_name'], rec['scan_disabled'], rec['scan_pilot']))
                else:
                    scans += 1  # found a good scan

        if args.noscan and scans == 0 or len(data) <= 0:
#            print(key,' thrown out')
            data = []  # clear

        else:
            data = list(itertools.compress(data, selector))
            yield data
