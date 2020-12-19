import sys, os
import argparse
from argparse import RawTextHelpFormatter
import glob
import shutil
import subprocess
import time
from datetime import datetime


parentName = 'WAREHOUSE'
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

def setStatus(edir,statspec):
    statfile = os.path.join(edir,'.status')
    tsval = ts('')
    statline = f'STAT:{tsval}:{parentName}:{statspec}\n'
    with open(statfile, 'a') as f:
        f.write(statline)

def get_dsid(ensdir,src):   # src must be 'WH' (warehouse) or 'PUB' (publication) directory
    if src == 'WH':
        return '.'.join(ensdir.split('/')[5:])
    elif src == 'PUB':
        return '.'.join(ensdir.split('/')[4:])


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


def isVLeaf(_):
    if len(_) > 1 and _[0] == 'v' and _[1] in '0123456789':
        return True
    return False

def getWHMaxVersion(enspath):
    if not gv_WH_root in enspath:
        print(f'ERROR:getWHMaxVersion:Not a valid warehouse path: {enspath}')
        return ''
    if not os.path.isdir(enspath):
        print(f'ERROR:getWHMaxVersion:Not a current warehouse path: {enspath}')
        return ''
    else:
        vleafs = [ f.name for f in os.scandir(enspath) if f.is_dir() ]      # use f.path for the fullpath
        vleafs.sort()
        vmax = vleafs[-1]
        return vmax

def getWHMaxVersionPath(enspath):
    vmax = getWHMaxVersion(enspath)
    if not len(vmax):
        return ''
    wh_version_dir = os.path.join(enspath,vmax)
    return wh_version_dir

def getPubCurrVersionPath(enspath):
    # trim enspath to id_path if not already (trim off WH_path_root)
    if not gv_WH_root in enspath:
        print(f'ERROR:getPubNextVersion:Not a valid warehouse path: {enspath}')
        return ''
    idpath = enspath[1+len(gv_WH_root):]
    pubtestpath = os.path.join(gv_PUB_root,idpath)
    # print(f'pubtestpath: {pubtestpath}')
    if not os.path.isdir(pubtestpath):
        return ''
    else:
        vpaths = [ f.path for f in os.scandir(pubtestpath) if f.is_dir() ]      # use f.path for the fullpath
        vpaths.sort()
        return vpaths[-1]

def getPubNextVersion(enspath):
    # trim enspath to id_path if not already (trim off WH_path_root)
    if not gv_WH_root in enspath:
        print(f'ERROR:getPubNextVersion:Not a valid warehouse path: {enspath}')
        return ''
    idpath = enspath[1+len(gv_WH_root):]
    pubtestpath = os.path.join(gv_PUB_root,idpath)
    # print(f'pubtestpath: {pubtestpath}')
    if not os.path.isdir(pubtestpath):
        return 'v1'
    else:
        vleafs = [ f.name for f in os.scandir(pubtestpath) if f.is_dir() ]      # use f.path for the fullpath
        vleafs.sort()
        vmaxN = vleafs[-1][1]
        return 'v' + str(int(vmaxN) + 1)

def setWHPubVersion(enspath):
    pubver = getPubNextVersion(enspath)
    maxwhv = getWHMaxVersion(enspath)

    if len(pubver) and len(maxwhv):
        srcpath = os.path.join(enspath,maxwhv)
        dstpath = os.path.join(enspath,pubver)
        os.rename(srcpath,dstpath)
    else:
        print(f'ERROR: cannot rename warehouse paths {maxwhv} to {pubver} for {enspath}')

def isPublishableMaxVersion(edir):
    vmax = getWHMaxVersion(edir)
    if int(vmax[1:]) < 1:
        return False
    return True
    
def get_statusfile_dir(apath):
    global gv_WH_root
    global gv_PUB_root

    ''' Take ANY inputpath.
        Reject if not begin with either warehouse_root or publication_root
        Reject if not a valid version dir or ensemble dir.
        Trim to ensemble directory, and trim to dataset_part ('E3SM/...').
        Determine if ".status" exists under wh_root/dataset_part or pub_root/dataset_part.
        Reject if both or neither, else return full path (root/dataset_part)
    '''
    if not (gv_WH_root in apath or gv_PUB_root in apath):
        logMessage('ERROR',f'invalid dataset source path:{apath}')
        return ''
    if gv_WH_root in apath:
        ds_part = apath[1+len(gv_WH_root):]
    else:
        ds_part = apath[1+len(gv_PUB_root):]

    # logMessage('DEBUG',f'ds_part  = {ds_part}')

    tpath, leaf = os.path.split(ds_part)
    if len(leaf) == 0:
        tpath, leaf = os.path.split(tpath)
    if leaf[0] == 'v' and leaf[1] in '123456789':
        tpath, leaf = os.path.split(tpath)
        if not (leaf[0:3] == 'ens' and leaf[3] in '123456789'):
            logMessage('ERROR',f'invalid dataset source path:{apath}')
            return ''
        ens_part = os.path.join(tpath,leaf)
    elif (leaf[0:3] == 'ens' and leaf[3] in '123456789'):
        ens_part = os.path.join(tpath,leaf)
    else:
        logMessage('ERROR',f'invalid dataset source path:{apath}')
        return ''
    wpath = os.path.join(gv_WH_root, ens_part, '.status')
    ppath = os.path.join(gv_PUB_root, ens_part, '.status')
    # logMessage('DEBUG',f'gv_WH_root  = {gv_WH_root}')
    # logMessage('DEBUG',f'gv_PUB_root = {gv_PUB_root}')
    # logMessage('DEBUG',f'wpath = {wpath}')
    # logMessage('DEBUG',f'ppath = {ppath}')
    in_w = os.path.exists(wpath)
    in_p = os.path.exists(ppath)
    if not (in_w or in_p):
        logMessage('ERROR',f'status file not found in warehouse or publication:{apath}')
        return ''
    if in_w and in_p:
        logMessage('ERROR',f'status file found in both warehouse and publication:{apath}')
        return ''
    if in_w:
        return os.path.join(gv_WH_root, ens_part)
    return os.path.join(gv_PUB_root, ens_part)


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
    
def filterByStatus(dlist,instat):
    # return retlist, rejects
    pass

def pubVersion(apath):
    vers = int( apath.split('/')[-1][1:2] )
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

    # create a file in the map-publish directory containing the successful publish paths
    edir, vleaf = os.path.split(pub_path)
    dsid = get_dsid(edir,'PUB')
    req_file_name = f'mapfile_request-{dsid}'
    req_file = os.path.join(gv_Mapfile_Auto_Gen,req_file_name)
    printFileList(req_file,[pub_path])

    return True

def conductPublication(adir,stagespec):        # cheat:  stagespec is either PUB_PUSH:Engaged, or PUB_COMMIT:Engaged
    #   Ensure a publishable version directory exists, non-empty, and a matching publication directory is not already populated
    #   Determine whther we can process PUB_PUSH or PUB_COMMIT
    #   Set PUB_<something>:Engaged:dstdir=leaf_vdir
    #   Do the work (Move the files, or the mapfiles)

    ### Now, become PUBLICATION, calling either its PUB_PUSH (to transfer files to publication) or PUB_COMMIT (to copy its mapfile to pub_loop)

    parentName = 'PUBLICATION'

    if stagespec == 'PUB_PUSH:Engaged':

        edir = adir
        ppath = getPubCurrVersionPath(edir)
        vleaf = getWHMaxVersion(edir)
        wpath = os.path.join(edir,vleaf)

        wfilenames = [files for _, _, files in os.walk(wpath)][0]
        wfilenames.sort()
        wcount = len(wfilenames)
        logMessage('INFO',f'Processing: {wcount} files: {wpath}')

        setStatus(edir,f'PUB_PUSH:Engaged:srcdir={vleaf},filecount={wcount}')

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
                    setStatus(edir,f'PUB_PUSH:Fail:destination_file_collision')
                    return False
        else:
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
                setStatus(edir,f'PUB_PUSH:Fail:file_move_error')
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
            setStatus(edir,f'PUB_PUSH:Fail:bad_destination_filecount')
            return False

        logMessage('INFO',f'Moved {wcount} files to {ppath}')

        setStatus(edir,f'PUB_PUSH:Pass')

    if stagespec == 'PUB_COMMIT:Engaged':

        pdir = adir

        wfilenames = [files for _, _, files in os.walk(pdir)][0]
        wfilenames.sort()
        wcount = len(wfilenames)
        # copy the pdir's .mapfile to auto_pub/<dsid>.map
        edir, vleaf = os.path.split(pdir)
        dsid = get_dsid(edir,'PUB')
        mapfile_name = '.'.join([dsid,'map'])
        mapfile_path = os.path.join(gv_Mapfile_Auto_Pub,mapfile_name)
        # copy to mapfiles/mapfiles_auto_publish
        curr_mapfile = os.path.join(pdir,'.mapfile')
        shutil.copyfile(curr_mapfile,mapfile_path)
        
        logMessage('INFO',f'Initiated Pub_Commit: {wcount} files: {pdir}')
        setStatus(edir,f'PUB_COMMIT:Engaged:srcdir={vleaf},filecount={wcount}')

    return True



def main():
    global parentName

    assess_args()

    logMessageInit('WH_PublishLog')

    # obtain list of directories to limit processing
    EnsList = loadFileLines(gv_EnsList)



    # DEBUG:  Test get_dataset_dirs_loc(anydir,loc)

    testpath = EnsList[0]
    epath, vlist = get_dataset_dirs_loc(testpath,'W')
    print(f'The Ensemble Dir: {epath}')
    for vpath in vlist:
        print(f'       A Pub dir: {vpath}')

    sys.exit(0)















    # sys.exit(0)

    p_rejects = []
    p_failure = []
    p_success = []
    # for each listed Ensemble directory:
    #   Ensure valid warehouse directory
    #   Consult Locks, and Statusfile for Holds, Blocks, and both PUBLICATION:Ready and PUBLICATION:Unblocked
    #   If all tests pass, call conductWahrehousePublication()

    # CHEAT!  If spec is either MAPFILE_GEN or PUBLICATION:COMMIT, convert all edirs to pdirs
    srcdirs = EnsList
    if gv_ChildSpec in ['MAPFILE_GEN', 'PUBLICATION:PUB_COMMIT']:
        srcdirs = [ getPubCurrVersionPath(edir) for edir in EnsList ]

    # printList('',srcdirs)
    # sys.exit(0)

    childp = gv_ChildSpec.split(':')[0]

    if childp == "PUBLICATION":
        action = gv_ChildSpec.split(':')[1]     # may be PUB_PUSH or PUB_COMMIT

        for pdir in srcdirs:
            edir, vleaf = os.path.split(pdir)
            # valid warehouse ensemble directory?
            if action == "PUB_PUSH" and not isWarehouseEnsemble(edir):
                logMessage('WARNING',f'Not a warehouse ensemble directory:{edir}')
                p_rejects.append(pdir)
                continue
            # valid publication directory?
            if action == "PUB_COMMIT" and not isPublicationDirectory(pdir):
                logMessage('WARNING',f'Not a valid publication directory:{pdir}')
                p_rejects.append(pdir)
                continue
            # is dataset locked?       
            if isLocked(edir):
                logMessage('WARNING',f'Dataset Locked:{edir}')
                p_rejects.append(pdir)
                continue

            setLock(edir)

            # READ the status file
            ds_status = load_DatasetStatus(edir) # keys = PATH, VDIR, STAT, COMM
            stats = ds_status['STAT']
            substats = status_breakdown(stats['WAREHOUSE'])

            if action == "PUB_PUSH" and not isPublishableMaxVersion(pdir):
                logMessage('WARNING',f'Dataset MaxVersion {getWHMaxVersion(pdir)} not publishable: {pdir}')
                p_rejects.append(pdir)
                continue

            if isActiveStatus(substats,'PUBLICATION:Blocked'):
                logMessage('WARNING',f'Dataset Publication Blocked:{pdir}')
                p_rejects.append(pdir)
                freeLock(edir)
                continue

            if action == "PUB_PUSH" and not isActiveStatus(substats,'PUBLICATION:Ready'):
                logMessage('WARNING',f'Dataset Pub_Push not Ready:{pdir}')
                p_rejects.append(pdir)
                freeLock(edir)
                continue

            if action == "PUB_COMMIT" and not (isActiveStatus(substats,'PUB_PUSH:Pass') and isActiveStatus(substats,'MAPFILE_GEN:Pass')):
                logMessage('WARNING',f'Dataset Pub_Commit not Ready:{pdir}')
                p_rejects.append(pdir)
                freeLock(edir)
                continue

            ### Cheat: First, ensure we're the WAREHOUSE, engaging the PUBLICATION workflow
            parentName = 'WAREHOUSE'
            setStatus(edir,f'PUBLICATION:Engaged')
            ### End Cheat


            # lets publish!
            pub_result = conductPublication(pdir,action)
            # pub_result = True

            ### Cheat: Pretend we are WAREHOUSE, reporting status of PUBLICATION (so far)
            parentName = 'WAREHOUSE'

            if pub_result == True:
                setStatus(edir,f'PUBLICATION:Success:{action}')
                setStatus(edir,f'MAPFILE_GEN:Ready')
                p_success.append(pdir)
            else:
                setStatus(edir,f'PUBLICATION:Failure:{action}')
                p_failure.append(pdir)

            ### End Cheat

            freeLock(edir)

        logMessage('INFO',f'Moved {len(p_success)} datasets to publishing, launching background mapfile_publication (to publoop)')

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

            # READ the status file
            stat_dir = get_statusfile_dir(adir)
            ds_status = load_DatasetStatus(stat_dir) # keys = PATH, VDIR, STAT, COMM
            stats = ds_status['STAT']
            substats = status_breakdown(stats['WAREHOUSE'])

            if isActiveStatus(substats,'MAPFILE_GEN:Blocked'):
                logMessage('WARNING',f'Dataset Mapfile_Gen Blocked:{adir}')
                p_rejects.append(adir)
                # freeLock(adir) # for now, only for warehouse dirs
                continue

            if not isActiveStatus(substats,'MAPFILE_GEN:Ready'):
                logMessage('WARNING',f'Dataset Mapfile_Gen not Ready:{adir}')
                p_rejects.append(adir)
                # freeLock(adir) # for now, only for warehouse dirs
                continue

            ### Cheat: First, ensure we're the WAREHOUSE, engaging the MAPFILE_GEN workflow
            parentName = 'WAREHOUSE'
            setStatus(stat_dir,f'MAPFILE_GEN:Engaged')
            ### End Cheat

            # Generate a Mapfile
            mapgen_result = conductMapfileGen(adir)

            ### Cheat: Pretend we are WAREHOUSE, reporting status of PUBLICATION (so far)
            parentName = 'WAREHOUSE'

            if mapgen_result == True:
                setStatus(stat_dir,f'MAPFILE_GEN:Success:')
                p_success.append(adir)
            else:
                setStatus(stat_dir,f'MAPFILE_GEN:Failure:')
                p_failure.append(adir)

            ### End Cheat

            # freeLock(adir) # for now, only for warehouse dirs


    logMessage('INFO',f'{childp}:Reject Datasets: {len(p_rejects)}')
    printList('',p_rejects)
    logMessage('INFO',f'{childp}:Failed Datasets: {len(p_failure)}')
    printList('',p_failure)
    logMessage('INFO',f'{childp}:Passed Datasets: {len(p_success)}')
    printList('',p_success)

    sys.exit(0)


if __name__ == "__main__":
  sys.exit(main())





