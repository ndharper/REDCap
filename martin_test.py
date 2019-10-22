# -*- coding: utf-8 -*-
"""
Created on Tue Oct 22 17:13:41 2019

@author: ndr15
"""

def _participant_(rec):
    """function to return the participantid for this record"""
    return rec['participationid']


def return_data(bd):
    """
    return a list of records for a single participant.  big_data doesn't
    need to be sorted in any particular order but records for a given
    participant must be adjacent
    """
    ibd = iter(bd)
    grouped_data = itertools.groupby(ibd, _participant_)

    for key, gen in grouped_data:

        data = list(gen)
        yield(data)
