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
import re
import csv
from pythonds.basic import Stack
from BinaryTree import BinaryTree
from operator import itemgetter


# subroutine to process a variable and return the value
# for some field types the returned value is stored directly in the redcap data
# true/false and yes/no just need the appropriate text value retuened
# radio, dropdown and checkbox require more complicated processing

# subroutine to convert the choices meta data into a dictionary of value, meaning

def unpack_choices(m_ent):
    result={}

    choices = m_ent.split('|')      # break into list of choices
    for choice in choices:
        choice2 = choice.split(',',1)   # now split the key from the value
        key = choice2[0].strip()      # clean off the blanks
        val = choice2[1].strip()
        result[key]=val
  
    return result



def process_fields(var,entry,meta):
    result = ()             # empty tuple    
    
#    if entry[var]=='' :
#        return result


    for m_ent in meta:      # find the appropriate entry in the metadata
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
            var_key = var_key.lower()

            if entry[var_key]=='1':              # is option ticked?
                result_code = result_code * 2 +1    # generate bitmap
                if len(result_str)>0 : result_str=result_str+'|'
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
                result=result+('False',)
            
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

                text_type=m_ent['text_validation_type_or_show_slider_number']   # get the type
                break
        

        if text_type=='' or entry[var]=='':
            return result + (entry[var],)               # it's just text so return tuple with just one value

   
        
        elif text_type=='integer':          # integer, return integer value
            result = (entry[var],int(entry[var]))

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
        
# parse the branching logic

        
def parse_branch(var,meta,my_event,big_data):
    rvar_pat=re.compile(r'\[(.*?)\]')
    str_pat=re.compile(r'\'(.*?)\'')
    paren_pat=re.compile(r'\((.*?)\)')
    operators={
            '=':'=',
            '>=':'>=',
            '>':'>',
            '<':'<',
            '=>':'>=',
            '<=':'<=',
            '=<':'<=',
            '!=':'!=',
            '<>':'!=',
            'and':'and',
            'or':'or',
            ')':')',
            '(':'('}
    
    
            
    out_list=[]
    for entry in meta:
        if entry['field_name']==var:
            break
    
    if entry['field_name'] != var:
        return                          # this will happen if the var isn't in the meta data list - error
    
    if entry['branching_logic'] =='':
        return                          # we've found it but it doesn't have any branching logic
    
    terms = entry['branching_logic'].split()    # now we should have alist of individual terms
#    
    for term in terms:
        matches=rvar_pat.findall(term)              # looking for redcap variable
        if len(matches)==1:                         # we've only got a single term so it must be in current entry
            a=paren_pat.sub('___\g<1>',matches[0]) # subsitute baby(1) = baby___1

            out_list.append(my_event[a.lower()])

        elif len(matches)==2:                       # if there are two [xxx][yyy] then we have both an event and a variable 
            for entry2 in big_data:                  # search through all of big data
                if matches[0]==entry2['redcap_event_name']:
                    a=paren_pat.sub('___\g<1>',matches[1]) # subsitute baby(1) = baby___1
                    out_list.append(entry2[a.lower()])
                    break
        else:                      
        # not a redcap variable.  Look for string argument wrapped in quotes
            
            matches=str_pat.findall(term)       # should return either 0 or 1 entries
            if len(matches)>0:
                out_list.append(matches[0])     # will strip the wrapping quotes
            
        # search for operators or paren
            elif term.strip() in operators:
                out_list.append('%$*&'+term.strip())
        
            else:
                out_list.append(term)            
            
   
    return out_list     # should tokenise


# move up the tree and find the node to insert after
# takes the current node and the precedence of the node we want to create
# if precedence of new node is even it will be inserted after a node with pfrecedence that
#    is strictly less than the new precence
# if precedence of new node is odd then new node will be inserted after the first note
#   with a precence less than or equal to new node


# return the prtecedence of the current node

def getPrec(node):
    cur_val = node.getValue()   # this will get the current precedence
    if type(cur_val) == tuple:
        cur_prec = cur_val[1]   # if node is an operator then value will be a tuple of operator,precedence
    else:
        cur_prec = 999999999    # if it's an operand then it doesn't have a precedece so force to highest 
    return cur_prec    
    
def climbTree(node,prec):
#    node.print_tree()
    cur_prec = getPrec(node)

        
    if prec % 2:                # precedence even or odd?
        while cur_prec > prec:  # odd so we want to move up until we find a node that's <=
            node = node.upTree()       # move up
            cur_prec = getPrec(node)
            
    else:                               # even so we want to find the node that's strictly less than
        while cur_prec >= prec:
            node = node.upTree()       # move up
            cur_prec = getPrec(node)    
        
    
    return node                     # will return pointer to node that we want to insert after


      
# build parse tree from expression.

def buildParseTree(fplist):
    operators = {
                'and':2,
                'or':2,
                '=':6,
                '!=':6,
                '>':6,
                '<=':6,
                '>':6,
                '<=':6,
                '*':10,
                '/':10,
                '+':8,
                '-':8,
                '^':11,
                }
    
    stack = Stack()
    left_bracket = ('(',0)          # tuple.  0 precedence - lowest
    
    TreeRoot = BinaryTree(left_bracket) # dummy an initial left bracket tuple node
    CurrentNode = TreeRoot
    
    for entry in fplist:        # loop through each symbol
#        

#        TreeRoot.print_tree()
        # first check for an operand
        
        if type(entry) != str or str(entry)[:4] !=  '%$*&' :           # we're just going to insert it below 
            CurrentNode = CurrentNode.insertBelowCross(entry) # it's going to be a leaf 



        # now check if it's an opening bracket
        
        elif entry == '%$*&('  :
            CurrentNode = CurrentNode.insertBelowCross(left_bracket)  # bracket is now on the right below old parent
            stack.push(CurrentNode)
        
        # now check for closing bracket.  If we find it we'll climb up until we find it's mate
        
        elif entry == '%$*&)' :
            CurrentNode = stack.pop()        # get opening bracket off the stack
#            CurrentNode.print_tree()
            rchild = CurrentNode.getRightChild()  # get the pointer to the downstream
            CurrentNode = CurrentNode.upTree()  # move up
            CurrentNode.right = rchild
#            CurrentNode.print_tree()           
            
        elif entry[4:] in operators:

            prec = operators[entry[4:]]     # get the precedence
            
            CurrentNode = climbTree(CurrentNode,prec)
            CurrentNode = CurrentNode.insertBelowCross((entry[4:],operators[entry[4:]]))
            
        else:
            err_str = 'entry' + entry +'cannot be processed in module buildParseTree'
            sys.exit(err_str)
        
    # made it all the way through the list.  Now snip off the initial open 
        
    CurrentNode = TreeRoot.right    # ignore initial dummy '(')
    CurrentNode.parent = None       # trash the link back to dummy node
    return CurrentNode

# evaluate parse tree.
    
def evalParseTree(parse_tree):
    operators = {
                'and':'logicAnd',
                'or':'logicOr',
                '=':'logicEq',
                '!=':'logicNE',
                '>':'logicGT',
                '>=':'logicGE',
                '<':'logicLT',
                '<=':'logicLE',
                '*':'arithMul',
                '/':'arithDiv',
                '+':'arithAdd',
                '-':'arithSub',
                '^':'arithExp'
                }   
    
    
    
    
    if not isinstance(parse_tree,BinaryTree):
        err_str = 'error: evalParseTree has been called with an argument that is not a BinaryTree'
        sys.exit(err_str)
    
    val = None  # return value
    if parse_tree.isLeaf():
        return parse_tree.getValue()            # leaf nodes should contail a value
    
    # we ought to have an operator here
    node_value = parse_tree.getValue()          # this will return a tuple
    if type(node_value) !=tuple:
        err_str = 'error: evalParseTree has found a node that ought to be an operator that is not a tuple'
        sys.exit(err_str)
    operator = node_value[0]
    if not operator in operators:
        err_str = 'error: evalParseTree has found a node that ought to be an operator that is not a tuple: '+operator
        sys.exit(err_str)   
    
    op=operators[operator]          # get the opperator routine
    left = left_arg(parse_tree)     # might be None
    right = right_arg(parse_tree)
    
    val = eval(op+'(left,right)')
    return val

def logicAnd(left,right):
    return left and right

def logicOr(left,right):
    return left or right

# test that two arguments are equal.  Returns either True or False

def logicEq(left,right):
    if left == right:
        return True
    
    # they don't match but make sure the problem isn't a type mis-match
    
    elif type(left)== type(right):      # if they're the same type and they don't match 
        return False                    # then they definately don't match
    
    elif str(left) == str(right):       # try converting both to str.  str(str)==str
        return True
      
    else:
        return False                    # gave it our best and it didn't match

# test for not equal.  Be lazy and just test for equal and negate

def logicNE(left,right):
    return not(logicEq(left,right))     

# all the logical compares will need numeric argument.  Function to ttry to
# convert strings.  Returns tuple(left,right)

def fixType(left,right):
    if type(left) == str:       # string?
        if len(left) == 0:
            return None         # warn to caller that we don't have number
        elif '.' in left:         # yes - does it have a decimal?
            left = float(left)  # yes then try to make it float
        else:
            left = int(left)    # no decimal - try to make it int
    if type(right) == str:
        if len(right) ==0:
            return None
        elif '.' in right:
            right = float(right)
        else:
            right = int(right)
    return (left,right)

# is left >= right

def logicGE(left,right):
    a = fixType(left,right)
    if a==None:
        return False
    return a[0] >= a[1]

def logicLE(left,right):
    a = fixType(left,right)
    if a==None:
        return False
    return a[0] <= a[1]

def logicGT(left,right):
    a = fixType(left,right)
    if a==None:
        return False
    a = fixType(left,right)
    return a[0] > a[1]


def logicLT(left,right):
    a = fixType(left,right)
    if a==None:
        return False
    a = fixType(left,right)
    return a[0] < a[1]

def arithMul(left,right):
    return

def arithDiv(left,right):
    return

def arithAdd(left,right):
    return

def arithSub(left,right):
    return

def arithExp(left,right):
    return


  
    
    

def left_arg(parse_tree):
    left = parse_tree.getLeftChild()
    if not left.isLeaf():                   # if it's not a leaf then call evalParseTree recursively
        return evalParseTree(left)
        
    return left.getValue()                  # if it's a leaf then just reurn it's value
        
def right_arg(parse_tree):
    right = parse_tree.getRightChild()
    if not right.isLeaf():                   # if it's not a leaf then call evalParseTree recursively
        return evalParseTree(right)
        
    return right.getValue()
    

def clean_participant(data_acc):
    if len(data_acc)==0:    # any data?
        return []          # no: return empty list
    
    # look to see if it's a void participant
    
    for r in data_acc:
        if r['redcap_event_name']=='administrative_inf_arm_1':
            if r['void_participant']=='1':
                return []           # void participant so return an empty list
            break # found the admin_info so don't keep looking
            
    # now get rig of any pilot or disabled scans
    scans =0
    for r in data_acc:
      if r['redcap_event_name'] in ['neonatal_scan_arm_1','fetal_scan_arm_1']:
            if r['scan_disabled']=='1' or r['scan_pilot'] =='1':
                data_acc.remove(r)      # get rid of it
            else:
                scans +=1           # increment the counter
                
    # if we didn't find any scans then return empty list
    
    if scans ==0:
        return []
    else:
        return data_acc
        


 ## build the metadata dictionary so we can find our variables easily
#meta_dict={} 
#i=0
#for var in meta:
#    meta_dict[var['field_name']]=i
#    i +=1
#    
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
    

def process_participant(data,meta,fem,codebook):

    for var_code in codebook:        # codebook is a list of tuples
        # kludge to deal with repeating instruments in non-repeating events
        # variables on these forms will occur in all events but will be blank in the main event 
        # record, generating errors.  A form can repeat in some events but not others and the api
        # won't tell us if a form is repeating in any event
        # can't poll the database because it's possible that there are no instances of the repeating instrument
        
        # list of forms that can be repeating and the events in which they do repeat
        is_repeat={'dna_sample':['baby_born_arm_1','18_month_assessment_arm_1'],
                   'post_scan_events':['post_scan_event_arm_1']}
        var = var_code[0]
#            print(var)
        form = var_code[1]      # this is the form name
        var_type=var_code[3]    # field type
        if var_code[19] == "Yes":
            continue
        
               
        # now we're going to loop through the form_event_table looking at each event to see if it includes this form         
        for form_event in fem:  # fem is a list of dictionaries

            if form==form_event['form']:       # we've found a reference to this variable's form
                event=form_event['unique_event_name']
                



    
    # now go find that event in the REDCap data
    # need to check that the vent name is right for this variable
    # and also that the form name matches the redcap repeat instrument
    # latter will only matter for repeating forms in non-repeating events
                for entry in data: # data is also a list of dictionaries
                    if entry['redcap_event_name']==event:       # matched the event.  now check for repeat instruments
                        if form in is_repeat:
                            elist = is_repeat[form]  # list of events in which this repeats
                            if entry['redcap_event_name'] in elist:
                                if form != entry['redcap_repeat_instrument']:
                                    continue                    # get out of here
                        elif entry['redcap_repeat_instrument'] !='':
                            continue
                        
                                
                        


                        field_value = process_fields(var,entry,meta)
                        if field_value==None:
                            sys.exit('Parser failure')
        
                        branch_str=parse_branch(var,meta,entry,data)
                        branch = True           # default is that item isn't hidden
                        if branch_str:
                            tree=buildParseTree(branch_str)
                            branch = evalParseTree(tree)
                        
                        if branch: # these are the records in which we are interested
                            if var_code[18]:
                                    
                                black_list=var_code[18].split('|')
                                if len(field_value)>0:
                                    check=field_value[0]
                                else:
                                    check = ''
                                
                                if check in black_list:
#                                        with open('dHCPmissing.txt','a',newline='') as out:
#                                            out_write=csv.writer(out,quotechar="'",delimiter='\t')
#    
#                                            out_write.writerow([entry['participationid'],entry['redcap_event_name'],\
#                                                            entry['redcap_repeat_instance'],var,\
#                                                            'Missing Value',field_value])
#                                        out = open('dHCPmissing.txt','a',newline='')
#                                        out_write=csv.writer(out,quotechar="'",delimiter='\t')
                                    out_write.writerow([entry['participationid'],entry['redcap_event_name'],\
                                                        entry['redcap_repeat_instance'],var,\
                                                        'Missing Value',field_value])

                                        
    return
        

    
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
source=infile['Working Copy']
codebook=[]                         # we're going to load the whole codebook for ease of processing


# read the codebook into memory so we don't have to keep accessing the spreadsheey 
codebook=[]                         # we're going to load the whole codebook for ease of processing
fields_of_interest=[]               # build a list of fields for the pycap import
for row in source.iter_rows(min_row=2,values_only=True):
    if row[19] != 'Yes':
        codebook.append(row)
        fields_of_interest.append(row[0])

# now get the data for this record

meta = project.export_metadata()                # metadata
fem = project.export_fem()                      # form event mappings

# export all records

big_data=project.export_records(fields=fields_of_interest,format='json')    # here's the data it'self


#big_data = sorted(big_data,key=itemgetter('participationid'))   # sort by participation id.  Shouldn't be needed

# now we need to loop through and find all the records belonging to each participant in turn and build as a subset
# we need to do this because otherise the branching logic calculations would have to loop through the whole set
# each time to find the right record

currentid = ''      # this the id that we're working on right now
data =[]            # build a list of records

#with open('dHCPmissing.txt','w',newline='') as out:
#    out_write=csv.writer(out,quotechar="'",delimiter='\t')
#    out_write.writerow(['participant','event','event_repreat','error'])

out = open('dHCPmissing.txt','w',newline='')
out_write=csv.writer(out,quotechar="'",delimiter='\t')
out_write.writerow(['participant','event','event_repeat','variable','error','value'])


   



for record in big_data:
    if record['participationid'] !=currentid :   # have we fount a new participant
        # process the records we already found
        # we're going to some garbage collection and then see if we've got anything left
        data=clean_participant(data)        # go do the garbage collection
        if len(data)>0:                     # have we got any?
            process_participant(data,meta,fem,codebook)           # yes: process them
        
      
        currentid=record['participationid']     # new participant
        data = [record]                      # start the list
    else:
        data.append(record)                    # add the record onto the list


        
data=clean_participant(data) # process the last participant


if len(data)>0:                     # have we got any?
    process_participant(data,meta,fem,codebook)           # yes: process them   

out.close() # close the output file

    


                            
                            

                            
                            
                            

        

                     
                     
                            
                            
                            
                            
#f.close
                        
                        
                        
                        

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
