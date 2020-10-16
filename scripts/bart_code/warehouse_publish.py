import sys, os
import argparse
from argparse import RawTextHelpFormatter
import glob
import shutil
import subprocess
import time


# 
def ts():
    return 'TS_' + datetime.now().strftime('%Y%m%d_%H%M%S')


helptext = '''
    The warehouse_publish utility accepts a warehouse directory listing file "--publist file".

    For each listed path, it will:

    1.  check that each path ends with "v#.P", where # in {1 - 9} (else WARNS of path and skips)
        (Use the "warehouse_assign" utility to set the directories to "v#.P" status)

    2.  temporarily changes the directory warehouse status to "working" (~)
    3.  creates a path below E3SM_Publish,

            /p/user_pub/work/E3SM/(newpath.v#)

        matching the existing path below the warehouse

            /p/user_pub/e3sm/staging/prepub/(curpath.v#P)

        If the path already exists but is not empty, the corresponding file lists are compared.
        If they intersect, a warning is issued, and this path is skipped (need "overwrite" flag).

    4.  count the files in the warehouse path
    5.  move the files from warehouse to publication
    6.  recount files in publication to ensure the counts match
        (if ok, change status to v#.X indicating 'ok to delete)
        (if not, leave in 'working' state, issue warning message and move on to next path)

    The list of (publication) paths that passed the above gauntlet intact are then passed to
    a publication-process that takes the given list and runs the mapfile and publish for each.

    Any warehouse paths that fail the above gauntlet are not published and are left in the "working" state.
 
'''

gv_WH_root = '/p/user_pub/e3sm/staging/prepub'
gv_PUB_root = '/p/user_pub/work/E3SM'

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

vstatcode = { 'free': '-', 'hold': '^', 'working': '~', 'toss': 'X', 'pub_ready': 'p', 'publish': 'P' }

# informaional
#   free        ready for any processing indicated by subsequent codes
#   hold        DO NOT process (except by specific "force" command)
#   working     directory is being processed - do not interfere (like "hold" but assumed temporary)
#   toss        Directory may be deleted (necessary?  Why not just delete?)
#   pub_ready   "pristine" dataset, awaiting publication suthorization
#   publish     Publish-seeking process may grab and publish.


def isVLeaf(_):
    if len(_) > 1 and _[0] == 'v' and _[1] in '0123456789':
        return True
    return False

def set_vpath_statusspec(apath,statspec):
    head, tail = os.path.split(apath)

    if not isVLeaf(tail):
        print(f'WARNING: Not VLeaf: {apath}')
        return ''

    spos = 0    # generalize
    tailparts = tail.split('.')

    vers_part = tailparts[0]
    if len(tailparts) == 1:
        stat_part = ''
    else:
        stat_part = tailparts[1]

    if (stat_part == '' or stat_part[spos] == vstatcode['hold'] or stat_part[spos] == vstatcode['working']) and not gv_Force:
        print(f'WARNING: set_vpath_statusspec precluded without -f (force)')
        return ''

    if stat_part == '':
        stat_part = str(statspec[spos])
    else:
        stat_part = stat_part[:spos] + statspec[spos] + stat_part[spos+1:]

    newtail = '.'.join([vers_part,stat_part])
    newpath = os.path.join(head,newtail)

    print(f' renaming {apath} to {newpath}')
    os.rename(apath,newpath)
    return newpath

def get_vpath_status(apath):
    head, tail = os.path.split(apath)

    if not isVLeaf(tail):
        print(f'WARNING: Not VLeaf: {apath}')
        return -1

    tailparts = tail.split('.')

    stat_part = tail.split('.')[1]
    stat_code = stat_part[0]

    stat_keys = [k for k,v in vstatcode.items() if v == statcode]
    return stat_keys[0]

def statusMatch(a,b):    # someday, handle multi-positional matchings
    if len(a) > 0 and len(b) > 0 and a == b:
        return True
    return False

def filterByStatus(dlist,instat):
    retlist = []
    rejects = []
    for apath in dlist:
        head, tail = os.path.split(apath)
        tailparts = tail.split('.')
        if len(tailparts) < 2:
            rejects.append(apath)
            continue
        if not statusMatch(tailparts[1],instat):
            rejects.append(apath)
            continue
        retlist.append(apath)

    return retlist, rejects

def pubVersion(apath):
    vers = int( apath.split('/')[-1][1:2] )
    return vers

def printList(alist):
    for _ in alist:
        print(f'{_}')

# /p/user_pub/e3sm/staging/prepub/(curpath.v#P)
def constructPubPath(wpath):
    wcomps = wpath.split('/')
    ppart = '/'.join(wcomps[6:-1])
    tpart = wcomps[-1][0:2]
    ppath = os.path.join(gv_PUB_root,ppart,tpart)
    print(f'wpath = {wpath}')
    print(f'ppath = {ppath}')
    return ppath

def trisect(A, B):
    return A-B, B-A, A&B

def main():

    assess_args()

    # obtain list of directories to limit processing
    with open(gv_PubList,"r") as f:
        PubList = f.read().split('\n')
    PubList = [ _ for _ in PubList if _[:-1] ]

    # split according to P-status
    PubList, Rejects = filterByStatus(PubList,'P')
    if len(Rejects) > 0:
        print(f'The following {len(Rejects)} warehouse paths do not have the expected publication status (.P)')
        print(f'(Use the "warehouse_assign" utility to set the directories to "v#.P" status)')
        printList(Rejects)

    p_success = []
    for wpath in PubList:
        ver = pubVersion(wpath)
        if ver < 1 or ver > 9:
            print(f'WARNING: Skipping warehouse path: cannot publish version v0 dataset')
            print(f'    {wpath}')
            continue
        # tpath = set_vpath_statusspec(wpath,'~')
        # if len(tpath) == 0
        #    continue
        # wpath = tpath
        _, _, wfilenames = walk(wpath).next()
        wcount = len(wfilenames)
        pcount = 0
        ppath = constructPubPath(wpath)
        if os.path.exists(ppath):
            if any(os.scandir(ppath)):
                _, _, pfilenames = walk(ppath).next()
                pcount = len(pfilenames)
                w_only, p_only, in_both = trisect(set(wfilenames),set(pfilenames))
                
                if( len(in_both) > 0 ):
                    print(f'WARNING: Skipping warehouse path: existing destination has {len(in_both)} matching files by name')
                    print(f'    {wpath}')
                    continue
        else:
            os.makedirs(ppath,exist_ok=True)
            os.chmod(ppath,0o775)

        for wfile in wfilenames:
            src = os.path.join(wpath,wfile)
            dst = os.path.join(ppath,wfile)
            shutil.move(src,dst)     # chmod 664?
            os.chmod(dst,0o664)

        _, _, pfilenames = walk(ppath).next()
        finalpcount = len(pfilenames)
        if not finalpcount == (pcount + wcount):
            print(f'WARNING: Discrepency in filecounts:  pub_original={pcount}, pub_warehouse={wcount}, pub_final={pcount+wcount}')
            print(f'    {wpath}')
            continue

        wpath = set_vpath_statusspec(wpath,'X')
        p_success.append(wpath)
        
    sys.exit(0)

    '''
    # set status string extension to gv_Setstat
    if (Limited or gv_Force) and len(gv_Setstat) > 0:
        for adir in DirList:
            if not os.path.exists(adir):
                print(f'WARNING: no such path: {adir}')
                continue
            print(f'set stat {gv_Setstat} for dir {adir}')
            set_vpath_statusspec(adir,gv_Setstat)
    '''
    
    sys.exit(0)

if __name__ == "__main__":
  sys.exit(main())





