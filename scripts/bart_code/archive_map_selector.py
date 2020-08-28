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
target = ''
selection = ''

def assess_args():
    global fields
    global target
    global unique
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

    fields = args.fields
    target = args.target
    selection = args.selection


am_field = ('Campaign','Model','Experiment','Ensemble','DatasetType','ArchivePath','DatasetMatchPattern')

def am_field_pos(fname):
    return am_field.index(fname)

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
    
    print(f'Sorry.  -s/--select is not yet implemented')

    sys.exit(0)

if __name__ == "__main__":
  sys.exit(main())





