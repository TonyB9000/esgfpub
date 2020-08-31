import sys, os
import argparse
from argparse import RawTextHelpFormatter
import glob
import shutil
import subprocess
import time


# 
def ts():
    return 'TS_' + datetime.now().strftime('%Y%m%d_%H%M%S')


helptext = '''
    Usage:  archive_map_selector [-h/--help] [-f/--fields] | [-u/--unique <fieldname>]
                    | -s/--select  <fieldname>=glob[,<fieldname>=glob]*
                    | -x/--exclude <fieldname>=glob[,<fieldname>=glob]*

        Only one of (-f/--fields, -u/--unique, (-s/--select and/or -x/--exclude) will be accepted.
        -f/--fields:               Provide the addressable fieldnames in the archive map
        -u/--unigue <fieldname>    Provide the sorted, unique values for a given field
        -s/--select csv-list       A list of field=value pairs (treated via AND) for which matching archive_map records are returned. 
        -x/--exclude csv-list      A list of field=value pairs (treated via OR)  for which matching archive_map records are excluded. 

        Example:  archive_map_selector.py -s Campaign=CRYO-v1 -x Model=1_2_1
            will return all Archive_Map lines for CRYO-v1 datasets except where Model is 1_2_1

        Issues:  The "glob" is not yet supported - field values must be given exactly.
'''

Arch_Map_File = '/p/user_pub/e3sm/archive/.cfg/Archive_Map'
fields = False
unique = False
select = False
exclude = False
target = ''
selection = ''

def assess_args():
    global fields
    global target
    global unique
    global select
    global exclude
    global selection
    global exclusion

    parser = argparse.ArgumentParser(description=helptext, prefix_chars='-', formatter_class=RawTextHelpFormatter)
    parser._action_groups.pop()
    required = parser.add_argument_group('required arguments')
    optional = parser.add_argument_group('optional arguments')
    optional.add_argument('-f', '--fields', action='store_true', dest="fields")
    optional.add_argument('-u', '--unique', action='store', dest="target", type=str)
    optional.add_argument('-s', '--select', action='store', dest="selection", type=str)
    optional.add_argument('-x', '--exclude', action='store', dest="exclusion", type=str)

    args = parser.parse_args()

    if not (args.fields or args.target or args.selection or args.exclusion):
        print("Error:  One of (-f/--fields, -u/--unique, -s/--select, -x/--exclude) must be supplied.  Try -h")
        sys.exit(0)

    if args.target:
        unique = True

    if args.selection:
        select = True

    if args.exclusion:
        exclude = True

    fields = args.fields
    target = args.target
    selection = args.selection
    exclusion = args.exclusion


am_field = ('Campaign','Model','Experiment','Ensemble','DatasetType','ArchivePath','DatasetMatchPattern')

def am_field_pos(fname):
    return am_field.index(fname)

def criteria_selection(pool,crit):
    # pool is list of tuples of positional field values
    # crit is list of 'var=val' pairs
    # use am_field.index(var) to seek value in pool tuples

    retlist = []
    for atup in pool:
        failed = False
        for acrit in crit:
            var, val = acrit.split('=')
            if not atup[am_field.index(var)] == val: # need RegExp comparison here
                failed = True
                break
        if failed:
            continue
        retlist.append(atup)

    return retlist

def criteria_exclusion(pool,crit):
    #
    retlist = []
    for atup in pool:
        skip = False
        for acrit in crit:
            var, val = acrit.split('=')
            if atup[am_field.index(var)] == val: # need RegExp comparison here
                skip = True
                break
        if skip:
            continue
        retlist.append(atup)

    return retlist

def print_csv_tuples(tup_list):
    for tup in tup_list:
        for _ in range(len(tup)):
            if _ > 0:
                print(f',{tup[_]}',end = '')
            else:
                print(f'{tup[_]}',end = '')
        print('')

def main():
    global fields
    global target
    global selection

    assess_args()

    if fields:
        for _ in am_field:
            print(f'{_}')
        sys.exit(0)

    # all other areas require reading the Archive Map

    with open(Arch_Map_File) as f:
        contents = f.read().split('\n')
    
    Arch_Map = [ tuple( _.split(',')) for _ in contents if  _[:-1]]

    if unique:
        dex = am_field.index(target)
        print(f'{target} index is {dex}')
        accum = []
        for _ in Arch_Map:
            accum.append(_[dex])
        uvals = sorted(set(accum))
        for _ in uvals:
            print(f'{_}')
        sys.exit(0)
    
    did_select = False

    if select:
        selection_criteria = selection.split(',')
        selected = criteria_selection(Arch_Map,selection_criteria)
        did_select = True

    if exclude:
        exclusion_criteria = exclusion.split(',')
        if did_select:
            selected = criteria_exclusion(selected,exclusion_criteria)
        else:
            selected = criteria_exclusion(Arch_Map,exclusion_criteria)
        
    print_csv_tuples(selected)

    sys.exit(0)

if __name__ == "__main__":
  sys.exit(main())

'''
    retlist = []
    for aline in linelist:
        failed = False
        for apatt in greplist:
            spatt = apatt + dlc
            if spatt not in aline:
                failed = True
                break
        if failed:
            continue
        retlist.append(aline)   # never failed to find grep pattern in aline

    return retlist
'''




