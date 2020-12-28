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
gv_logname = ''

'''
    Run with "nohup python mapfile_generation_service.py &"

    INTENTION:  To be launched and remain in background, seek files from
       staging/mapfiles/mapfile_requests/
    where
       filenames are "mapfile_request-<ts>" and contain a single dataset fullpath
       NOTE: The "dataset fullpath" may be either a publication or warehouse version path.

    I was going to make this a flag:
        [--warehouse-persona]   (act "warehouse compliant", check/update dataset status file)
    so that the service could perform where no ".status" processing is expected.  Presently,
    this (--warehouse-persona) is simply the default.
'''

# ======== convenience ========================

def ts(prefix):
    return prefix + datetime.now().strftime('%Y%m%d_%H%M%S')

def loadFileLines(afile):
    retlist = []
    if len(afile):
        with open(afile,"r") as f:
            retlist = f.read().split('\n')
        retlist = [ _ for _ in retlist if _[:-1] ]
    return retlist

def logMessageInit(logtitle):
    global gv_logname
    gv_logname = f'{logtitle}-{ts("")}'
    open(gv_logname, 'a').close()

def logMessage(mtype,message):
    outmessage = f'{ts("TS_")}:{mtype}:{message}\n'
    with open(gv_logname, 'a') as f:
        f.write(outmessage)

# ======== warehouse ========================

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


gv_WH_root = '/p/user_pub/e3sm/warehouse/E3SM'
gv_PUB_root = '/p/user_pub/work/E3SM'

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
        

def setStatus(edir,statspec):
    statfile = os.path.join(edir,'.status')
    tsval = ts('')
    statline = f'STAT:{tsval}:{parentName}:{statspec}\n'
    with open(statfile, 'a') as f:
        f.write(statline)

def mapfile_validate(srcdir):
    ''' at this point, the srcdir should contain both datafiles (*.nc)
        and the .mapfile, so we can do a name-by-name comparison.
        MUST test for each srcdir datafile in mapfile listing.
    '''
    dataset_files = sorted(glob.glob(srcdir + '/*.nc'))
    mapfile_lines = sorted(loadFileLines(os.path.join(srcdir,'.mapfile')))

    if not len(dataset_files) == len(mapfile_lines):
        logMessage('ERROR',f'non-matching count of files and mapfile lines: {srcdir}')
        return False
        
    # MUST assume both lists sort identically
    pairlist = list(zip(dataset_files,mapfile_lines))
    for atup in pairlist:
        if not atup[0] in atup[1]: 
            logMessage('ERROR',f'dataset file not listed in mapfile: {srcdir}')
            logMessage('ERROR',f'{atup[0]} not in {atup[1]}')
            return False

    return True


input_dir = '/p/user_pub/e3sm/staging/mapfiles/mapfile_requests'
exput_dir = '/p/user_pub/e3sm/staging/mapfiles/mapfiles_output'
ini_path = '/p/user_pub/e3sm/staging/ini_std/'
esgmapfile_make = '/p/user_pub/e3sm/bartoletti1/Pub_Work/2_Mapwork/esgmapfile_make.sh'

searchpath = os.path.join(input_dir,'mapfile_request.*')

warehouse_persona = True
pwd = os.getcwd()
req_done = os.path.join(pwd,'requests_processed')

def main():
    global parentName

    # assess_args()
    logMessageInit('runlog_mapfile_gen_loop')

    while True:
        req_files = glob.glob(input_dir + '/*')
        req_files.sort(key=os.path.getmtime)
        if not len(req_files):
            # print(f'DEBUG: sleeping 60')
            time.sleep(60)
            continue



        request_file = req_files[0]  # or req_files[-1], ensure oldest is selected
        request_path = loadFileLines(request_file)
        request_path = request_path[0]

        if warehouse_persona:
            stat_path = get_statusfile_dir(request_path)
            # logMessage('DEBUG',f'stat_path: {stat_path}')
            if not len(stat_path):
                shutil.move(f'{request_file}',f'{req_done}')
                time.sleep(5)
                continue        # error message already given

        logMessage('INFO',f'MAPGENLOOP:Launching Request Path:{request_path}')
        tm_start = time.time()
        # CALL the Mapfile Maker
        # WAIT here until esgmapfile_make returns
        retcode = os.system(f'{esgmapfile_make} {request_path}')
        tm_final = time.time()
        ET = tm_final - tm_start
        opath, basep = os.path.split(request_file)
        testpath = os.path.join(req_done,basep)
        if os.path.exists(testpath):
            os.remove(testpath)
        shutil.move(f'{request_file}',f'{req_done}')
        logMessage('INFO',f'MAPGENLOOP:Returned:ET={ET}')
        
        time.sleep(5)
        # continue

        # based upon return status
        if retcode:
            # write logfile entry, then
            logMessage('STATUS',f'MAPFILE_GEN:Fail:ret_code={retcode}')
            if warehouse_persona:
                setStatus(stat_path,f'MAPFILE_GEN:Fail:ret_code={retcode}')
            continue
        if not mapfile_validate(request_path):
            # write logfile entry, then
            logMessage('STATUS',f'MAPFILE_GEN:Fail:Bad_mapfile')
            if warehouse_persona:
                setStatus(stat_path,f'MAPFILE_GEN:Fail:Bad_mapfile')
            continue
        # write logfile entry, then
        logMessage('STATUS',f'MAPFILE_GEN:Pass')
        if warehouse_persona:
            setStatus(stat_path,'MAPFILE_GEN:Pass')

      
if __name__ == "__main__":
  sys.exit(main())



