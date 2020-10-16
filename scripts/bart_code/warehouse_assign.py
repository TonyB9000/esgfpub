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
    The warehouse_assign utility conducts miscellaneous management tasks involving the warehouse,
    from changing the status assignment codes to the dataset leaf directories to the wholesale
    removal of directories no longer needed in the warehouse.

    Options:
        -r, --rootpath              Override default warehouse /p/user_pub/e3sm/staging/prepub
        -w, --warehouse-paths       File of selected warehouse leaf directoriesa upon which to operate.
        -l, --listpaths mode        List (all,empty,nonempty) leaf directories under rootpath (warehouse)
        -g, --getstatus statcode    Return all leaf directories possessing the given statcode.
        -G, --getstatus statstring  Return all leaf directories possessing the given statcode string.
        -s, --setstatus statcode    Apply the given statcode to all qualifying leaf directories.
        -S, --setstatus statstring  Apply the given statcode string to all qualifying leaf directories.
        --force                     Override 'hold', 'working' and 'nostatus" dirs that prevent processing.

    Options that involve making changes (-s, --setstatus) require the "-w filelist" specification.
        Some setstatus commands will be rejected unless "-f, --force" is supplied.
    Options that involve examination (-g --getstatus) do not require the "-w filelist" specification,
    although -w may be supplied as an additional filter.

    If both getstatus and setstatus are applied, the getstatus value is used as a filter, as in
        "where getstatus is S1, setstatus to S2", again additionally filtered by input filelist.
    
    The -l, --listpaths (all,empty,nonempty) command will return all qualifying leaf directories

    THE STATUS words and values:

        statword    charvalue       intention
        ------------------------------------------------------------------------------------------
        (none)      (none)          directory not "in play" for warehouse automated processing (*)
        free        -               open for any appropriate processing
        hold        ^               treat as (none), directory not "in play"
        working     ~               directory contents are being modified - do not interfere
        toss        X               directory may be deleted up to dependents
        pub_ready   p               dataset publication-ready
        publish     P               dataset publication-ready and authorized

        (*) 'none' and 'hold' may be overridden by "-f, --force".

        The intention is to supply extended codes to directories, such as

            v0.-FtD--:  open for processing, Failed timecheck, Needs time-rectify, ...

        Presently only the first position (v0.-, v0.P, etc) are available.

        So, 'setstatus hold' is the same as 'Setstatus ^', but eventually 'setstatus' will affect
        only a single position, whereas 'SetStatus -FtD--' will completely replace the target
        directory extension code.

        Hence, a bash command like "mv dirpath/v0.* dirpath/v0" will take a directory out of play.

    WARNING:  Although these directory extensions are part of the formal directory path, they
        should not be replicated with the same "v#".  That is, there must be only ONE v0.statcode,
        and ONE v1.statcode, etc.
 
'''

gv_WH_root = '/p/user_pub/e3sm/staging/prepub'

gv_SelectionFile = ''
gv_Force = False
gv_setstat = ''
gv_Setstat = ''
gv_getstat = ''
gv_Getstat = ''
gv_PathSpec = ''    # all, empty, nonempty


def assess_args():
    global gv_WH_root
    global gv_SelectionFile
    global gv_Force
    global gv_setstat
    global gv_Setstat
    global gv_getstat
    global gv_Getstat
    global gv_PathSpec

    parser = argparse.ArgumentParser(description=helptext, prefix_chars='-', formatter_class=RawTextHelpFormatter)
    parser._action_groups.pop()
    required = parser.add_argument_group('required arguments')
    optional = parser.add_argument_group('optional arguments')

    optional.add_argument('-r', '--rootpath', action='store', dest="wh_rootpath", type=str, required=False)
    optional.add_argument('-w', '--warehouse-path-list', action='store', dest="wh_selected", type=str, required=False)
    optional.add_argument('-g', '--getstatus', action='store', dest="gv_getstat", type=str, required=False)
    optional.add_argument('-G', '--Getstatus', action='store', dest="gv_getstats", type=str, required=False)
    optional.add_argument('-l', '--listpaths', action='store', dest="gv_pathspec", type=str, required=False)
    optional.add_argument('-s', '--setstatus', action='store', dest="gv_setstat", type=str, required=False)
    optional.add_argument('-S', '--Setstatus', action='store', dest="gv_setstats", type=str, required=False)
    optional.add_argument('--force', action='store_true', dest="gv_force", required=False)


    args = parser.parse_args()

    if (args.gv_setstat or args.gv_setstats) and not args.wh_selected:
        print("Error:  Setstatus or setstatus requires a pathlist file (-w).  Try -h")
        sys.exit(0)

    # new root?
    if args.wh_rootpath:
        gv_WH_root = args.wh_rootpath

    # got dir listing?
    if args.wh_selected:
        gv_SelectionFile = args.wh_selected

    if args.gv_pathspec:
        gv_PathSpec = args.gv_pathspec

    if args.gv_getstat:
        gv_getstat = args.gv_getstat
    if args.gv_getstats:
        gv_Getstat = args.gv_getstats
    if args.gv_setstat:
        gv_setstat = args.gv_setstat
    if args.gv_setstats:
        gv_Setstat = args.gv_setstats

    if args.gv_getstat and args.gv_getstats:
        print("Error:  Only one of '-getstat statword' or '-getstats statstring' may be specified.  Try -h")
        sys.exit(0)
    if args.gv_setstat and args.gv_setstats:
        print("Error:  Only one of '-setstat statword' or '-setstats statstring' may be specified.  Try -h")
        sys.exit(0)

    if args.gv_force:
        gv_Force = args.gv_force


def get_leafdirs(rootpath,mode):     # mode == "any" (default), or "empty" or "nonempty"
    '''
    return all directories containing no subdirectories
    optionally trim to only empty, or nonempty directories
    '''

    selected = []
    for root, dirs, files in os.walk(rootpath):
        if not dirs:
            selected.append(root)
    if not (mode == 'empty' or mode == 'nonempty'):
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
        return -1

    spos = 0    # generalize
    tailparts = tail.split('.')

    vers_part = tailparts[0]
    if len(tailparts) == 1:
        stat_part = ''
    else:
        stat_part = tailparts[1]

    if (stat_part == '' or stat_part[spos] == vstatcode['hold'] or stat_part[spos] == vstatcode['working']) and not gv_Force:
        print(f'WARNING: set_vpath_statusspec precluded without -f (force)')
        return -1

    if stat_part == '':
        stat_part = str(statspec[spos])
    else:
        stat_part = stat_part[:spos] + statspec[spos] + stat_part[spos+1:]

    newtail = '.'.join([vers_part,stat_part])
    newpath = os.path.join(head,newtail)

    print(f' renaming {apath} to {newpath}')
    os.rename(apath,newpath)

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
    for apath in dlist:
        head, tail = os.path.split(apath)
        tailparts = tail.split('.')
        if len(tailparts) < 2:
            continue
        if not statusMatch(tailparts[1],instat):
            continue
        retlist.append(apath)

    return retlist

def printList(alist):
    for _ in alist:
        print(f'{_}')

def main():

    assess_args()

    # if gv_setstat (word) or gv_getstat (word), convert to gvSetstat (char) or gv_Getstat (char)
    if len(gv_getstat) > 0:
        if not gv_getstat in vstatcode:
            print(f'ERROR: unrecognized statcode "{gv_getstat}"')
            sys.exit(-1)
        else:
            gv_Getstat = vstatcode[gv_getstat]

    if len(gv_setstat) > 0:
        if not gv_setstat in vstatcode:
            print(f'ERROR: unrecognized statcode "{gv_setstat}"')
            sys.exit(-1)
        else:
            gv_Setstat = vstatcode[gv_setstat]

    # easy stuff first
    if len(gv_PathSpec) > 0:
        thedirs = get_leafdirs(gv_WH_root,gv_PathSpec)
        printList(thedirs)
        sys.exit(0)
        
    # obtain list of directories to limit processing
    Limited = False
    if len(gv_SelectionFile) > 0:
        Limited = True
        with open(gv_SelectionFile,"r") as f:
            DirList = f.read().split('\n')
        DirList = [ _ for _ in DirList if _[:-1] ]
    else:
        DirList = get_leafdirs(gv_WH_root,'any')

    # process getStat
    if len(gv_Getstat) > 0:
        DirList = filterByStatus(DirList,gv_Getstat)
        if len(gv_Setstat) == 0:        # output results and exit
            printList(DirList)
            sys.exit(0)

    '''
    print(f'Limited = {Limited}')
    print(f'gv_Setstat = {gv_Setstat}')
    printList(DirList)
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
    
    sys.exit(0)

if __name__ == "__main__":
  sys.exit(main())





