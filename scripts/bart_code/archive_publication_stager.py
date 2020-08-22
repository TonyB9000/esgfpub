import sys, os
import argparse
from argparse import RawTextHelpFormatter
import glob
import shutil
import subprocess
import time

#  USAGE:  archive_publication_stager.sh -A arch_path -P extract_pattern -D dest_dir [-O]"

helptext = '''
    The archive_publication_stager accepts a single archive path, a file extraction pattern (glob-style wildcards),
    a fully-qualified (faceted) publication path, and an overwrite flag, and populates the publication path from
    archive with the indicated case dataset files.  If called more than once for the same dataset (some datasets
    span multiple archives for different years), then the overwrite flag "True" allows the union of files to be
    applied.  (By default, a non-empty destination directory will not be populated and will cause an abort.)

    See: "/p/user_pub/e3sm/archive/.cfg/Archive_Map" for selection of archive path and extraction patterns for
    various experiment datasets.

    NOTE:  This process requres an environment with zstash v0.4.1 or greater.
'''

thePWD = ''

arch_path = ''
x_pattern = ''
pub_path = ''
overwrite = False

holodeck = ''
holozst = ''

def assess_args():
    global thePWD
    global arch_path
    global x_pattern
    global pub_path
    global overwrite
    global holodeck
    global holozst

    thePWD = os.getcwd()
    # parser = argparse.ArgumentParser(description=helptext, prefix_chars='-')
    parser = argparse.ArgumentParser(description=helptext, prefix_chars='-', formatter_class=RawTextHelpFormatter)
    parser._action_groups.pop()
    required = parser.add_argument_group('required arguments')
    optional = parser.add_argument_group('optional arguments')

    required.add_argument('-A', '--archive', action='store', dest="arch_path", type=str, required=True)
    required.add_argument('-P', '--pattern', action='store', dest="x_pattern", type=str, required=True)
    required.add_argument('-D', '--destdir', action='store', dest="pub_path", type=str, required=True)
    optional.add_argument('-O', '--overwrite', action='store_true', dest="overwrite", required=False)

    args = parser.parse_args()

    # sys.exit(0)

    if not (args.arch_path and args.x_pattern and args.pub_path):
        print("Error:  missing arguments (use --help for more info)")
        sys.exit(1)

    if not os.path.exists(args.arch_path):
        print("Error:  Specified archive not found: {}".format(args.arch_path))
        sys.exit(1)

    arch_path = args.arch_path
    x_pattern = args.x_pattern
    pub_path = args.pub_path
    overwrite = args.overwrite

    # deal with overwrite conflict BEFORE zstash

    if not overwrite and os.path.exists(args.pub_path):
        if os.listdir(args.pub_path) != []:
            print("Error: Given destination directory is not empty, and overwrite is not indicated")
            sys.exit(1)
        
    holodeck = os.path.join(thePWD,"holodeck-" + str(time.time()))
    holozst=os.path.join(holodeck,'zstash')

def echo_inputs():
    print("Process INPUTS:")
    print(f'    arch_path: {arch_path}')
    print(f'    x_pattern: {x_pattern}')
    print(f'    pub_path:  {pub_path}')
    print(f'    overwrite: {overwrite}')


def main():

    assess_args()

    # echo_inputs()

    zstashversion = subprocess.check_output(['zstash', 'version']).strip().decode('utf-8')
    print(f'zstash version: {zstashversion}')

    if not (zstashversion == 'v0.4.1' or zstashversion == 'v0.4.2'):
        print('ERROR: ABORTING:  zstash version is not 0.4.1 or greater, or is unavailable')
        sys.exit(1)

    # print('Producing Holodeck {} for archive {}'.format(holodeck,arch_path))

    os.mkdir(holodeck)
    os.mkdir(holozst)
    os.chdir(holodeck)

    for item in os.scandir(arch_path):
        base = item.path.split('/')[-1]         # get archive item basename
        link = os.path.join(holozst,base)       # create full link name 
        os.symlink(item.path,link)


    print("Calling: zstash ls --hpss=none {} from location {}".format(x_pattern,thePWD));
    # retval = subprocess.call(['zstash', 'ls', '--hpss=none', x_pattern])
    # retval = subprocess.call(['zstash', 'extract', '--hpss=none', x_pattern], stdout=subprocess.DEVNULL)
    retval = subprocess.call(['zstash', 'extract', '--hpss=none', x_pattern])
    if not retval == 0:
        print("ERROR:  zstash returned exitcode {}".format(retval))
        os.chdir('..')
        shutil.rmtree(holodeck,ignore_errors=True)
        sys.exit(retval)

    # print("Extraction Completed:  Files remain in Holodeck {}".format(holodeck))
    # sys.exit(0)
        
    os.makedirs(pub_path,exist_ok=True)
    os.chmod(pub_path,0o755)

    for file in glob.glob(x_pattern):
        shutil.move(file, pub_path)     # chmod 644?
        
    os.chdir('..')
    shutil.rmtree(holodeck,ignore_errors=True)

    sys.exit(0)


if __name__ == "__main__":
  sys.exit(main())

