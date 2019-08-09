# -*- coding: utf-8 -*-
"""
Created on Tue Apr  2 10:12:03 2019

@author: ndr15
"""

#!/usr/bin/python3

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
from openpyxl import Workbook, load_workbook
from openpyxl.styles import PatternFill, Border, Side, Alignment, Protection, Font
from openpyxl.worksheet.pagebreak import Break
from copy import copy

# subroutine to process a variable and return the value
# for some field types the returned value is stored directly in the redcap data
# true/false and yes/no just need the appropriate text value retuened
# radio, dropdown and checkbox require more complicated processing

# subroutine to convert the choices meta data into a dictionary of value, meaning

def unpack_choices(m_ent):
    result={}
#    print(m_ent)
    choices = m_ent.split('|')      # break into list of choices
    for choice in choices:
        choice2 = choice.split(',',1)   # now split the key from the value
        key = choice2[0].strip()      # clean off the blanks
        val = choice2[1].strip()
        result[key]=val
#    print(result)   
    return result



def process_fields(var,entry,meta):
    result = ()             # empty tuple    
    
    if entry[var]=='' :
        return result


    for m_ent in meta:      # find the appropriate entry in the metadat
        if var==m_ent['field_name'] :   
            var_type=m_ent['field_type']   # get the type
            break

    result_str = ''         # accumulate result        
    
    # checkbox fields.  Will return a tuple(bitmap of options, concatenated string of the texts of set options)
    # if the field is blank will return a tuple of (0,'') but this should never happen if called correctly
    if var_type=='checkbox' : # most complicated case because each option has won variable
        choices=unpack_choices(m_ent['select_choices_or_calculations'])       # code shared with dropdown and radio
        result_code = 0
        i=0
        for key, desc in choices.items():
            i += 1
            var_key=var+'___'+key
            var_key = var_key.replace('-','_')  # deal with any hyphens

            if entry[var_key]=='1':              # is option ticked?
                result_code = result_code * 2 +1    # generate bitmap
                if len(result_str)>0 : result_str=result+str+'|'
                result_str = result_str+desc
    
        result =result+(result_code,result_str)
        return result
    
    # dropdown or radio.  returns tuple (value in variable,text designated by that option)
    # if field is empty ('') will return an empty tuple
    elif var_type=='dropdown' or var_type=='radio' :
        if entry[var]!='':      # ignore blank
            choices=unpack_choices(m_ent['select_choices_or_calculations'])
            result_str=choices[entry[var]]
            result = result + (entry[var],result_str)
        return result
    
    # yesno.  returns tuple ('0','No')|('1','Yes') if not blank.  returns empty tuple if blank
    elif var_type=='yesno' :
        if entry[var]!='':
            result = result+(entry[var],)
            if result[0]=='1' :
                result=result+('Yes',)
            else:
                result=result+('No',)
        return result

    # truefalse.  returns tuple ('0','False')|('1','True') if not blank.  returns empty tuple if blank
    elif var_type=='truefalse' :
        if entry[var]!='' :
            result = result+(entry[var],)
            if result[0]=='1' :
                result=result+('True',)
            else:
                result=result+('False')
            
        return result
    
    #calc or notes fields.  Return tuple with just a single entry, value in the fields.
    #blanks may be valid values for these fields
    elif var_type=='calc' or var_type=='notes' :
        result=result+(entry[var],)
        return result
    
    
    # has to be a text field
    else:
               
#        result=result+(entry[var],)
        # now we need to create the second parameter based on the field validation type
        text_type=''
        for m_ent in meta:                # find the appropriate entry in the metadat
            if var==m_ent['field_name'] :
#                print(var,m_ent['field_name'],m_ent['text_validation_type_or_show_slider_number'])
                text_type=m_ent['text_validation_type_or_show_slider_number']   # get the type
                break
        
#        print(var,text_type)
        if text_type=='':
            return result + (entry[var],)               # it's just text so return tuple with just one value

   
        
        elif text_type=='integer':          # integer, return integer value
            result = (entry[var],int(entry[var]))
            print(var,entry[var],int(entry[var]),result)
            return result
        elif text_type=='number':       # float, rteturn floating point number
            result = (entry[var],float(entry[var]))
            return result
        elif text_type=='time' :            # return times in excel decimal fraction of 24*60*60
            a = datetime.datetime.strptime(entry[var],'%H:%M')
            b = a.hour*60+a.minute/(3600*24)  # convert to Excel like time
            result = (entry[var],b)        
            return result
        elif text_type == 'date_dmy':       # date, return as excel format
            a = datetime.datetime.strptime(entry[var],'%Y-%m-%d')
            b=a-datetime.datetime(1899,12,30)       # adjust for excel 2/29/1900
            result = (entry[var],b.days)
            return result
        elif text_type == 'datetime_dmy':
            a = datetime.datetime.strptime(entry[var],'%Y-%m-%d %H:%M')
            b = a-datetime.datetime(18,12,30)
            result = (entry[var],b.days+b.seconds/(3600*24))
            return result
        
    return          # should never get here but return None signals that we've met a data type or a validation we 
                    # didn't plan for
        
        

  



#  new comment

parser = argparse.ArgumentParser(description='RedCap REST client')
parser.add_argument('records_of_interest', metavar='ID', type=str, nargs='+',
                    help='a list of subject IDs to fetch metadata from')
parser.add_argument('--all', dest='export_disabled', action='store_const',
                    const=True, default=False,
                    help='export all subject sessions even when marked as disabled (default: exclude disabled)')

args = parser.parse_args()

records_of_interest = args.records_of_interest



# fetch API key from ~/.redcap-key ... don't keep in the source
key_filename = os.path.expanduser('~') + '/.redcap-key'
if not os.path.isfile(key_filename):
    print('redcap key file {} not found'.format(key_filename))
    sys.exit(1)
api_key = open(key_filename, 'r').read().strip()



api_url = 'https://externalredcap.isd.kcl.ac.uk/api/'
project = Project(api_url, api_key)

# open the Excel workbook that has the variables to check

infile=load_workbook('Codebook for Error Check.xlsx')

source=infile['Variables']
#outfile_name='checking_batch.xlsx'
codebook=[]                         # we're going to load the whole codebook for ease of processing
fields_of_interest=[]               # build a list of fields for the pycap import
for row in source.iter_rows(min_row=2,values_only=True):
    codebook.append(row)
    fields_of_interest.append(row[0])


# now get the data for this record from redcap

meta = project.export_metadata()                # metadata
fem = project.export_fem()                      # form event mappings
big_data=project.export_records(records=records_of_interest,fields=fields_of_interest,
                              format='json')    # here's the data it'self

# build the metadata dictionary so we can find our variables easily
meta_dict={} 
i=0
for var in meta:
    meta_dict[var['field_name']]=i
    i +=1
    
# REDCap will return a list of dictionaries one, dictionary for each event.
# the trouble is that each dictionary will have entries for all the variables
# we asked for, whether they exist in that event or not so we'll have to 
# do a complicated set of loops.
# OUTERMOST LOOP: read through the codebook one variable at a time
# MIDDLE LOOP: get the form name for the variable and loop through the
#    form_event_map looking for entries that reference this form.  There may be
#    more than one if the form is mapped into more than one event.
# INNER LOOP: When we find the form name, loop through the returned data and
#   process the value found in that event.  We will have to loop through all
#    data because there may be multiple instances of the event
    
for var_code in codebook:        # codebook is a list of tuples
        var = var_code[0]
        form = var_code[1]      # this is the form name
        var_type=var_code[3]    # field type
#        print(var,form)
        
        for form_event in fem:  # fem is a list of dictionaries
             if form==form_event['form']:
                event=form_event['unique_event_name']
#                print(var,form,event)
                
                for entry in big_data: # big_data is also a list of dictionaries
                    
                    
                    if var in entry and entry['redcap_event_name']==event:
                        result = process_fields(var,entry,meta)
                        if result==None:
                            sys.exit('Parser failure')
                        print(var,event,entry['redcap_repeat_instance'],result)
                        
                        
                        
                        
                        

#
#                
#                 
#
#
#
#
## build output file
#
#
#source=infile['enrolment_arm_1']
#
#
#
#
## big loop.  Going through once per participant
#
#for participant in records_of_interest:
#    # build data as a list of the events for this participant only
#    data=[] 
#    for event in big_data:
#        if event['participationid']==participant:
#            data.append(event)
#            
#    # now we're going to use the template sheets to build output file with
#    # all the relevant sections and the right number of them for scans
#    # No data at this time but the output created will be used as both an 
#    # input and an output in the data population phase        
#        
#    source=infile['enrolment_arm_1']        # we'll always have enrolment and baby born
#    target=infile.copy_worksheet(source) # copy over the enrolemnt+baby+born # so just copy the whole works
#    
#    target.cell(row=1,column=3,value=participant)  # write the participant number (hard coded row 1, col 3)
#    target.title=participant # output sheet
#    # preserve page margins
#    target.page_margins.left = source.page_margins.left
#    target.page_margins.right = source.page_margins.right
#    target.page_margins.top = source.page_margins.top
#    target.page_margins.bottom = source.page_margins.bottom
#    target.print_title_rows='1:8'
#    
#    
#    scans=['fetal_scan_arm_1','neonatal_scan_arm_1']   # we're going to look for both
#    
#    for event_of_interest in scans:
#        source=infile[event_of_interest]
#        for event in data:              # now look through data to see how many of each
#            
#            if event['redcap_event_name']==event_of_interest and event['scan_disabled'] !='1' : #right event
#                out_bottom=target.max_row               # where to start writing on the output
#                
#                # very inelegant code to copy the cells and the formats
#                for i in range(1,source.max_row+1):
#                    for j in range(1,source.max_column+1):
#                        in_cell=source.cell(row=i,column=j)
#                        out_cell=target.cell(row=out_bottom+i,column=j,value=in_cell.value)
#                        target.cell(row=out_bottom+i,column=j,value=in_cell.value)._style=copy(in_cell._style)
#                        
#                # now we need to write out the event_number
#                
#                new_out_bottom = target.max_row
#                for i in range(out_bottom+1,new_out_bottom+1):
#                    in_cell=target.cell(row=i,column=1)
#                    if in_cell.value == event_of_interest:
#                        target.cell(row=i,column=3,value=event['redcap_repeat_instance'])
#                     
# 
#    
#    
#    
#    inrow=0
#    event={}                            # dummy end event
#    event_of_interest=''
#    event_no = 0                    # flag number of events identified in Excel
#
#    for row in target:
#
#        inrow +=1                       # increment the counter
#        var=row[0].value                # get the variable or event name
#    #    print(var)
#
#        if var in event_list:           # have we found an event to tell us what event we're looking at?
#            
#            # yes - now check to see whether that event exists in the input
#    #        print('found event',var)
#    
##            if event_no>0:
###                page_break=Break(id=inrow)
##                print(target.page_breaks)
##                target.page_breaks.append(Break(id=inrow)) # inject page break
#            
#            event_no +=1
##            print(event_no)
#            event_of_interest=''        # clear event_of_interest so we can tell if we found it
#            for event in data:
#                event_num=''
#                if event['redcap_event_name'] ==var and not('dna_sample' in event.values()):
#                    
#                    if var in scans:
##                        print(var,event['redcap_repeat_instance'],row[2].value)
#                        event_num = row[2].value  # get the event number
#                    
#                    
#                    if event_num==event['redcap_repeat_instance']:
#                        event_of_interest=var       # found it so set up the event_of_interest
#                        break                       # event will be left containing the dictionary for this event
#    
#    # will fall or break out of loop.  Check if we were successful
#            
#            if len(event_of_interest)==0:        # did we find it?
#                row[2].value=var+' Does not Exist for this Participant'
#            
#    # if it's a scan we need to fill in the concatenated drugs field
#                
#            if event_of_interest in scans:
#                drugv_bases=['tri1_','tri2_','tri3_','tri4_','xbaby_']
#                for drug_var_base in drugv_bases:
#    #                print(drug_var_base)
#    
#                    concat_var_name=drug_var_base +'drugs_concat' # this is the variable name
#                    concat_var_value=''                         # initialise it to empty string
#                    for j in range(1,21):  # now we're going to loop through each of the individual drugs entries
#                        var = drug_var_base+'drug'+str(j)          # build the drug name
#    #                    print(var)
#                        if var in event:                # just in case it's not there
#    #                        print(var)
#                            var_value=event[var]        # initialise it to in index 
#    #                        print(var_value)
#                            if var_value !='':          # ignore it if it's blank
#                                if len(concat_var_value)>0 :
#                                    concat_var_value +='|'   # introduce separator unless this is 1st
#                                var_meta=meta[meta_dict[var]]
#                                drop_list=var_meta['select_choices_or_calculations'].split('|')
#                                for entry in drop_list:
#                                    if entry.split(',')[0].strip()==var_value: # find the entry
#                                        
#                                        var_value=entry.split(',')[1].strip()
#    #                                    print(var_value,entry)
#                                        concat_var_value +=var_value            # add it ont
#    #                                    print(var_value,concat_var_value)
#                                        break                                   # done.  stop searching
#                                
#                        # finished the enumerated drug.  now need to pick up the 
#                    var = drug_var_base +'drug_other'
#    #                print(var)
#                    if var in event:
#                        if event[var] !='':
#                            if len(concat_var_value)>0:
#                                concat_var_value +='|'
#                                concat_var_value +=event[var]
#    #                print(concat_var_value)
#                    event[concat_var_name]=concat_var_value
#                    
#    
#    # It's not an event.  Might be spare line, comment, header
#    
#    #    print(var)
#        elif var in meta_dict and len(event_of_interest)>0:    # if not a variable just ignore it
#            var_meta=meta[meta_dict[var]]
#            
#    
#            
#            # now the meaty bit.  Get the value in the appropriate format and passwrite into the template
#            
#            # dropdown or radio buttons.  Just need to map the entry to the value label
#            
#            if var_meta['field_type'] == 'dropdown' or var_meta['field_type'] == 'radio' : # dropdown.  Need to map the value into text
#                drop_list=var_meta['select_choices_or_calculations'].split('|')
#    
#                var_value=event[var]            # initialise to the var value.  This protects if entry is blank
#                for entry in drop_list:
#                    if entry.split(',')[0].strip()==event[var]:
#                        var_value=entry.split(',')[1].strip()
#    #                    print(var,enrolment_data[var],var_value)
#                        break           # this is just breaking out of inner loop
#    
#            # multiple choice buttons.  Need to search the sub variables and produce a concatentated outputr
#            
#            elif var_meta['field_type'] == 'checkbox':
#                var_value=""
#                drop_list=var_meta['select_choices_or_calculations'].split('|')
#    
#                for entry in drop_list:
#                    varx=var+'___'+entry.split(',')[0].strip().replace('-','_')
#                    if event[varx]=='1':
#                        if len(var_value)>0:
#                            var_value=var_value+'|'
#                        var_value=var_value+entry.split(',')[1].strip()
#            else:
#                var_value=event[var]
#                
#    #        print(var,var_value)       
#            row[2].value=var_value
#    
#    
#    
#    
#    
##    CellFill = PatternFill(fill_type='gray125')
#    
#    #source['C1'].fill=CellFill           
#                  
#   
#
## now output under a fresh name
#
#infile.save(outfile_name)
#
#        
#
