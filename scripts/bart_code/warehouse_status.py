import os, sys
import argparse
from argparse import RawTextHelpFormatter
import time
from datetime import datetime

acomment = 'Hangs on Links'

helptext = '''
(may hang if links are encountered?)'

'''



gv_WH_root = '/p/user_pub/e3sm/warehouse/E3SM'

ts=datetime.now().strftime('%Y%m%d_%H%M%S')
ensem_out = 'warehouse_ensem-' + ts
paths_out = 'warehouse_paths-' + ts
stats_out = 'warehouse_status-' + ts

# vs_mode = 4  # from 'v0__' to 'v1:P'

gv_all = True
gv_empty = False
gv_nonempty = False

def assess_args():
    global gv_WH_root
    global gv_SelectionFile
    global gv_Force
    global gv_SetVers
    global gv_setstat
    global gv_Setstat
    global gv_getstat
    global gv_Getstat
    global gv_PathSpec

    parser = argparse.ArgumentParser(description=helptext, prefix_chars='-', formatter_class=RawTextHelpFormatter)
    parser._action_groups.pop()
    required = parser.add_argument_group('required arguments')
    optional = parser.add_argument_group('optional arguments')

    optional.add_argument('--all', action='store_true', dest="gv_all", required=False)
    optional.add_argument('--empty', action='store_true', dest="gv_empty", required=False)
    optional.add_argument('--nonempty', action='store_true', dest="gv_nonempty", required=False)

    args = parser.parse_args()

    ac = 0
    if args.gv_all:
        gv_all = args.gv_all
        ac += 1
    if args.gv_empty:
        gv_empty = args.gv_empty
        ac += 1
    if args.gv_nonempty:
        gv_nonempty = args.gv_nonempty
        ac += 1
    if ac > 1:
        print('ERROR:  only one of --all, --empty or gv_nonempty may be specified. Default is --all.')
        sys.exit(0)


# Generic Convenience Functions =============================

def loadFileLines(afile):
    retlist = []
    if len(afile):
        with open(afile,"r") as f:
            retlist = f.read().split('\n')
        retlist = [ _ for _ in retlist if _[:-1] ]
    return retlist

def printList(prefix,alist):
    for _ in alist:
        print(f'{prefix}{_}')

def printFileList(outfile,alist):
    stdout_orig = sys.stdout
    with open(outfile,'w') as f:
        sys.stdout = f

        for _ in alist:
            print(f'{_}',flush=True)

        sys.stdout = stdout_orig



def get_dataset_dirs_loc(anydir,loc):   # loc in ['P','W']
    global gv_WH_root
    global gv_PUB_root

    '''
        Return tuple (ensemblepath,[version_paths])
        for the dataset indicated by "anydir" whose
        "dataset_id" part identifies a dataset, and
        whose root part is warehouse or publication.
    '''

    if not loc in ['P','W']:
        logMessage('ERROR',f'invalid dataset location indicator:{loc}')
        return ''
    if not (gv_WH_root in anydir or gv_PUB_root in anydir):
        logMessage('ERROR',f'invalid dataset source path:{anydir}')
        return ''
    if gv_WH_root in anydir:
        ds_part = anydir[1+len(gv_WH_root):]
    else:
        ds_part = anydir[1+len(gv_PUB_root):]

    tpath, leaf = os.path.split(ds_part)
    if len(leaf) == 0:
        tpath, leaf = os.path.split(tpath)
    if leaf[0] == 'v' and leaf[1] in '123456789':
        tpath, leaf = os.path.split(tpath)
        if not (leaf[0:3] == 'ens' and leaf[3] in '123456789'):
            logMessage('ERROR',f'invalid dataset source path:{anydir}')
            return ''
        ens_part = os.path.join(tpath,leaf)
    elif (leaf[0:3] == 'ens' and leaf[3] in '123456789'):
        ens_part = os.path.join(tpath,leaf)
    else:
        logMessage('ERROR',f'invalid dataset source path:{anydir}')
        return ''

    if loc == 'P':
        a_enspath = os.path.join(gv_PUB_root, ens_part)
    else:
        a_enspath = os.path.join(gv_WH_root, ens_part)

    vpaths = []
    if os.path.exists(a_enspath):
        vpaths = [ f.path for f in os.scandir(a_enspath) if f.is_dir() ]      # use f.path for the fullpath
        vpaths.sort()

    return a_enspath, vpaths



# Warehouse Specific Functions ==============================


def specialize_expname(expn,reso,tune):
    if expn == 'F2010plus4k':
        expn = 'F2010-plus4k'
    if expn[0:5] == 'F2010' or expn == '1950-Control':
        if reso[0:4] == '1deg' and tune == 'highres':
            expn = expn + '-LRtunedHR'
        else:
            expn = expn + '-HR'
    return expn

def get_dsid_arch_key( dsid ):
    comps=dsid.split('.')
    expname = specialize_expname(comps[2],comps[3],comps[4])
    return comps[1],expname,comps[-1]

def get_dsid_type_key( dsid ):
    comps=dsid.split('.')
    realm = comps[-5]
    gridv = comps[-4]
    otype = comps[-3]
    freq = comps[-2]

    if realm == 'atmos':
        realm = 'atm'
    elif realm == 'land':
        realm = 'lnd'
    elif realm == 'ocean':
        realm = 'ocn'

    if gridv == 'native':
        grid = 'nat'
    elif otype == 'climo':
        grid = 'climo'
    elif otype == 'monClim':
        grid = 'climo'
        freq = 'mon'
    elif otype == 'seasonClim':
        grid = 'climo'
        freq = 'season'
    elif otype == 'time-series':
        grid = 'reg'
        freq = 'ts-' + freq
    elif gridv == 'namefile':
        grid = 'namefile'
        freq = 'fixed'
    elif gridv == 'restart':
        grid = 'restart'
        freq = 'fixed'
    else:
        grid = 'reg'
    return '_'.join([realm,grid,freq])

# dsid:  root,model,experiment.resolution. ... .realm.grid.otype.ens.vcode

def get_dsid(ensdir):
    return '.'.join(ensdir.split('/')[5:])

def get_vdirs(rootpath,mode):     # mode == "any" (default), or "empty" or "nonempty"
    selected = []
    for root, dirs, files in os.walk(rootpath):
        if not dirs:
            selected.append(root)
    if not (mode == 'empty' or mode == 'nonempty'):  # "any"
        return selected

    sel_empty = []
    sel_nonempty = []
    for adir in selected:
        for root, dirs, files in os.walk(adir):
            if files:
                sel_nonempty.append(adir)
            else:
                sel_empty.append(adir)
    if mode == 'empty':
        return sel_empty
    return sel_nonempty


def isVLeaf(_):
    if len(_) > 1 and _[0] == 'v' and _[1] in '0123456789':
        return True
    return False

def isEnsDir(_):
    if len(_) > 1 and _[0:3] == 'ens' and _[3] in '0123456789':
        return True
    return False

def countFiles(path):           # assumes only files are present if any.
    return len([f for f in os.listdir(path)])

# get ALL warehouse ensemble directories

def get_ensemble_dirs():
    vdirs = get_vdirs(gv_WH_root,"all")
    if print_paths:
        printFileList(paths_out,vdirs)
    ensemble_paths = []
    for adir in vdirs:
        ensdir, vdir = os.path.split(adir)
        ensemble_paths.append(ensdir)
    ensemble_paths = list(set(ensemble_paths))
    ensemble_paths.sort()
    return ensemble_paths

'''
DS_Status: dictionary

{ akey:
    { dkey:
        { ‘PATH’: ‘ensemble path’,
          ‘VDIR’: { dict of 'vdir': filecount, 'vdir': filecount, ...},
          ‘STAT’: [<list of (timestamp,section,statline) tuples],
          ‘COMM’: [<list of unstructured text comment lines>],
        },
      dkey:
        {
        },
      . . .
    },
  akey:
    {
    },
  . . .
}
'''

# read status file, convert lines "STAT:ts:PROCESS:status1:status2:..."
# into dictionary, key = STAT, rows are tuples (ts,'PROCESS:status1:status2:...')
# and for comments, key = COMM, rows are comment lines

def load_DatasetStatusFile(edir):
    statdict = {}
    statfile = os.path.join(edir,'.status')
    if not os.path.exists(statfile):
        return statdict
    statdict['STAT'] = []
    statdict['COMM'] = []
    statbody = loadFileLines(statfile)
    for aline in statbody:
        if aline[0:5] == 'STAT:':       # forge tuple (timestamp,residual_string), add to STAT list
            items = aline.split(':')
            tstp = items[1]
            rest = ':'.join(items[2:])
            atup = tuple([tstp,rest])
            statdict['STAT'].append(atup)
        else:
            statdict['COMM'].append(aline)

    return statdict


def load_DatasetStatus(edir):

    status = {}
    status['PATH'] = ''
    status['VDIR'] = {}         # dict of { vdir:filecount, ...}
    status['STAT'] = {}         #
    status['COMM'] = []

    # retain edir for convenience
    status['PATH'] = edir

    # collect vdirs and file counts
    for root, dirnames, filenames in os.walk(edir):
        for adir in dirnames:
            if isVLeaf(adir):
                fcount = countFiles(os.path.join(edir,adir))
                status['VDIR'][adir] = fcount

    statdict = load_DatasetStatusFile(edir)     # raw statusfile as dict { STAT: [ (ts,rest_of_line) tuples ], COMM: [ comment lines ] }

    status['STAT'] = status_breakdown(statdict['STAT'])
    status['COMM'] = statdict['COMM']

    return status

# from list [ (timestamp,'category:subcat:subcat:...') ] tuples
# return dict { category: [ (timestamp,'subcat:subcat:...') ], ... tuple-lists
# may be called on dict[category] for recursive breakdown of categories, all tuple lists sorted on their original timestamps


def load_DS_StatusList(ensdirs):
    wh_status = {}
    for edir in ensdirs:
        idval = get_dsid(edir)
        akey = get_dsid_arch_key(idval)
        dkey = get_dsid_type_key(idval)
        if not akey in wh_status:
            wh_status[akey] = {}
        wh_status[akey][dkey] = load_DatasetStatus(edir)
    return wh_status

def status_breakdown(stat_tuples):
    stat_breakdown = {}
    # get unique tuple[1] first :-split values
    categories = []
    for atup in stat_tuples:
        acat = atup[1].split(':')[0]
        categories.append(acat)
    categories = list(set(categories))
    # print(f'DEBUG breakdown cats = {categories}')
    categories.sort()
    for acat in categories:
        stat_breakdown[acat] = []
    for atup in stat_tuples:
        tstp = atup[0];
        acat = atup[1].split(':')[0]
        rest = ':'.join(atup[1].split(':')[1:])
        stat_breakdown[acat].append(tuple([tstp,rest]))

    return stat_breakdown

def dataset_print_csv( akey, dkey ):
    print(f'{akey[0]},{akey[1]},{akey[2]},{dkey}')

def get_vleaf_padded(vleaf):
    if len(vleaf) >= 4:
        vpadded = vleaf[0:4]
    elif len(vleaf) == 3:
        vpadded = vleaf[0:3] + '_'
    else:
        vpadded = vleaf[0:2] + '__'
    vroot = vleaf[0:2]

    return vroot, vpadded

def produce_status_listing_vcounts(datasets):

    statlinelist = []
    for akey in datasets.keys():
        for dkey in datasets[akey].keys():
            # print(f'DEBUG: akey,dkey = {akey},{dkey}')
            ds_status = datasets[akey][dkey]        # { 'PATH': path, 'VDIR': { vdir: filecount, ... }, 'STAT': [ statlines ], 'COMM': [ commlines ] }
            corepath = ds_status['PATH']
            if len(corepath) == 0:
                continue
            vdict = ds_status['VDIR']      # { 'v0': fcount , 'v1': fcount, ... }
            statlist = ['__________','__________','__________','__________','__________','__________']
            spos = 0
            vkeys = list(vdict.keys())
            vkeys.sort()
            for vdir in vkeys:
                vbase, vleaf = get_vleaf_padded(vdir)
                statlist[spos] = f"{vleaf}[{vdict[vdir]:4d}]"
                spos += 1
                
            statbar = f'{statlist[0]}.{statlist[1]}.{statlist[2]}.{statlist[3]}.{statlist[4]}.{statlist[5]}'
            ds_spec = f'{akey[0]},{akey[1]},{akey[2]},{dkey}'
            ds_stat_list = ds_status['STAT']
            ds_comm_list = ds_status['COMM']

            ds_warehouse = ds_stat_list['WAREHOUSE']    # [ (ts,'PROCESS:statline'), (ts,'PROCESS:statline'), ... ]
            stat_general = 'NO_STATFILE'
            if len(ds_warehouse):
                latest = ds_warehouse[-1]
                stat_general = f"{latest[0]}:{latest[1]}"

            # TEST: reconstitute status file from structures
            # if len(ds_stat_list):       # have .status file data
            #     write_status_file(adict,ds_stat_struct,ds_comm_list)

            statline = f'{ds_spec:60}|{stat_general:40}|{statbar}|{corepath}'
            # statline = f'{ds_spec}|{stat_general}|{statbar}|{corepath}'       # for CSV output from pipe-delimiters
            statlinelist.append(statline)
            
    statlinelist = list(set(statlinelist))
    statlinelist.sort()
    return statlinelist


# for testing - should be subsumed in args
print_ensem = True
print_paths = False

def main():

    assess_args()

    ensdirs = get_ensemble_dirs()
    wh_datasets = load_DS_StatusList(ensdirs)

    status_list = produce_status_listing_vcounts(wh_datasets)

    printFileList(stats_out,status_list)

    sys.exit(0)


if __name__ == "__main__":
  sys.exit(main())

