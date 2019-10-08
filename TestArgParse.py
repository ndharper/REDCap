# -*- coding: utf-8 -*-
"""
Created on Wed Sep 11 11:17:05 2019

Test program to play with argparse

@author: ndr15
"""
import urllib3
import sys
import os
import argparse
from redcap import Project, RedcapError
from openpyxl import Workbook, load_workbook
from openpyxl.styles import PatternFill, Border, Side, Alignment, Protection, Font
from openpyxl.worksheet.pagebreak import Break
import csv
import re

AMERICAN_DATE = False     # Assume European day-month year
"""
Project specific code.  When we read the database with PyCAP we can identify
repeating events but we can't tell whether an instrument repeats within an
event.  This is a problem because PyCap will return repeating instruments as
seperate instances of the event in which they occur.  These events will still
contain all the fields that we've asked for in the whole project.  These event
records will have redcap_repeat_instrument set to the name of the field and
redcap_repeat_instance will be non-zero.  We will also get an event record for
the part of the event that doesn't come from repeatung instruments.  To make
it even more complicated, an instrument could repeat in one event bit not in
another.  To get round this we have a hard coded dictionary that has entries
for each instrument that does repeat and values that are lists of the vents in
which they do repeat.
"""

IS_REPEAT = {'dna_sample': ['baby_born_arm_1', '18_month_assessment_arm_1'],
             'post_scan_events': ['post_scan_event_arm_1']
             }


def unpack_choices(m_ent):
    """
    function to unpack the choices of multiple choice filrds: radio, checkbox
    or dropdown.  returns a dictionary with each key being a choice value and
    the corresponding value equal to the text
    """
    result = {}
    choices = m_ent.split('|')      # break into list of choices
    for choice in choices:
        choice2 = choice.split(',', 1)   # now split the key from the value
        key = choice2[0].strip()      # clean off the blanks
        val = choice2[1].strip()
        result[key] = val
    return result


def process_fields(var, entry, meta):
    """
    function to process each filed from the dictionary and reurn its value
    Different field types reqyire different processing.  Will return a tuple
    with the f=raw value of the field and its interpretation
    """
    result = ()             # empty tuple

    for m_ent in meta:      # find the appropriate entry in the metadata
        if var == m_ent['field_name']:
            var_type = m_ent['field_type']   # get the type
            break

    result_str = ''         # accumulate result

    """ process the different field types """
    if var_type == 'checkbox':
        """
        Checkbox fields are complicated because the variable name in meta
        refers to the whole set but the returned data records will contain a
        set of values qualified by the choice.
        """
        choices = unpack_choices(m_ent['select_choices_or_calculations'])
        result_code = 0
        for key, desc in choices.items():
            result_code *= 2  # shift the result bitmap left
            var_key = var + '___' + key
            var_key = var_key.replace('-', '_')  # deal with any hyphens
            var_key = var_key.lower()

            if entry[var_key] == '1':              # is option ticked?
                result_code += 1                   # set the bit
                if len(result_str) > 0:
                    result_str = result_str + '|'
                result_str = result_str + desc

        result = result + (result_code, result_str)
        """
        returned tuple will consist of a result code and a string
        concatenation of all the selected options.  The result code is a
        bitmap where the lowest numbered option is the msb and the last
        option is the lsb.  If no options are ticked then will return (0, '')
        """
        return result

    elif var_type == 'dropdown' or var_type == 'radio':
        """
        dropdown or radio field
        """
        if entry[var] != '':      # ignore blank
            choices = unpack_choices(m_ent['select_choices_or_calculations'])
            result_str = choices[entry[var]]
            result = result + (entry[var], result_str)
        """
        returned tuple is the actual value of the variable and it's string
        description.  If the variable is empty will return empty tuple
        """
        return result

    elif var_type == 'yesno':
        if entry[var] != '':
            result = result + (entry[var],)
            if result[0] == '1':
                result = result + ('Yes',)
            else:
                result = result + ('No',)
        """ returns ('0','No') if no, ('1','Yes') if yes
        returns empty tuple if blank
        return result
        """

    elif var_type == 'truefalse':
        if entry[var] != '':
            result = result + (entry[var],)
            if result[0] == '1':
                result = result + ('True',)
            else:
                result = result + ('False',)
        """ returns ('0','False') if flase, ('1','True') if true
        returns empty tuple if blank
        return result
        """
        return result

    elif var_type == 'calc' or var_type == 'notes':
        """
        calc or notes fields.  Return tuple with just a single entry,
        value in the fields. blanks may be valid values for these fields
        """
        result = result + (entry[var],)
        return result

    elif var_type == 'text':
        """
        text can be treated differently depending on the validation type
        """
        text_type = ''
        for m_ent in meta:
            if var == m_ent['field_name']:
                text_type = m_ent['text_validation_type_or_show_slider_number']
                break

        if text_type == '' or entry[var] == '':
            """
            no validation so it's free form text.  Return as single entry
            tuple
            """
            return result + (entry[var],)

        elif text_type == 'integer':          # integer, return integer value
            result = (entry[var], int(entry[var]))
            """ return raw value and the integer equivalent"""
            return result

        elif text_type == 'number':       # float
            result = (entry[var],float(entry[var]))
            """ return raw value and the floating point equivalent"""
            return result
        
        elif text_type == 'time' :            # return times in excel decimal fraction of 24*60*60
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





def clean_participant(data_acc):
    """
    Garbage cleaning of reords for this participant.  Will get rid of void
    participants, disabled scans and, depending on flag, pilot scans.
    """
    if len(data_acc) == 0:  # any data?
        return []           # no: return empty list

    # look to see if it's a void participant
    if args.void:  # don't do this check if --VOID flag on command
        for r in data_acc:
            if r['redcap_event_name'] == 'administrative_inf_arm_1':
                if r['void_participant'] == '1':
                    return []           # return empty list
                break  # found the admin_info so don't keep looking

    # now get rig of any disabled scans
    if args.disabled:
        for r in data_acc:
            if r['redcap_event_name'] in ['neonatal_scan_arm_1',
                                          'fetal_scan_arm_1']:
                if r['scan_disabled'] == '1':
                    data_acc.remove(r)      # get rid of it

    # now the pilot scans
    if args.pilot == 0:  # default level . throw them out
        for r in data_acc:
            if r['redcap_event_name'] in ['neonatal_scan_arm_1',
                                          'fetal_scan_arm_1']:
                if r['scan_pilot'] == '1':
                    data_acc.remove(r)      # get rid of it

    # now count how many scans we have
    scans = 0
    for r in data_acc:
        if r['redcap_event_name'] in ['neonatal_scan_arm_1',
                                      'fetal_scan_arm_1']:
            scans += 1

    # and throw if we don't have any scans
    if args.noscan:
        if scans == 0:
            return []
    else:
        return data_acc


def process_participant(data, meta, fem, dictionary):
    for var in dictionary:
        form = dictionary[var]['Form Name']      # this is the form name
        var_type = dictionary[var]['Field Type']    # field type
        if dictionary[var]['Ignore']:
            continue

        # now we're going to loop through the form_event_table looking at
        # each event to see if it includes this form
        for form_event in fem:  # fem is a list of dictionaries

            if form == form_event['form']:
                event = form_event['unique_event_name']

    # now go find that event in the REDCap data
    # need to check that the event name is right for this variable
    # and also that the form name matches the redcap repeat instrument
    # latter will only matter for repeating forms in non-repeating events
                for entry in data:  # data is also a list of dictionaries
                    if entry['redcap_event_name'] == event:
                        if form in IS_REPEAT:
                            elist = IS_REPEAT[form]
                            if entry['redcap_event_name'] in elist:
                                if form != entry['redcap_repeat_instrument']:
                                    continue
                        elif entry['redcap_repeat_instrument'] != '':
                            continue

                        field_value = process_fields(var, entry, meta)
                        if field_value == None:
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
                                    check = field_value[0]
                                else:
                                    check = ''
                                
                                if check in black_list:
                                    out_write.writerow([entry['participationid'],entry['redcap_event_name'],\
                                                        entry['redcap_repeat_instance'],var,\
                                                        'Missing Value',field_value])

                                        
    return


parser = argparse.ArgumentParser(description='RedCap REST client')
parser.add_argument('--dictionary', type=str,
                    default='Codebook for Error Check.xlsx [Working Copy]',
                    help='''Dictionary file with variables to check
                    If dictionary file is an Excel workbook then specification
                    can be followed by an optional worksheet name enclosed in
                    square brackets ([]).  If no worksheet name is given then
                    the first sheet in the workbook will be used.  If file
                    does not have an extension .xlx, .xlsx, .xlsb or .xlsm
                    then it will be processed as an ordinary comma seperated
                    test file''')
parser.add_argument('--output', type=argparse.FileType('w'),
                    default='dHCPmissing.txt',
                    help='Output file')
parser.add_argument('--pilot', action='count', default=0,
                    help='''--p means include pilot scans in deciding whether
                    to processs a record but ignore any data in it.
                    --pp means process the data from pilot scans too''')
parser.add_argument('--void', action='store_false',
                    help='include void participant records')
parser.add_argument('--disabled', action='store_false',
                    help='include disabled scan records')
parser.add_argument('--noscan', action='store_false',
                    help='include records with no scans at all')
parser.add_argument('--xlimits', action='store_true',
                    help='''override maximum and minimum limits on variable
                    values in the meta data with values from the dictionary''')
parser.add_argument('records_of_interest', metavar='ID', type=str, nargs='*',
                    help='a list of subject IDs to fetch metadata from')
args = parser.parse_args()


"""
Check and see if the dictionary file is an Excel spreadsheet.  If it isn't,
assume it's a comma seperated file.  Excel file specification will be of the
form filespec.xl* optionally followed by [Worksheet]. [] are used to contain
the worksheet name beacuse those characters won't occur in the full filespec.
If no worksheet is specified then program will use the active sheet in the
workbook.
If file extension isn't .xls* then assume it's a comma seperated file with the
column headers in the first row
"""

fpat = re.compile(r'\s*(?P<file>.*xls[xmb]?)\s*(\[\s*(?P<sheet>.*)\b)')
match = fpat.match(args.dictionary)

# build the dictionay
dictionary = {}
if match:  # if we matched then it's an Excel file
    print('reading Excel File')
    # read the data dictionary
    dict_cols = {}
    infile = load_workbook(match.group('file'))
    if match.group('sheet'):
        source = infile[match.group('sheet')]
    else:
        source = infile.active
    dg = source.iter_rows(min_row=1, values_only=True)
    header = next(dg, None)
    '''
    Build a dictionary of dictionaries.  Top level uses the variable name
    from ist column as a kdictey with value equal to a dictionary of all the
    other variables in the row with each getting a key equal to the column
    heading
    '''
    ig_col = header.index('Ignore') if 'Ignore' in header else -999

    for rec in dg:
        if ig_col >= 0:
            if rec[ig_col] in ['Yes', 1, True]:
                continue
        dic_entry = {}
        for i in range(1, len(header)):
            dic_entry[header[i]] = rec[i]

        dictionary[rec[0]] = dic_entry

else:
    print('reading .csv file')
    with open(args.dictionary, 'r') as infile:
        inreader = csv.reader(infile)
        headers = next(inreader, None)
        ig_col = header.index('Ignore') if 'Ignore' in header else -999
        dictionary = {}
        for rec in inreader:
            if ig_col > 0:
                if rec[ig_col] in ['Yes', 1, True]:
                    continue
            dic_entry = {}
            for i in range(1, len(header)):
                dic_entry[header[i]] = rec[i]
            dictionary[rec[0]] = dic_entry

"""
Check date format.  We can distinguish betweem date and datetime but we don't
have any good way of distinguishing between day-month-year and month-day-year
To address scan the dictionary looking for the text validation values
We have to assume that we won't have a mixture of US and normal dates in the
same project
"""

for r in dictionary.values():
    if r['Field Type'] == 'text':
        ft = r['Text Validation Type OR Show Slider Number']
        if ft:
            if ft.find('mdy') >= 0:
                AMERICAN_DATE = True

"""
Now read the data from REDCap
May fail if we try to read to many variables from too many records
limit not hard but approx recors * variables < 1,000,000
"""
# fetch API key from ~/.redcap-key ... don't keep in the source
key_filename = os.path.expanduser('~') + '/.redcap-key'
if not os.path.isfile(key_filename):
    print('redcap key file {} not found'.format(key_filename))
    sys.exit(1)
api_key = open(key_filename, 'r').read().strip()

api_url = 'https://externalredcap.isd.kcl.ac.uk/api/'
project = Project(api_url, api_key)

fields_of_interest = list(dictionary.keys())
try:
    big_data = project.export_records(fields=fields_of_interest,
                                      records=args.records_of_interest,
                                      format='json')

except RedcapError:
    print('Redcap export too large')

meta = project.export_metadata()                # metadata
fem = project.export_fem()                      # form event mappings

"""
Main body of the program. For each partipant in turn we need to group all the
event records for that participants.  As part of that stage we will identify
items that don't need to be checked, e.g. only pilot scans, void participant.
"""
currentid = ''      # this the id that we're working on right now
data = []            # build a list of records

out = open(args.output.name, 'w', newline='')
out_write = csv.writer(out, quotechar="'", delimiter='\t')
out_write.writerow(['participant', 'event', 'event_repeat', 'variable',
                    'error', 'value'])

for record in big_data:
    if record['participationid'] != currentid:   # new participant?
        # Yes - process the collection we've accumulated
        data = clean_participant(data)        # go do the garbage collection
        if len(data) > 0:                     # have we got any?
            process_participant(data, meta, fem, dictionary)

        currentid = record['participationid']     # new participant
        data = [record]                      # start the list
    else:
        data.append(record)                    # add the record onto the list

data = clean_participant(data)  # process the last participant


if len(data)>0:                     # have we got any?
    process_participant(data,meta,fem,codebook)           # yes: process them   

out.close() # close the output file