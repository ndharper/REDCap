#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Feb  2 10:53:48 2022

@author: nickharper
"""
import csv

missing = []
total = []

subscale_names = []
subscales = {key: [] for key in subscale_names}
missing_formula = 'if(isblankormissingcode([{var}]),1,0)'

with open('bleq_rules.csv', 'r') as rules:
    reader = csv.DictReader(rules)
    for l in reader:
        total.append(l['Formula'].format(var=l['Variable']))
        missing.append(missing_formula.format(var=l['Variable']))
        for sub in subscales:
            if l[sub]:
                subscales[sub].append(l['Formula'].format(var=l['Variable']))

print('Total', '+'.join(total))
print('Missing', '+'.join(missing))
for sub in subscales:
    print(sub, '+'.join(subscales[sub]))



# vnames = [f'[aq_mother_{str(i)}]' for i in range(1,51)]
# print('variables', vnames)

# vnames2 = [f'if([aq_mother_{s}]="",1,0)' for s in vnames]
# outstr = '+'.join(vnames)
# print('total missing',outstr)

# soc_skills = [
#      (1,1)   
    
    
#     ]