import sys, os
import argparse
from argparse import RawTextHelpFormatter
import glob
import shutil
import subprocess
import time
from pathlib import Path


# 
def ts():
    return 'TS_' + datetime.now().strftime('%Y%m%d_%H%M%S')


helptext = '''
    usage:  python archive_map_to_dsid -i file_of_archive_map_lines [--names | --files] [--prefix]

    For each archive_map line of the input file, the corresponding dataset_id (dsid) is generated.
    If "--names" is given, the dataset ids are simply printed to stdout.
    If "--files" (default) is given each constructed dsid becomes a filename, with optional prefix,
    populated with all archive_map lines the result in the same dsid.

    For instance:

        python archive_map_to_dsid -i file_of_archive_map_lines --prefix extraction_request-

    will produce as output the files needed to supply to the archive_extraction_loop process
    input queue,

        /p/user_pub/e3sm/archive/.extraction_requests/

'''

gv_names = False
gv_files = True
gv_input = ''
gv_prefx = ''

def assess_args():
    global gv_names
    global gv_files
    global gv_input
    global gv_prefx

    parser = argparse.ArgumentParser(description=helptext, prefix_chars='-', formatter_class=RawTextHelpFormatter)
    parser._action_groups.pop()
    required = parser.add_argument_group('required arguments')
    optional = parser.add_argument_group('optional arguments')
    required.add_argument('-i', '--input', action='store', dest="input", type=str, required=True)
    optional.add_argument('-f', '--files', action='store_true', dest="files", required=False)
    optional.add_argument('-n', '--names', action='store_true', dest="names", required=False)
    optional.add_argument('-p', '--prefix', action='store', dest="prefx", type=str, required=False)

    args = parser.parse_args()

    if (args.files and args.names):
        print("Error:  Only one of --files or --names may be supplied. Try -h")
        return False

    if args.names:
        gv_names = True
        gv_files = False

    gv_input = args.input
    
    if args.prefx:
        gv_prefx = args.prefx

    return True

# Generic Convenience Functions =============================

def load_file_lines(file_path):
    if not file_path:
        return list()
    file_path = Path(file_path)
    if not file_path.exists() or not file_path.is_file():
        raise ValueError(f"file at path {file_path.resolve()} either doesnt exist or is not a regular file")
    with open(file_path, "r") as instream:
        retlist = [[i for i in x.split('\n') if i].pop() for x in instream.readlines() if x[:-1]]
    return retlist

def print_list(prefix, items):
    for x in items:
        print(f'{prefix}{x}')

def print_file_list(outfile, items):
    with open(outfile, 'w') as outstream:
        for x in items:
            outstream.write(f"{x}\n")

def file_append_line(afile,aline):
    outline = aline
    if not aline[-1] == '\n':
        outline = f'{aline}\n' 
    with open(afile, 'a') as f:
        f.write(outline)

def get_archspec(archline):
    archvals = archline.split(',')
    archspec = {}
    archspec['campa'] = archvals[0]
    archspec['model'] = archvals[1]
    archspec['exper'] = archvals[2]
    archspec['ensem'] = archvals[3]
    archspec['dstyp'] = archvals[4]
    archspec['apath'] = archvals[5]
    archspec['apatt'] = archvals[6]

    if 'ne120' in archspec['apath']:
        archspec['resol'] = '0_25deg_atm_18-6km_ocean'
    else:
        archspec['resol'] = '1deg_atm_60-30km_ocean'

    return archspec

def get_dsid_via_archline(archline):
    archspec = get_archspec(archline)

    if len(archspec['dstyp'].split('_')) == 3:
        realmcode, grid, freq = archspec['dstyp'].split('_')
    else:
        realmcode, grid, freq1, freq2 = archspec['dstyp'].split('_')
        freq = ('_').join([freq1,freq2])

    realm = realm_longname(realmcode)
    if grid == 'nat':
        grid = 'native'

    dsid = '.'.join(['E3SM', \
                    archspec['model'], \
                    archspec['exper'], \
                    archspec['resol'], \
                    realm, \
                    grid, \
                    'model-output', \
                    freq, \
                    archspec['ensem']])

    return dsid


def realm_longname(realmcode):
    ret = realmcode
    if realmcode == 'atm':
        ret = 'atmos'
    elif realmcode == 'lnd':
        ret = 'land'
    elif realmcode == 'ocn':
        ret = 'ocean'

    return ret


def main():

    if not assess_args():
        sys.exit(1)

    am_lines = load_file_lines(gv_input)

    for aline in am_lines:

        dsid = get_dsid_via_archline(aline)
    
        if gv_names:
            print(f'{gv_prefx}{dsid}')
            continue

        fname = f'{gv_prefx}{dsid}'
        file_append_line(fname,aline)

    sys.exit(0)

if __name__ == "__main__":
  sys.exit(main())





