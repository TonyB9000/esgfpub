import sys, os
import argparse
from argparse import RawTextHelpFormatter
import glob
import shutil
import subprocess
import time
from datetime import datetime


parentName = 'WAREHOUSE'
gv_theOp = ''

# 
def ts(prefix):
    return prefix + datetime.now().strftime('%Y%m%d_%H%M%S')


helptext = '''
    The warehouse_assign utility conducts miscellaneous controller tasks involving the warehouse,
    from changing the status assignment values in the dataset ".status" files to the wholesale
    removal of directories no longer needed in the warehouse.

    Options:
        --rootpath                  Override default warehouse /p/user_pub/e3sm/warehouse/E3SM
        -w, --warehouse-paths       File of selected warehouse leaf or ensemble directories upon which to operate.
                                    (Leaf directories will be reduced to their ensemble directories)
                                    (-w is unnecessary with the -l --listpaths or -g --getstatus options)
        -l, --listpaths pathtype    List fullpath (ensembles,versions) directories under rootpath (warehouse)
        -g, --getstatus statword    Return all ensemble directories possessing the given status string.
                                    (See below for list of valid status strings)
        -s, --setstatus statstring  Append the given status string to the warehouse listing of status files
                                    (See below for list of valid status strings)
        -c, --comment commentary    Append the indicated commentaries to the warehouse listing of status files
        --adddir vX                 Add leaf directory "vX" to the listed ensembles
        --rename vX,vY              Rename the leaf directory vX to Vy for all indicated warehouse ensembles
        --remove vN                 Smart-Delete directories solely supporting the given leaf directory
                                    for the selected warehouse ensembles (empty unless --force is applied)
        --lock                      Place a ".lock" file in each of the (-w selected) ensemble directories.
        --unlock                    Remove ".lock" files from the (-w selected) ensemble directories (requires --force).
        -t, --timestamp             Override current time with YYYYMMDD_hhmmss as the timestamp for the operation.
        --setdir-nextpub            Set the highest existing version directory to the highest published directory + 1.
        --force                     Override 'hold', 'lock' and 'nostatus" dirs that prevent processing.

    Options that involve read-only (-l, --listpaths, -g, --getstatus) do not require the -w specification.
    although -w may be supplied as an additional filter.

    Some setstatus commands will be rejected unless "-f, --force" is supplied.

    THE STATUS strings:

        All status strings will be prefixed by "STAT:<ts>:<parent>:" indicating that the status change
        is a directive of some controlling workflow.  For this application, that will usually be "WAREHOUSE".

        The timestamp <ts> ifor status file entries is generated automatically, but can be overridden by
        supplying -t or --timestamp YYYYMMDD_hhmmss

        NOTE: The last component (<details>,<dirname>, etc) can be set, but are not testable by the
        -g --getstatus command.  Thus only commands like "-g Hold" or "-g VALIDATION:Returned" are useful.

        Status strings intended for Management consumption:

            Hold:<details>              Prevents further processing until Free (+ --force) is encountered
            Free:<details>              voids Hold, requires --force
            AddDir:<dirname>            added leaf directory "v#[.#]" (automatic if --add-leaf used)
            Remove:<dirname>            removed leaf directory (automatic if --remove-leaf used)
            Rename:<dirX,dirY>          renamed leaf directory vX to vY (automatic if --rename used)
            Retracted:<reason>          dataset has been retracted/reset

            [*] These operations and status updates would ordinarily be auto-coordinated by a controlling
                workflow system.

        Status string intended for major subprocess consumption: (in {VALIDATION, POSTPROCESS, PUBLICATION})

            <processname>:Hold:<details>        Prevents further processing until Free (+ --force) is encountered
            <processname>:Free:<details>        voids Hold, requires --force
            <processname>:Ready:<details>       Indicates any prerequisite processes all report "Passed".
            <processname>:Engaged:<details>     Indicates that the named process is currently active.
            <processname>:Returned:<details>    Indicates that the named process has completed.
            <processname>:Blocked:<details>     Process may not proceed, irrespective of Hold.
            <processname>:Unblocked:<details>   Process may proceed when Ready, if not under Hold.

'''

valid_status = ['Hold','Free','AddDir','Remove','Rename','Lock','Unlock','Blocked','Unblocked','Engaged','Returned','Validated','PostProcessed','Published','PublicationApproved','Retracted']
valid_subprocess = ['EXTRACTION','VALIDATION','POSTPROCESS','PUBLICATION','EVICTION']
valid_substatus  = ['Hold','Free','Ready','Blocked','Unblocked','Engaged','Returned']
status_binaries = { 'Hold':'Free', 'Free':'Hold', 'Lock':'Unlock', 'Unlock':'Lock', 'Blocked':'Unblocked', 'Unblocked':'Blocked', 'Engaged':'Returned', 'Returned':'Engaged' }

gv_WH_root = '/p/user_pub/e3sm/warehouse/E3SM'
gv_PUB_root = '/p/user_pub/work/E3SM'

def validStatus(statspec):
    items = statspec.split(':')
    if items[0] in valid_status:
        return True
    if not items[0] in valid_subprocess:
        return False
    if not items[1] in valid_substatus:
        return False
    return True

def validTimestamp(ts):
    ymd, hms = ts.split('_')
    if len(ymd) != 8 or len(hms) != 6:
        print(f'ERROR: timestamp must be in the format: YYYYMMDD_hhmmss')
        return False

    Y = int(ymd[0:4])
    M = int(ymd[4:6])
    D = int(ymd[6:8])
    if Y < 2020:
        print(f'ERROR: timestamp invalid year: {Y}')
        return False
    if M < 0 or M > 12:
        print(f'ERROR: timestamp invalid month: {M}')
        return False
    if D < 1 or D > 31:
        print(f'ERROR: timestamp invalid day: {D}')
        return False

    h = int(hms[0:2])
    m = int(hms[2:4])
    s = int(hms[4:6])
    if h < 0 or h > 23:
        print(f'ERROR: timestamp invalid hour: {h}')
        return False
    if m < 0 or h > 59:
        print(f'ERROR: timestamp invalid minute: {m}')
        return False
    if s < 0 or h > 59:
        print(f'ERROR: timestamp invalid second: {s}')
        return False

    return True

gv_PathSpec = ''    # ensembles or versions
gv_SelectionFile = ''
gv_setstat = ''
gv_getstat = ''
gv_statval = ''
gv_comment = ''
gv_timestamp = ''
gv_adddir = ''
gv_rename = ''
gv_adddir = ''
gv_setDirNextPub = False
gv_makeLock = False
gv_freeLock = False
gv_Force = False

def assess_args():
    global gv_theOp
    global gv_WH_root
    global gv_PathSpec
    global gv_SelectionFile
    global gv_setstat
    global gv_getstat
    global gv_statval
    global gv_timestamp
    global gv_adddir
    global gv_rename
    global gv_adddir
    global gv_setDirNextPub
    global gv_makeLock
    global gv_freeLock
    global gv_Force

    parser = argparse.ArgumentParser(description=helptext, prefix_chars='-', formatter_class=RawTextHelpFormatter)
    parser._action_groups.pop()
    required = parser.add_argument_group('required arguments')
    optional = parser.add_argument_group('optional arguments')

    optional.add_argument('-r', '--rootpath', action='store', dest="rootpath", type=str, required=False)
    optional.add_argument('-l', '--listpaths', action='store', dest="pathtype", type=str, required=False)
    optional.add_argument('-w', '--warehouse-paths', action='store', dest="wh_selected", type=str, required=False)
    optional.add_argument('-g', '--getstatus', action='store', dest="getstat", type=str, required=False)
    optional.add_argument('-s', '--setstatus', action='store', dest="setstat", type=str, required=False)
    optional.add_argument('-c', '--comment', action='store', dest="comment", type=str, required=False)
    optional.add_argument('-t', '--timestamp', action='store', dest="timestamp", type=str, required=False)
    optional.add_argument('--adddir', action='store', dest="adddir", type=str, required=False)
    optional.add_argument('--rename', action='store', dest="rename", type=str, required=False)
    optional.add_argument('--remove', action='store', dest="remove", type=str, required=False)
    optional.add_argument('--setdir-nextpub', action='store_true', dest="setdirnextpub", required=False)
    optional.add_argument('--lock', action='store_true', dest="lock", required=False)
    optional.add_argument('--unlock', action='store_true', dest="unlock", required=False)
    optional.add_argument('--force', action='store_true', dest="force", required=False)


    args = parser.parse_args()

    if (args.setstat or args.comment or args.adddir or args.rename or args.remove or args.unlock ) and not args.wh_selected:
        print("Error:  {setstatus,comment,adddir,rename,remove} requires a selected warehouse paths file (-w).  See -h")
        return False

    # new root?
    if args.rootpath:
        gv_WH_root = args.rootpath

    # got dir listing?
    if args.wh_selected:
        gv_SelectionFile = args.wh_selected

    if args.pathtype:
        gv_PathSpec = args.pathtype

    if args.getstat:
        gv_getstat = args.getstat

    if args.setstat:
        gv_setstat = args.setstat
        gv_theOp = 'SetStatus'

    if args.comment:
        gv_comment = args.comment
        gv_theOp = 'AddComment'

    if args.timestamp:
        if not validTimestamp(args.timestamp):
            return False
        gv_timestamp = args.timestamp

    if args.adddir:
        gv_adddir = args.adddir
        gv_theOp = 'AddDirectory'

    if args.rename:
        gv_rename = args.rename
        gv_theOp = 'RenameDirectory'

    if args.remove:
        gv_remove = args.remove
        gv_theOp = 'RemoveDirectory'

    if args.setdirnextpub:
        gv_setDirNextPub = True
        gv_theOp = 'SetDir_NextPubVersion'

    if args.lock:
        gv_makeLock = args.lock

    if args.unlock:
        if not args.force:
            print("Error:  --unlock requires --force.  See -h")
            return False
        gv_freeLock = args.unlock

    if args.force:
        gv_Force = args.force

    # valid status values?
    if gv_statval and not validStatus(gv_statval):
        print(f'ERROR: invalid status specification: {gv_statval}')
        return False

    return True


# Generic Convenience Functions =============================

def loadFileLines(afile):
    retlist = []
    if len(afile):
        with open(afile,"r") as f:
            retlist = f.read().split('\n')
        retlist = [ _ for _ in retlist if _[:-1] ]
    return retlist

def countFiles(path):           # assumes only files are present if any.
    return len([f for f in os.listdir(path)])

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

def dirLeafRename(enspath,renamespec):
    thepair = renamespec.split(',')
    oldpath = os.path.join(enspath,thepair[0])
    newpath = os.path.join(enspath,thepair[1])
    if os.path.isdir(oldpath):
        # print(f' exists: {oldpath}')
        os.rename(oldpath,newpath)

def logMessageInit(logtitle):
    global gv_logname
    gv_logname = f'{logtitle}-{ts("")}'
    open(gv_logname, 'a').close()

def logMessage(mtype,message):
    outmessage = f'{ts("TS_")}:{mtype}:{message}\n'
    with open(gv_logname, 'a') as f:
        f.write(outmessage)



# E3SM Specific Functions ==============================

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

def get_dsid(ensdir):
    return '.'.join(ensdir.split('/')[5:])

# Warehouse Specific Functions ==============================

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
        return '',[]
    if not (gv_WH_root in anydir or gv_PUB_root in anydir):
        logMessage('ERROR',f'invalid dataset source path - bad root:{anydir}')
        return '',[]
    if gv_WH_root in anydir:
        ds_part = anydir[1+len(gv_WH_root):]
    else:
        ds_part = anydir[1+len(gv_PUB_root):]

    tpath, leaf = os.path.split(ds_part)

    if len(leaf) == 0:
        tpath, leaf = os.path.split(tpath)
    if leaf[0] == 'v' and leaf[1] in '0123456789':
        ens_part = tpath
    elif (leaf[0:3] == 'ens' and leaf[3] in '123456789'):
        ens_part = ds_part
    else:
        logMessage('ERROR',f'invalid dataset source path:{anydir}')
        return '',[]

    if loc == 'P':
        a_enspath = os.path.join(gv_PUB_root, ens_part)
    else:
        a_enspath = os.path.join(gv_WH_root, ens_part)

    vpaths = []
    if os.path.exists(a_enspath):
        vpaths = [ f.path for f in os.scandir(a_enspath) if f.is_dir() ]      # use f.path for the fullpath
        vpaths.sort()

    # print(f'DEBUG: get_dataset_dirs_loc: RETURNING: a_enspath = {a_enspath}, vpaths = {vpaths}',flush=True)
    return a_enspath, vpaths


def isVLeaf(_):
    if len(_) > 1 and _[0] == 'v' and _[1] in '0123456789':
        return True
    return False

def isEnsDir(_):
    # print(f'DEBUG: isEnsDir: input = {_}',flush=True)
    if len(_) > 1 and _[0:3] == 'ens' and _[3] in '0123456789':
        return True
    return False

def getWHMaxVersion(enspath):
    epath, vpaths = get_dataset_dirs_loc(enspath,'W')
    if len(vpaths):
        apath, vleaf = os.path.split(vpaths[-1])
        return vleaf
    return ''

def getWHMaxVersionPath(enspath):
    epath, vpaths = get_dataset_dirs_loc(enspath,'W')
    if len(vpaths):
        return vpaths[-1]
    return ''

def getPubCurrVersionPath(enspath):
    epath, vpaths = get_dataset_dirs_loc(enspath,'P')
    if len(vpaths):
        return vpaths[-1]
    return ''

def getPubNextVersion(enspath):
    epath, vpaths = get_dataset_dirs_loc(enspath,'P')
    if len(vpaths) == 0:
        return 'v1'
    epath, vleaf = os.path.split(vpaths[-1])
    vmaxN = vleaf[1]
    return 'v' + str(int(vmaxN) + 1)

def getPubNextVersionPath(enspath):
    epath, vpaths = get_dataset_dirs_loc(enspath,'P')
    upver = getPubNextVersion(epath)
    return os.path.join(epath,upver)


def setWHPubVersion(enspath):
    maxwhv = getWHMaxVersion(enspath)
    pubver = getPubNextVersion(enspath)

    if len(maxwhv) and len(pubver):
        if not maxwhv == pubver:
            srcpath = os.path.join(enspath,maxwhv)
            dstpath = os.path.join(enspath,pubver)
            os.rename(srcpath,dstpath)
        return 0
    else:
        print(f'ERROR: cannot rename warehouse paths {maxwhv} to {pubver} for {enspath}')
        return 1


# get a selected subset of warehouse directories
# if given vdirs, trim to ensemble dirs, regain vdirs in later "datasets" operation.

def get_wh_selection(selection_file):
    input_Dirs = loadFileLines(selection_file)
    ensemble_paths = []
    for adir in input_Dirs:
        # print(f'DEBUG: adir = {adir}')
        trunk, tail = os.path.split(adir)
        if not len(tail):       # path ends with '/'
            adir = trunk
            trunk, tail = os.path.split(adir)
        if isEnsDir(tail):
            ensemble_paths.append(adir) # adir is ensemble dir
            continue
        if not isVLeaf(tail):
            print(f'WARNING: skipping non-ensemble or ensemble/version input directory: {adir}')
            continue
        ncode, ntail = os.path.split(trunk)
        if not isEnsDir(ntail):
            print(f'WARNING: skipping non-ensemble or ensemble/version input directory: {adir}')
            continue
        ensemble_paths.append(trunk)

    ensemble_paths.sort()

    return ensemble_paths

# get ALL warehouse ensemble directories

def get_ensemble_dirs():
    vdirs = get_vdirs(gv_WH_root,"all")
    ensemble_paths = []
    for adir in vdirs:
        ensdir, vdir = os.path.split(adir)
        ensemble_paths.append(ensdir)
    ensemble_paths = list(set(ensemble_paths))
    ensemble_paths.sort()
    return ensemble_paths

def isLocked(edir):     # cheap version for now
    lockpath = os.path.join(edir,".lock")
    if os.path.isfile(lockpath):
        return True
    return False

def setLock(edir):      # cheap version for now
    lockpath = os.path.join(edir,".lock")
    open(lockpath, 'a').close()
    
def freeLock(edir):      # cheap version for now
    lockpath = os.path.join(edir,".lock")
    os.system('rm -f ' + lockpath)
    
def setStatus(edir,statspec):
    statfile = os.path.join(edir,'.status')
    if len(gv_timestamp):
        tsval = gv_timestamp
    else:
        tsval = ts('')
    statline = f'STAT:{tsval}:{parentName}:{statspec}\n'
    with open(statfile, 'a') as f:
        f.write(statline)


         
'''
DS_Status: dictionary

{ akey:
    { dkey:
        { 'PATH': ‘ensemble path’,
          'VDIR': { dict of 'vdir': filecount, 'vdir': filecount, ...},
          'STAT': {<dict of <SECTION>: [list of (timestamp:status)... tuples],}
          'COMM': [<list of text lines>]
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



# provide "wh_status[akey][dkey]" access to each dataset statusfile info.

def load_DS_Status(ensdirs):
    wh_status = {}
    for edir in ensdirs:
        idval = get_dsid(edir)
        akey = get_dsid_arch_key(idval)        
        dkey = get_dsid_type_key(idval)        
        if not akey in wh_status:
            wh_status[akey] = {}
        status = load_DatasetStatus(edir)
        wh_status[akey][dkey] = status  # dictionary with keys PATH, VDIR, STAT, COMM
    return wh_status


def rmpath_onlyto(apath):
    '''
    remove leaf directory and all contents.
    remove all parent directories that have
    no dependents (files or directories)
    '''

    # this part makes it so a trailing '/' in the input spec won't affect things
    head, tail = os.path.split(apath)
    if tail == '':
        apath = head

    # remove leaf directory and ALL of its content
    os.system('rm -rf ' + apath)
    head, tail = os.path.split(apath)   # tail should be gone

    apath = head
    while len(apath) == 0:
        head, tail = os.path.split(apath)
        os.system('rm -rf ' + apath)
        apath = head


def filterByStatus(dlist,instat):
    # return retlist, rejects
    pass

# Given an "append-only" status history, we must take the given status and (for some)
# determine only that it exists.  For others we must determine not only that it exists,
# but that it was not subsequently countermanded by some contra-indicator (cancelled or
# superceded by a later assignment.

# stats = dictionary of [<lists of (timestamp,statline) tuples], statline = 'SECTION:status'
# query = 'SECTION:status'

def isActiveStatus(substats,query):     # substats = warehouse dictionary of [<lists of (timestamp,statline) tuples], statline = 'SECTION:status'

    testsection = query.split(':')[0]
    test_status = query.split(':')[1]

    checklist = substats[testsection]   # list of (ts,state) values for testsection

    if test_status in status_binaries:
        affirm = test_status
        deny = status_binaries[test_status]
        testlist = []
        for atup in checklist:
            if affirm in atup[1] or deny in atup[1]:
                testlist.append(atup)
        if len(testlist) == 0:
            return False
        testlist.sort()
        if affirm in testlist[-1][1]:
            return True
        return False

    # default: just test for existence

    if not test_status in valid_status:
        return False
    for atup in checklist:
        if test_status in atup[1]:
            return True

    return False


def filter_datasets_by_status(datasets,status):
    qualified = []
    for akey in datasets:
        for dkey in datasets[akey]:
            stats = datasets[akey][dkey]['STAT']        # [<list of (timestamp,section,statline) tuples]
            if len(stats):
                stat_struct = get_ds_stat_struct(stats)
                if isActiveStatus(stat_struct,parentName,status):
                    qualified.append(datasets[akey][dkey])
    return qualified
            


def main():
    global gv_Getstat

    logMessageInit('WH_AssignLog')

    if not assess_args():
        sys.exit(1)

    # easy stuff first, reads not writes
    if len(gv_PathSpec) > 0:
        if gv_PathSpec == 'versions':
            thedirs = get_vdirs(gv_WH_root,'all')
        elif gv_PathSpec == 'ensembles':
            thedirs = get_ensemble_dirs()
        printList('',thedirs)
        sys.exit(0)

    if len(gv_getstat) > 0:
        thedirs = get_ensemble_dirs()
        print(f'DEBUG: len(thedirs) = {len(thedirs)}')
        wh_datasets = load_DS_Status(thedirs)
        print(f'DEBUG: len(wh_datasets) = {len(wh_datasets)}')
        qualified = filter_datasets_by_status(wh_datasets,gv_getstat)
        qual_paths = []
        if len(qualified):
            for _ in qualified:
                qual_paths.append(_['PATH'])
        printList('',qual_paths)
        sys.exit(0)
        
    # now the mods

    # obtain list of directories to limit processing
    EnsDirs = []
    Limited = False
    if len(gv_SelectionFile) > 0:
        Limited = True
        EnsDirs = get_wh_selection(gv_SelectionFile)

    #
    # Here, we operate on each dataset "as if" it were not part of a list, so to prepare our function for "atomic" transactions.
    # Therefore, we cycle over the list of datasets, and for each we redundantly test for the indicated processing, even though
    # we know it will be the same for each dataset.

    for edir in EnsDirs:

        if gv_freeLock and gv_Force and isLocked(edir):
            freeLock(edir)
            continue
            

        if isLocked(edir):
            logMessage('WARNING',f'Dataset Locked:{edir}')
            continue

        setLock(edir)

        # check for an arbitrary rename operation
        if len(gv_rename):
            dirLeafRename(edir,gv_rename)

        # check for leaf dir rename to incremented max publication
        elif gv_setDirNextPub:
            setWHPubVersion(edir)

        # check for a status update operation
        elif len(gv_setstat):
            setStatus(edir,gv_setstat)

        logMessage('Completed',f'{gv_theOp}: {edir}')

        freeLock(edir)

    sys.exit(0)


if __name__ == "__main__":
  sys.exit(main())


'''

    # Just a test:
    for edir in EnsDirs:
        print(f' wh maxv : {getWHMaxVersion(edir)}')
        print(f' next ver: {getPubNextVersion(edir)}')

    vlist = ['v2', 'v12', 'v0', 'v0.2', 'v0.15']
    vlist.sort()
    print(f'{vlist}')
'''


'''

# ============== Special Onetime Function - Create Whole Statusfiles from Scratch using wh_startdates_e file ==================
#
# 1.  Use the touch_statfile(statfile) to have the file opened and closed
# 2.  Use the timestamp from the file to craft a "STAT:<ts>:CONTROL:EXTRACTION:Success" update
# STAT:ts:CONTROL:VALIDATION:Unblocked:
# STAT:ts:CONTROL:VALIDATION:Ready:srcdir=v0
# STAT:ts:CONTROL:POSTPROCESS:Unblocked
# STAT:ts:CONTROL:PUBLICATION:Blocked
# STAT:ts:CONTROL:PUBLICATION:Unapproved
# STAT:ts:CONTROL:CLEANUP:Blocked

def initialStatusFiles():
    global gv_timestamp
    driverfile = '/p/user_pub/e3sm/bartoletti1/Pub_Work/1_Refactor/wh_startdates_e'
    driverlines = loadFileLines(driverfile)
    for aline in driverlines:
        comps = aline.split(':')
        ts = comps[0][0:15]
        gv_timestamp = ts
        enspath = comps[1]
        statfile = os.path.join(enspath,'.status')
        print(f'ts = {ts}, statfile: {statfile}')
        setStatus(statfile,parentName,'EXTRACTION:Success:')
        setStatus(statfile,parentName,'VALIDATION:Unblocked:')
        setStatus(statfile,parentName,'VALIDATION:Ready:srcdir=v0')
        setStatus(statfile,parentName,'POSTPROCESS:Unblocked:')
        setStatus(statfile,parentName,'PUBLICATION:Blocked:')
        setStatus(statfile,parentName,'PUBLICATION:Unapproved:')
        setStatus(statfile,parentName,'EVICTION:Blocked:')

def main():

    # One Time Gig
    initialStatusFiles()
    sys.exit(0)

'''


