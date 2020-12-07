import sys, os
import argparse
from argparse import RawTextHelpFormatter
import glob
import shutil
import subprocess
import time
from datetime import datetime


parentName = 'PUBLICATION'

#
def ts(prefix):
    return prefix + datetime.now().strftime('%Y%m%d_%H%M%S')



helptext = '''
    The warehouse_publish utility accepts a warehouse ensemble directory listing file "--publist file".

 
'''

gv_WH_root = '/p/user_pub/e3sm/staging/prepub'
gv_PUB_root = '/p/user_pub/work/E3SM'
gv_MapGenPath = '/p/user_pub/e3sm/bartoletti1/Pub_Work/2_Mapwork'
gv_MapGenProc = '/p/user_pub/e3sm/bartoletti1/Pub_Work/2_Mapwork/multi_mapfile_publish.sh'


gv_PubList = ''
gv_Force = False


def assess_args():
    global gv_PubList
    global gv_Force

    parser = argparse.ArgumentParser(description=helptext, prefix_chars='-', formatter_class=RawTextHelpFormatter)
    parser._action_groups.pop()
    required = parser.add_argument_group('required arguments')
    optional = parser.add_argument_group('optional arguments')

    required.add_argument('--publist', action='store', dest="wh_publist", type=str, required=True)
    optional.add_argument('--force', action='store_true', dest="gv_force", required=False)


    args = parser.parse_args()

    if args.wh_publist:
        gv_PubList = args.wh_publist

    if args.gv_force:
        gv_Force = args.gv_force

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
valid_subprocess = ['EXTRACTION','VALIDATION','POSTPROCESS','PUBLICATION','EVICTION']
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


def isVLeaf(_):
    if len(_) > 1 and _[0] == 'v' and _[1] in '0123456789':
        return True
    return False

def getWHMaxVersion(enspath):
    # trim enspath to id_path if not already (trim off WH_path_root)
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

# /p/user_pub/e3sm/staging/prepub/(curpath.v#P)
def constructPubPath(wpath):
    wcomps = wpath.split('/')
    ppart = '/'.join(wcomps[6:-1])
    tpart = wcomps[-1][0:2]
    ppath = os.path.join(gv_PUB_root,ppart,tpart)
    # print(f'wpath = {wpath}')
    # print(f'ppath = {ppath}')
    return ppath

def trisect(A, B):
    return A-B, B-A, A&B

def conductPublication(edir):
    #   Ensure a publishable version directory exists, non-empty, and a matching publication directory is not already populated
    #   Set PUB_PUSH:Engaged:dstdir=leaf_vdir
    #   Move the files
    #   Launch the Mapfile_Publication suite

    vleaf = getWHMaxVersion(edir)
    wpath = os.path.join(edir,vleaf)

    wfilenames = [files for _, _, files in os.walk(wpath)][0]
    wfilenames.sort()
    wcount = len(wfilenames)
    logMessage('INFO',f'Processing: {wcount} files: {wpath}')

    setStatus(edir,f'PUB_PUSH:Engaged:srcdir={vleaf},filecount={wcount}')

    pcount = 0
    ppath = constructPubPath(wpath)
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
            shutil.move(src,dst)
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
    # STATUS WRITE: wpath = set_vpath_statusspec(wpath,'X',True)

    '''
        We launch a detached background "mapfile-publish" job right here and return.
        The "p_success" list has the publication paths we write to a file as input.
    '''

    # create a file in the map-publish directory containing the successful publish paths

    mapjobfile = 'map_publish_job-' + ts('')
    mapjobpath = os.path.join(gv_MapGenPath,mapjobfile)
    pubpaths = [ ppath ]        # a pathlist-file of one path!
    printFileList(mapjobpath,pubpaths)

    os.system(f'nohup {gv_MapGenProc} {mapjobpath} &')

    setStatus(edir,f'PUB_PUSH:Pass')

    return True



def main():
    global parentName

    assess_args()

    logMessageInit('WH_PublishLog')

    # obtain list of directories to limit processing
    PubList = loadFileLines(gv_PubList)

    p_rejects = []
    p_failure = []
    p_success = []
    # for each listed Ensemble directory:
    #   Ensure valid warehouse directory
    #   Consult Locks, and Statusfile for Holds, Blocks, and both PUBLICATION:Ready and PUBLICATION:Unblocked
    #   If all tests pass, call conductWahrehousePublication()

    for edir in PubList:
        # valid warehouse ensemble directory?
        if not isWarehouseEnsemble(edir):
            logMessage('WARNING',f'Not a warehouse ensemble directory:{edir}')
            p_rejects.append(edir)
            continue
        # is dataset locked?       
        if isLocked(edir):
            logMessage('WARNING',f'Dataset Locked:{edir}')
            p_rejects.append(edir)
            continue
        if not isPublishableMaxVersion(edir):
            logMessage('WARNING',f'Dataset MaxVersion {getWHMaxVersion(edir)} not publishable: {edir}')
            p_rejects.append(edir)
            continue

        setLock(edir)

        ds_status = load_DatasetStatus(edir) # keys = PATH, VDIR, STAT, COMM
        stats = ds_status['STAT']
        substats = status_breakdown(stats['WAREHOUSE'])

        if isActiveStatus(substats,'PUBLICATION:Blocked'):
            logMessage('WARNING',f'Dataset Publication Blocked:{edir}')
            p_rejects.append(edir)
            freeLock(edir)
            continue

        if not isActiveStatus(substats,'PUBLICATION:Ready'):
            logMessage('WARNING',f'Dataset Publication not Ready:{edir}')
            p_rejects.append(edir)
            freeLock(edir)
            continue

        ### Cheat: First, pretend we're the WAREHOUSE, engaging the PUBLICATION workflow
        parentName = 'WAREHOUSE'
        setStatus(edir,f'PUBLICATION:Engaged')
        ### Now, go back to being PUBLICATION, calling its PUB_PUSH (to auto-publish) process
        parentName = 'PUBLICATION'
        ### End Cheat


        # lets publish!
        pub_result = conductPublication(edir)
        # pub_result = True

        ### Cheat: Pretend we are WAREHOUSE, reporting status of PUBLICATION (so far)
        parentName = 'WAREHOUSE'

        if pub_result == True:
            setStatus(edir,f'PUBLICATION:Success:Pub_Push')
            p_success.append(edir)
        else:
            setStatus(edir,f'PUBLICATION:Failure:Pub_Push')
            p_failure.append(edir)

        parentName = 'PUBLICATION'
        ### End Cheat

        freeLock(edir)

    logMessage('INFO',f'Moved {len(p_success)} datasets to publishing, launching background mapfile_publication (to publoop)')

    logMessage('INFO',f'Reject Datasets: {len(p_rejects)}')
    printList('',p_rejects)
    logMessage('INFO',f'Failed Datasets: {len(p_failure)}')
    printList('',p_failure)
    logMessage('INFO',f'Passed Datasets: {len(p_success)}')
    printList('',p_success)

    sys.exit(0)


if __name__ == "__main__":
  sys.exit(main())





