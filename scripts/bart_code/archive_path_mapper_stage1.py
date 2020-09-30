import sys, os
import argparse
from argparse import RawTextHelpFormatter
import glob
import shutil
from subprocess import Popen, PIPE, check_output
import time
from datetime import datetime

helptext = '''
    Usage:  archive_path_mapper -a al_listfile

    The archive_path_mapper accepts a file containing one or more Archive_Locator specification line, and

    See: "/p/user_pub/e3sm/archive/.cfg/Archive_Locator" for archive selection specification lines.

    NOTE:  This process requires an environment with zstash v0.4.1 or greater.
'''

the_SDEP = '/p/user_pub/e3sm/archive/.cfg/Standard_Datatype_Extraction_Patterns'

WorkDir = '/p/user_pub/e3sm/bartoletti1/Pub_Status/ArchivePathMapper/'
PathsFound = os.path.join(WorkDir,'PathsFound')

holodeck = os.path.join(WorkDir,'Holodeck')
holozst = os.path.join(holodeck,'zstash')


AL_Listfile = ''
thePWD = ''

arch_path = ''
x_pattern = ''


def ts():
    return 'TS_' + datetime.now().strftime('%Y%m%d_%H%M%S')


def assess_args():
    global AL_Listfile
    global thePWD

    thePWD = os.getcwd()
    # parser = argparse.ArgumentParser(description=helptext, prefix_chars='-')
    parser = argparse.ArgumentParser(description=helptext, prefix_chars='-', formatter_class=RawTextHelpFormatter)
    parser._action_groups.pop()
    required = parser.add_argument_group('required arguments')
    optional = parser.add_argument_group('optional arguments')

    required.add_argument('-a', '--al_spec', action='store', dest="AL_Listfile", type=str, required=True)

    args = parser.parse_args()

    AL_Listfile = args.AL_Listfile




def get_al_spec(specline):
    archvals = specline.split(',')
    aspec = {}
    aspec['campa'] = archvals[0]
    aspec['model'] = archvals[1]
    aspec['exper'] = archvals[2]
    aspec['ensem'] = archvals[3]
    aspec['apath'] = archvals[4]
    return aspec

def get_sdep_spec(specline):
    sdepvals = specline.split(',')
    aspec = {}
    aspec['dtype'] = sdepvals[0].replace(' ','_')
    aspec['spatt'] = sdepvals[1]
    aspec['clist'] = sdepvals[2].split(' ')
    return aspec


def main():

    assess_args()

    zstashversion = check_output(['zstash', 'version']).decode('utf-8').strip()
    # print(f'zstash version: {zstashversion}')

    if not (zstashversion == 'v0.4.1' or zstashversion == 'v0.4.2'):
        print(f'{ts()}: ERROR: ABORTING:  zstash version [{zstashversion}] is not 0.4.1 or greater, or is unavailable', flush=True)
        sys.exit(1)

    # move previous path-finds to 

    pathsFound = os.path.join(thePWD,'PathsFound')
    shutil.rmtree(pathsFound,ignore_errors=True)
    os.makedirs(pathsFound)

    # process each archive location

    with open(AL_Listfile) as f:
        al_contents = f.read().split('\n')

    with open(the_SDEP) as f:
        sdep_contents = f.read().split('\n')

    ALE = 0

    al_linelist = [ al_line for al_line in al_contents if al_line[:-1] ]
    for al_line in al_linelist:
        # print(f'{al_line}')
        al_spec = get_al_spec(al_line)
        arch_path = al_spec['apath']
        if arch_path == 'NAV':
            continue
        
        # create SDEP subset specific to this Campaign
        sdep_list = [ sdep_line for sdep_line in sdep_contents if sdep_line[:-1] ]
        sdep_selected = []      # a list of dictionaries
        for sdep_line in sdep_list:
            sdep_spec = get_sdep_spec(sdep_line)
            # print(f"{sdep_spec['dtype']}, {sdep_spec['spatt']}, {sdep_spec['clist']}")
            if sdep_spec['spatt'] == 'ignore':
                continue
            if al_spec['campa'] not in sdep_spec['clist']:      # al_list campaign MUST be in sdep campaign list
                continue
            sdep_selected.append(sdep_spec)

        # for adict in sdep_selected:
        #    print(f' DICT = {adict}')


        ALE += 1

        basetag = ':'.join([al_spec['campa'],al_spec['model'],al_spec['exper'],al_spec['ensem']])

        # prepare the Holodeck
        if os.path.exists(holodeck):
            shutil.rmtree(holodeck,ignore_errors=True)
        os.mkdir(holodeck)
        os.mkdir(holozst)
        os.chdir(holodeck)

        # create the symlink to index.db only
        link = os.path.join(holozst,'index.db')
        targ = os.path.join(arch_path,'index.db')
        os.symlink(targ,link)

        for adict in sdep_selected:
            dstitle = adict['dtype']
            ds_patt = adict['spatt']
            outfile = ':'.join([str(ALE),basetag,dstitle,arch_path])
            
            # call zstash
            cmd = ['zstash', 'ls', '--hpss=none', ds_patt]
            proc = Popen(cmd, stdout=PIPE, stderr=PIPE)
            proc_out, proc_err = proc.communicate()
            if not proc.returncode == 0:
                print(f'{ts()}: ERROR: zstash returned exitcode {proc.returncode}', flush=True)
                os.chdir('..')
                sys.exit(proc.returncode)

            proc_out = proc_out.decode('utf-8')
            proc_err = proc_err.decode('utf-8')
            # print(f'{proc_out}',flush=True)
            if len(proc_err) > 0:
                print(f'{proc_err}',flush=True)

            outpath = os.path.join(PathsFound,outfile)
            f = open(outpath,"w")
            f.write(proc_out)

        os.chdir('..')


    sys.exit(0)


if __name__ == "__main__":
  sys.exit(main())

