import sys, os
import argparse
from argparse import RawTextHelpFormatter
import glob
import shutil
from subprocess import Popen, PIPE, check_output
import time
from datetime import datetime

#  USAGE:  archive_publication_stager.sh -A arch_path -P extract_pattern -D dest_dir [-O]"

helptext = '''
    Usage:  archive_dataset_extractor -a am_specfile [-d dest_diri] [-O]

    The archive_dataset_extractor accepts a file containing a single Archive_Map specification line, and
    a destination directory to receive the extracted dataset files.  If -O (allow overwite) is given, the
    existence of a non-empty destination directory will not deter extraction. if '-d dest_dir' is not
    given, only the list of files that would have been extracted is produced.

    See: "/p/user_pub/e3sm/archive/.cfg/Archive_Map" for dataset selection specification lines.

    NOTE:  This process requres an environment with zstash v0.4.1 or greater.
'''

AM_Specfile = ''
thePWD = ''

arch_path = ''
x_pattern = ''
dest_path = ''
overwrite = False

holodeck = ''
holozst = ''

def ts():
    return 'TS_' + datetime.now().strftime('%Y%m%d_%H%M%S')


def assess_args():
    global AM_Specfile
    global dest_path
    global thePWD

    thePWD = os.getcwd()
    # parser = argparse.ArgumentParser(description=helptext, prefix_chars='-')
    parser = argparse.ArgumentParser(description=helptext, prefix_chars='-', formatter_class=RawTextHelpFormatter)
    parser._action_groups.pop()
    required = parser.add_argument_group('required arguments')
    optional = parser.add_argument_group('optional arguments')

    required.add_argument('-a', '--am_spec', action='store', dest="AM_Specfile", type=str, required=True)
    optional.add_argument('-d', '--destdir', action='store', dest="dest_path", type=str, required=False)
    optional.add_argument('-O', '--overwrite', action='store_true', dest="overwrite", required=False)

    args = parser.parse_args()

    AM_Specfile = args.AM_Specfile
    dest_path = args.dest_path
    overwrite = args.overwrite

    # deal with overwrite conflict BEFORE zstash

    if args.dest_path and not overwrite and os.path.exists(args.dest_path):
        if os.listdir(args.dest_path) != []:
            print("Error: Given destination directory is not empty, and overwrite is not indicated")
            sys.exit(1)
        


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
    return archspec

def main():

    assess_args()

    zstashversion = check_output(['zstash', 'version']).decode('utf-8').strip()
    # print(f'zstash version: {zstashversion}')

    if not (zstashversion == 'v0.4.1' or zstashversion == 'v0.4.2'):
        print(f'{ts()}: ERROR: ABORTING:  zstash version [{zstashversion}] is not 0.4.1 or greater, or is unavailable', flush=True)
        sys.exit(1)

    with open(AM_Specfile) as f:
        contents = f.read().split('\n')

    am_line = contents[0]
    am_spec = get_archspec(am_line)
    arch_path = am_spec['apath']
    x_pattern = am_spec['apatt']

    holodeck = os.path.join(thePWD,"holodeck-" + ts() )
    holozst = os.path.join(holodeck,'zstash')

    
    # print(f'Producing Holodeck {holodeck} for archive {iarch_path}')
    print(f'{ts()}: Extraction: Calling: zstash ls --hpss=none {x_pattern} from location {thePWD}', flush=True)


    # create the Holodeck
    os.mkdir(holodeck)
    os.mkdir(holozst)
    os.chdir(holodeck)

    # create the symlinks
    for item in os.scandir(arch_path):
        base = item.path.split('/')[-1]         # get archive item basename
        link = os.path.join(holozst,base)       # create full link name 
        os.symlink(item.path,link)

    # call zstash
    if not dest_path:
        cmd = ['zstash', 'ls', '--hpss=none', x_pattern]
    else:
        cmd = ['zstash', 'extract', '--hpss=none', x_pattern]
    proc = Popen(cmd, stdout=PIPE, stderr=PIPE)
    proc_out, proc_err = proc.communicate()
    if not proc.returncode == 0:
        print(f'{ts()}: ERROR: zstash returned exitcode {proc.returncode}', flush=True)
        os.chdir('..')
        shutil.rmtree(holodeck,ignore_errors=True)
        sys.exit(retval)

    proc_out = proc_out.decode('utf-8')
    proc_err = proc_err.decode('utf-8')
    print(f'{proc_out}',flush=True)
    print(f'{proc_err}',flush=True)

    if dest_path:
        os.makedirs(dest_path,exist_ok=True)
        os.chmod(dest_path,0o775)

        for file in glob.glob(x_pattern):
            shutil.move(file, dest_path)     # chmod 664?
        
        print(f'{ts()}: Extraction Completed to {dest_path}', flush=True)

    os.chdir('..')
    shutil.rmtree(holodeck,ignore_errors=True)

    print(f'{ts()}: Process Completed, holodeck removed.', flush=True)

    sys.exit(0)


if __name__ == "__main__":
  sys.exit(main())

