import sys, os
import argparse
from argparse import RawTextHelpFormatter
import glob
import shutil
from subprocess import Popen, PIPE
import time
from datetime import datetime

arch_map = '/p/user_pub/e3sm/archive/.cfg/Archive_Map'

# 
helptext = '''
    usage: python publication_staging_control.py [-h/--help]
                                                 -a/--am_lines file_of_Archive_Map_selectedlines
                                                 -c/--config jobset_configfile

    The jobset_config file must contain lines:
        resolution=<res>        (where res is one of 1deg_atm_60-30km_ocean or 0_25deg_atm_18-6km_ocean)
        pubversion=<ver>        (where ver is one of v1, v2, etc)
        pub_root=<path>         (usually, /p/user_pub/e3sm/staging/prepub/)
        overwrite=<True|False>  (Boolean, allows adding files to a non-empty destination directory)

    These values must apply to every experiment/archive line listed in the file_of_Archive_Map_selectedlines.
        
'''

# job_spec
jobset_spec = ''

# file of Archive_Locator lines
AM_selected = ''

# jobset parameters

jobset = {}

def ts():
    return 'TS_' + datetime.now().strftime('%Y%m%d_%H%M%S')

def assess_args():
    global jobset_spec
    global AM_selected
    global dstype_static
    global jobset
    global timehuman

    parser = argparse.ArgumentParser(description=helptext, prefix_chars='-', formatter_class=RawTextHelpFormatter)
    parser._action_groups.pop()
    required = parser.add_argument_group('required arguments')
    optional = parser.add_argument_group('optional arguments')
    required.add_argument('-a', '--am_lines', action='store', dest="AM_selected", type=str, required=True)
    required.add_argument('-c', '--config', action='store', dest="jobset_spec", type=str, required=True)
    # optional.add_argument('--optional_arg')

    args = parser.parse_args()

    if not (args.jobset_spec and args.AM_selected):
        print(f'{ts()}: Error:  Both jobset_configfile and file_of_archive_map_lines are required. Try -h')
        sys.exit(0)

    jobset_spec = args.jobset_spec
    AM_selected = args.AM_selected

    # extract dstype_static, dstype_freq_list, resolution, pubvers, and overwriteFlag from jobset_config

    with open(jobset_spec) as f:
        contents = f.read().split('\n')

    speclist = [ _ for _ in contents if _[:-1] ]

    for _ in speclist:
        pair = _.split('=')    # each a list with two elements
        jobset[ pair[0] ] = pair[1]
        # print(f'  jobset[ {pair[0]} ] = {pair[1]}')


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

    utcStart = time.time()
    runlog = 'psc_log-' + ts()

    assess_args()

    sys.stdout = open(runlog,"w")
    sys.stderr = sys.stdout

    with open(AM_selected) as f:
        contents = f.read().split('\n')

    archlist = [ _ for _ in contents if _[:-1] ]
    archspec = {}
    arch_count = 0
    for archline in archlist:
        archspec = get_archspec(archline)
        arch_count += 1

        # must prepare: archive_publication_stager.py -A arch_path -P extract_pattern -D dest_dir [-O]

        # pub_path needs: /p/user_pub/e3sm/staging/prepub/<model>/<exper>/<resolution>/<realm>/<grid>/model-output/<freq>/<ensemble>/<pubversion>

        if len(archspec['dstyp'].split('_')) == 3:
            realmcode, grid, freq = archspec['dstyp'].split('_')
        else:
            realmcode, grid, freq1, freq2 = archspec['dstyp'].split('_')
            freq = ('_').join([freq1,freq2])

        realm = realm_longname(realmcode)
        if grid == 'nat':
            grid = 'native'

        pub_path = os.path.join(jobset['pub_root'], \
                                archspec['model'], \
                                archspec['exper'], \
                                jobset['resolution'], \
                                realm, \
                                grid, \
                                'model-output', \
                                freq, \
                                archspec['ensem'], \
                                jobset['pubversion'])

        utcS = time.time()
        print(f'{ts()}: Calling: python archive_publication_stager.py to produce {pub_path}', flush=True)

        cmd = ['python', 'archive_publication_stager.py', '-A', archspec["apath"], '-P', archspec["apatt"], '-D', pub_path, '-O']
        proc = Popen(cmd, stdout=PIPE, stderr=PIPE)       
        proc_out, proc_err = proc.communicate()
        if not proc.returncode == 0:
            print(f'{ts()}: ERROR: archive_publication_stager returned exitcode {proc.returncode}', flush=True)

        proc_out = proc_out.decode("utf-8")
        proc_err = proc_err.decode("utf-8")
        print(f'{proc_out}',flush=True)
        print(f'{proc_err}',flush=True)
        utcF = time.time()
        set_et = utcF - utcS
        print(f'{ts()}: stager ET: {set_et} seconds',flush=True)

    
    print(f'{ts()}: Completion: Processed {arch_count} archive map lines.',flush=True)
    utcFinal = time.time()
    elapsedTime = utcFinal - utcStart
    print(f'{ts()}: Elapsed Time: {elapsedTime} seconds.',flush=True)

    sys.exit(0)

if __name__ == "__main__":
  sys.exit(main())

