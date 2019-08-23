# -*- coding: utf-8 -*-
"""
Created on Thu Aug 22 15:19:53 2019

@author: ndr15
"""

import csv



def do_stuff():
    out_write.writerow(['bob','carol','ted'])
    out_write.writerow(['bob2','carol2','ted2'])
    return


out = open('testw.txt','w',newline='')
out_write=csv.writer(out,quotechar="'",delimiter='\t')
out_write.writerow(['1st','2nd','3rd'])
do_stuff()
out.close()
    
    
    
