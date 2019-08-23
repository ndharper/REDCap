# -*- coding: utf-8 -*-
"""
Created on Thu Aug 22 14:24:03 2019

@author: ndr15
"""

# test csv
import csv

def writesome():
    out_write.writerow(['bob','carol','ted'])
    out_write.writerow(['bob2','carol2','ted2'])

with open('test.txt','w',newline='') as out:
    out_write=csv.writer(out,quotechar="'",delimiter='\t')
    out_write.writerow(['1st','2nd','3rd'])
    writesome()
    