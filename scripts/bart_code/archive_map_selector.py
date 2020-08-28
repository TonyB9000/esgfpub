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
    Usage:  archive_map_selector [-h/--help] [-f/--fields | -u/--unique <fieldname> | -s/--select <fieldname>=glob[,<fieldname>=glob}*]

        Only one of (-f/--fields, -u/--unique, -s/--select) will be accepted.
        -f/--fields:               Provide the addressable fieldnames in the archive map
        -u/--unigue <fieldname>    Provide the sorted, unique values for a given field
        -s/--select csv-list       A list of field=value pairs, for which matching archive_map records are returned. 
'''

Arch_Map_File = '/p/user_pub/e3sm/archive/.cfg/Archive_Map'
fields = False
unique = False
select = False
target = ''
selection = ''

def assess_args():
    global fields
    global target
    global unique
    global select
    global selection

    parser = argparse.ArgumentParser(description=helptext, prefix_chars='-', formatter_class=RawTextHelpFormatter)
    parser._action_groups.pop()
    required = parser.add_argument_group('required arguments')
    optional = parser.add_argument_group('optional arguments')
    optional.add_argument('-f', '--fields', action='store_true', dest="fields")
    optional.add_argument('-u', '--unique', action='store', dest="target", type=str)
    optional.add_argument('-s', '--select', action='store', dest="selection", type=str)

    args = parser.parse_args()

    if not (args.fields or args.target or args.selection):
        print("Error:  One of (-f/--fields, -u/--unique, -s/--select) must be supplied.  Try -h")
        sys.exit(0)

    if args.target:
        unique = True

    if args.selection:
        select = True

    fields = args.fields
    target = args.target
    selection = args.selection


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
    
    # print(f'Sorry.  -s/--select is not yet implemented')

    if select:
        criteria = selection.split(',')
        selected = criteria_selection(Arch_Map,criteria)
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




