import sys, os
import argparse
from argparse import RawTextHelpFormatter
import glob
import shutil
import subprocess
import time
from datetime import datetime


subcommand = ''

#
def ts(prefix):
    return prefix + datetime.now().strftime('%Y%m%d_%H%M%S')



helptext = '''
    Usage:      warehouse_publish --childspec spec --enslist file_of_ensemble_paths

        childspec must be one of
                MAPFILE_GEN
                PUBLICATION:PUB_PUSH
                PUBLICATION:PUB_COMMIT

    The warehouse_publish utility is a "cover" for both publication and mapfile_generation functions
    that are cognizant of status file settings that both mitigate and record their actions.

    As this cover subsumes both WAREHOUSE and PUBLICATION activities, it will alter its identification
    in order to issue status file updates "as if" the partent or the child workflow/process.

    As "mapfile_gen" it will (presently) demand
        PUBLICATION:PUB_PUSH:Pass
        MAPFILE_GEN:Ready

    As "publish" it will look for status
        PUBLICATION:PUB_PUSH:Ready      to run the Pub_Push (file move) and exit.
        PUBLICATION:PUB_COMMIT:Ready    to move mapfile(s) to the publoop mapfiles_auto_publish

    As "warehouse" (ALWAYS) it will serve by both ensuring the proper statusfile values exist or are
    written, (faking the existence of a transition graph) so that processing can proceed properly.

    In every case, a file listing one or more warehouse ensemble paths is require as input.

 
'''

gv_WH_root = '/p/user_pub/e3sm/warehouse/E3SM'
gv_PUB_root = '/p/user_pub/work/E3SM'
gv_Mapfile_Auto_Gen = '/p/user_pub/e3sm/staging/mapfiles/mapfile_requests'
gv_Mapfile_Auto_Pub = '/p/user_pub/e3sm/staging/mapfiles/mapfiles_auto_publish'
# gv_MapGenProc = '/p/user_pub/e3sm/bartoletti1/Pub_Work/2_Mapwork/multi_mapfile_publish.sh'


gv_EnsList = ''
gv_ChildSpec = ''


def assess_args():
    global gv_EnsList
    global gv_ChildSpec

    parser = argparse.ArgumentParser(description=helptext, prefix_chars='-', formatter_class=RawTextHelpFormatter)
    parser._action_groups.pop()
    required = parser.add_argument_group('required arguments')
    optional = parser.add_argument_group('optional arguments')

    required.add_argument('--enslist', action='store', dest="wh_enslist", type=str, required=True)
    required.add_argument('--childspec', action='store', dest="wh_childspec", type=str, required=True)


    args = parser.parse_args()

    if args.wh_enslist:
        gv_EnsList = args.wh_enslist

    if args.wh_childspec:
        gv_ChildSpec = args.wh_childspec

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
    with open(outfile,'a+') as f:
        sys.stdout = f
        for _ in alist:
            print(f'{_}',flush=True)
        sys.stdout = stdout_orig

def logMessageInit(logtitle):
    global gv_logname
    gv_logname = f'{logtitle}-{ts("")}'
    open(gv_logname, 'a').close()

def logMessage(mtype,message):
    outmessage = f'{ts("TS_")}:{mtype}:{message}\n'
    with open(gv_logname, 'a') as f:
        f.write(outmessage)
        f.flush()
        os.fsync(f)

# Warehouse-Specific Functions =============================

valid_status = ['Hold','Free','AddDir','Remove','Rename','Lock','Unlock','Blocked','Unblocked','Engaged','Returned','Validated','PostProcessed','Published','PublicationApproved','Retracted']
valid_subprocess = ['EXTRACTION','VALIDATION','POSTPROCESS','MAPFILE_GEN','PUBLICATION','EVICTION']
valid_substatus  = ['Hold','Free','Ready','Blocked','Unblocked','Engaged','Returned']
status_binaries = { 'Hold':'Free', 'Free':'Hold', 'Lock':'Unlock', 'Unlock':'Lock', 'Blocked':'Unblocked', 'Unblocked':'Blocked', 'Engaged':'Returned', 'Returned':'Engaged', 'Pass':'Fail', 'Fail':'Pass' }

def isWarehouseEnsemble(edir):
    if not edir[0:len(gv_WH_root)] == gv_WH_root:
        return False
    if not edir[-4:-1] == 'ens' or not edir[-1] in '0123456789':
        return False
    if not os.path.exists(edir):
        return False
    return True

def isPublicationDirectory(pdir):
    if not pdir[0:len(gv_PUB_root)] == gv_PUB_root:
        return False
    if not pdir[-2] == 'v' or not pdir[-1] in '123456789':
        return False
    if not os.path.exists(pdir):
        return False
    return True


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

def setStatus(statfile,parent,statspec):
    tsval = ts('')
    statline = f'STAT:{tsval}:{parent}:{statspec}\n'
    with open(statfile, 'a') as f:
        f.write(statline)


def get_dsid(ensdir,src):   # src must be 'WH' (warehouse) or 'PUB' (publication) directory
    if src == 'WH':
        return '.'.join(ensdir.split(os.sep)[5:])
    elif src == 'PUB':
        return '.'.join(ensdir.split(os.sep)[4:])


# stats = dictionary of [<lists of (timestamp,statline) tuples], statline = 'SECTION:status'
# query = 'SECTION:status'

def isActiveStatus(substats,query):     # substats = warehouse dictionary of [<lists of (timestamp,statline) tuples], statline = 'SECTION:status'

    testsection = query.split(':')[0]
    test_status = query.split(':')[1]

    if not substats[testsection]:
        print(f'ERROR: substats has no section = {testsection}')
        return False

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

    if not test_status in valid_substatus:
        return False
    for atup in checklist:
        if test_status in atup[1]:
            return True

    return False


def rmpathto(apath):
    '''
    remove leaf directory and all contents.
    remove all parent directories that have
    no dependents (files or directories)
    '''

    # this part makes it so a trailing '/' won't affect things
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
    pubver = getPubNextVersion(enspath)
    maxwhv = getWHMaxVersion(enspath)

    if len(maxwhv) and len(pubver):
        if not maxwhv == pubver:
            srcpath = os.path.join(enspath,maxwhv)
            dstpath = os.path.join(enspath,pubver)
            os.rename(srcpath,dstpath)
        return 0
    else:
        print(f'ERROR: cannot rename warehouse paths {maxwhv} to {pubver} for {enspath}')
        return 1

def isPublishableMaxVersion(edir):
    vmax = getWHMaxVersion(edir)
    if int(vmax[1:]) < 1:
        return False
    return True
    

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
                vpath = os.path.join(edir,adir)
                fcount = countFiles(vpath)
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
    
def filterByStatus(dlist,instat):
    # return retlist, rejects
    pass

def pubVersion(apath):
    vers = int( apath.split(os.sep)[-1][1:2] )
    return vers

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

def trisect(A, B):
    return A-B, B-A, A&B

def conductMapfileGen(pub_path):    # pub_path is the best publishable dir, or else
    '''
        Ensure good pub_path (highest-version pub_path in pubdirs)
        Obtain edir.  Obtain dsid from edir, write pub_path into file named "mapfile_request-<dsid>"
        Place mapfile_request in mapfiles/mapfile_requests
            (It will be picked up by the Mapfile_Gen_Loop background process)
        Issue 'MAPFILE_GEN:Engaged'
    '''
    edir_w, vdirs_w = get_dataset_dirs_loc(pub_path,'W')

    # create a file in the map-publish directory containing the successful publish paths
    edir, vleaf = os.path.split(pub_path)
    statfile = os.path.join(edir_w,'.status')
    setStatus(statfile,'MAPFILE_GEN',f'Engaged:dstdir={vleaf}')

    dsid = get_dsid(edir,'PUB')
    req_file_name = f"mapfile_request-{dsid}-{ts('')}"
    req_file = os.path.join(gv_Mapfile_Auto_Gen,req_file_name)
    printFileList(req_file,[pub_path])

    setStatus(statfile,'MAPFILE_GEN',f'Queued:dstdir={vleaf}')

    return True

def conductPublication(adir,stagespec):        # cheat:  stagespec is either PUB_PUSH:Engaged, or PUB_COMMIT:Engaged
    #   Ensure a publishable version directory exists, non-empty, and a matching publication directory is not already populated
    #   Determine whther we can process PUB_PUSH or PUB_COMMIT
    #   Set PUB_<something>:Engaged:dstdir=leaf_vdir
    #   Do the work (Move the files, or the mapfiles)

    ### Now, become PUBLICATION, calling either its PUB_PUSH (to transfer files to publication) or PUB_COMMIT (to copy its mapfile to pub_loop)

    if stagespec == 'PUB_PUSH':

        edir_w, vdirs_w = get_dataset_dirs_loc(adir,'W')
        edir_p, vdirs_p = get_dataset_dirs_loc(adir,'P')

        statfile = os.path.join(edir_w,'.status')

        # Note: the warehouse max_vpath has already been set to 1 + max_pub_vpath by warehouse_assign.
        # All that the new pub_path creation involves here is to create the 
        ppath = getPubNextVersionPath(adir)
        vleaf = getWHMaxVersion(adir)
        wpath = os.path.join(edir_w,vleaf)

        wfilenames = [files for _, _, files in os.walk(wpath)][0]
        wfilenames.sort()
        wcount = len(wfilenames)
        logMessage('INFO',f'Processing: {wcount} files: {wpath}')

        setStatus(statfile,'PUBLICATION',f'PUB_PUSH:Engaged:srcdir={vleaf},filecount={wcount}')

        pcount = 0
        if os.path.exists(ppath):
            if any(os.scandir(ppath)):
                pfilenames = [files for _, _, files in os.walk(ppath)][0]
                pfilenames.sort()
                pcount = len(pfilenames)
                w_only, p_only, in_both = trisect(set(wfilenames),set(pfilenames))
                
                if( len(in_both) > 0 ):
                    logMessage('WARNING',f'Skipping warehouse path: existing destination has {len(in_both)} matching files by name')
                    logMessage('REJECTED',f'{wpath}')
                    setStatus(statfile,'PUBLICATION',f'{stagespec}:Fail:destination_file_collision')
                    return False
        else:
            ''' CREATE NEW PUBLICATION PATH HERE '''
            os.makedirs(ppath,exist_ok=True)
            os.chmod(ppath,0o775)

        broken = False
        for wfile in wfilenames:
            src = os.path.join(wpath,wfile)
            dst = os.path.join(ppath,wfile)
            try:
                shutil.move(src,dst)    # move all files, including .status and (if exists) .
            except shutil.Error:
                logMessage('WARNING',f'shutil - cannot move file: {wfile}')
                logMessage('REJECTED',f'{wpath}')
                setStatus(statfile,'PUBLICATION',f'{stagespec}:Fail:file_move_error')
                broken = True
                break
            try:
                os.chmod(dst,0o664)
            except:
                pass

        if broken:
            return False

        pfilenames = [files for _, _, files in os.walk(ppath)][0]
        pfilenames.sort()
        finalpcount = len(pfilenames)
        if not finalpcount == (pcount + wcount):
            logMessage('WARNING',f'Discrepency in filecounts:  pub_original={pcount}, pub_warehouse={wcount}, pub_final={pcount+wcount}')
            logMessage('WARNING',f'{wpath}')
            setStatus(statfile,'PUBLICATION',f'{stagespec}:Fail:bad_destination_filecount')
            return False

        logMessage('INFO',f'Moved {wcount} files to {ppath}')

        setStatus(statfile,'PUBLICATION',f'{stagespec}:Pass:dstdir={vleaf}')

        return True

    if stagespec == 'PUB_COMMIT':

        edir_w, vdirs_w = get_dataset_dirs_loc(adir,'W')
        pdir = getPubCurrVersionPath(adir)

        wfilenames = [files for _, _, files in os.walk(pdir)][0]
        wfilenames.sort()
        wcount = len(wfilenames)
        # copy the pdir's .mapfile to auto_pub/<dsid>.map
        edir_p, vleaf = os.path.split(pdir)
        dsid = get_dsid(edir_p,'PUB')
        mapfile_name = '.'.join([dsid,'map'])
        mapfile_path = os.path.join(gv_Mapfile_Auto_Pub,mapfile_name)
        # copy to mapfiles/mapfiles_auto_publish
        curr_mapfile = os.path.join(pdir,'.mapfile')
        shutil.copyfile(curr_mapfile,mapfile_path)
        
        logMessage('INFO',f'Initiated {stagespec}: {wcount} files: {pdir}')
        setStatus(statfile,'PUBLICATION',f'{stagespec}:Engaged:srcdir={vleaf},filecount={wcount}')

    return True



def main():

    assess_args()

    logMessageInit('WH_PublishLog')

    # obtain list of directories to limit processing
    EnsList = loadFileLines(gv_EnsList)

    p_rejects = []
    p_failure = []
    p_success = []

    srcdirs = EnsList

    childp = gv_ChildSpec.split(':')[0]

    if childp == "PUBLICATION":
        action = gv_ChildSpec.split(':')[1]     # may be PUB_PUSH or PUB_COMMIT

        for adir in srcdirs:

            edir_w, vdirs_w = get_dataset_dirs_loc(adir,'W')
            edir_p, vdirs_p = get_dataset_dirs_loc(adir,'P')

            statfile = os.path.join(edir_w,'.status')

            if action == 'PUB_PUSH' and (len(edir_w) == 0 or len(vdirs_w) == 0):
                logMessage('WARNING',f'Unrecognized corresponding warehouse dataset directory:{adir}')
                p_rejects.append(adir)
                continue
            if action == 'PUB_COMMIT' and (len(edir_p) == 0 or len(vdirs_p) == 0):
                logMessage('WARNING',f'Unrecognized corresponding publication dataset directory:{adir}')
                p_rejects.append(adir)
                continue
            vdirw = vdirs_w[-1]

            # is dataset locked?       
            if isLocked(edir_w) or isLocked(edir_p):
                logMessage('WARNING',f'Dataset Locked:{edir_w}')
                p_rejects.append(adir)
                continue

            if action == 'PUB_PUSH':
                setLock(edir_w)
            else:
                setLock(edir_p)

            # READ the status file
            ds_status = load_DatasetStatus(edir_w) # keys = PATH, VDIR, STAT, COMM
            stats = ds_status['STAT']
            substats = status_breakdown(stats['WAREHOUSE'])

            if action == "PUB_PUSH" and not isPublishableMaxVersion(edir_w):
                logMessage('WARNING',f'Dataset MaxVersion not publishable: {vdirw}')
                p_rejects.append(adir)
                freeLock(edir_w)
                continue

            if isActiveStatus(substats,'PUBLICATION:Blocked'):
                logMessage('WARNING',f'Dataset Publication Blocked:{vdirw}')
                p_rejects.append(adir)
                freeLock(edir)
                continue

            if action == "PUB_PUSH" and not isActiveStatus(substats,'PUBLICATION:Ready'):
                logMessage('WARNING',f'Dataset Pub_Push not Ready:{adir}')
                p_rejects.append(adir)
                freeLock(edir_w)
                continue

            # if action == "PUB_COMMIT" and not (isActiveStatus(substats,'PUB_PUSH:Pass') and isActiveStatus(substats,'MAPFILE_GEN:Pass')):
            if action == "PUB_COMMIT" and not isActiveStatus(substats,'MAPFILE_GEN:Pass'):
                logMessage('WARNING',f'Dataset Pub_Commit not Ready:{adir}')
                p_rejects.append(adir)
                freeLock(edir_p)
                continue

            ### Cheat: First, ensure we're the WAREHOUSE, engaging the PUBLICATION workflow
            setStatus(statfile,'WAREHOUSE',f'PUBLICATION:Engaged')
            if action == "PUB_COMMIT":
                setStatus(statfile,'WAREHOUSE',f'PUBLICATION:PUB_COMMIT:Ready')
            ### End Cheat


            # lets publish!
            pub_result = conductPublication(adir,action)
            # pub_result = True

            ### Cheat: Pretend we are WAREHOUSE, reporting status of PUBLICATION (so far)

            if pub_result == True:
                setStatus(statfile,'WAREHOUSE',f'PUBLICATION:{action}:Pass')
                if action == "PUB_PUSH":
                    setStatus(statfile,'WAREHOUSE',f'MAPFILE_GEN:Ready')
                p_success.append(adir)
            else:
                setStatus(statfile,'WAREHOUSE',f'PUBLICATION:{action}:Fail')
                p_failure.append(adir)

            ### End Cheat

            if action == "PUB_PUSH":
                freeLock(edir_w)
            else:
                freeLock(edir_p)

        logMessage('INFO',f'Pushed {len(p_success)} datasets to publishing')

    if childp == 'MAPFILE_GEN':
        for adir in srcdirs:
            ''' Only needed if generating mapfiles from warehouse '''
            '''
            # valid warehouse ensemble directory?
            if not isWarehouseEnsemble(adir):
                logMessage('WARNING',f'Not a warehouse ensemble directory:{adir}')
                p_rejects.append(adir)
                continue
            # is dataset locked?       
            if isLocked(adir):
                logMessage('WARNING',f'Dataset Locked:{adir}')
                p_rejects.append(adir)
                continue

            setLock(adir)
            '''

            edir_w, vdirs_w = get_dataset_dirs_loc(adir,'W')
            edir_p, vdirs_p = get_dataset_dirs_loc(adir,'P')

            statfile = os.path.join(edir_w,'.status')

            # READ the status file
            ds_status = load_DatasetStatus(edir_w) # keys = PATH, VDIR, STAT, COMM
            stats = ds_status['STAT']
            substats = status_breakdown(stats['WAREHOUSE'])

            if isActiveStatus(substats,'MAPFILE_GEN:Blocked'):
                logMessage('WARNING',f'Dataset Mapfile_Gen Blocked:{edir_w}')
                p_rejects.append(adir)
                # freeLock(adir) # for now, only for warehouse dirs
                continue

            if not isActiveStatus(substats,'MAPFILE_GEN:Ready'):
                logMessage('WARNING',f'Dataset Mapfile_Gen not Ready:{adir}')
                p_rejects.append(adir)
                # freeLock(adir) # for now, only for warehouse dirs
                continue

            ### Cheat: First, ensure we're the WAREHOUSE, engaging the MAPFILE_GEN workflow
            setStatus(statfile,'WAREHOUSE',f'MAPFILE_GEN:Engaged')
            ### End Cheat

            # Generate a Mapfile
            pdir = vdirs_p[-1]
            mapgen_result = conductMapfileGen(pdir)

            ### Cheat: Pretend we are WAREHOUSE, reporting status of MAPFILE_GEN (so far)

            if mapgen_result == True:
                setStatus(statfile,'WAREHOUSE',f'MAPFILE_GEN:Queued:')
                p_success.append(adir)
            else:
                setStatus(statfile,'WAREHOUSE',f'MAPFILE_GEN:Failure:')
                p_failure.append(adir)

            ### End Cheat

            # freeLock(adir) # for now, only for warehouse dirs

        logMessage('INFO',f'Queued {len(p_success)} datasets to background mapfile_gen_loop (mapfiles/mapfile_requests)')


    logMessage('INFO',f'{childp}:Reject Datasets: {len(p_rejects)}')
    printList('',p_rejects)
    logMessage('INFO',f'{childp}:Failed Datasets: {len(p_failure)}')
    printList('',p_failure)
    logMessage('INFO',f'{childp}:Passed Datasets: {len(p_success)}')
    printList('',p_success)

    sys.exit(0)


if __name__ == "__main__":
  sys.exit(main())




# ==== save this test ==== 

'''
for adir in EnsList:
    edir_w, vdirs_w = get_dataset_dirs_loc(adir,'W')
    print(f'DEBUG_TEST:get_dataset_dirs_loc W')
    print(f'DEBUG_TEST:    inpath =  {adir}')
    print(f'DEBUG_TEST:    edir_w =  {edir_w}')
    print(f'DEBUG_TEST:    vdirs_w = {vdirs_w}')
sys.exit(0)
'''

