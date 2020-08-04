import sys, os
from collections import Counter
from shutil import copy2, copyfile

# alpha_collect.py
#
# for every line in MANIFEST that begins "DEPLOY_CFG:" the remainder is the fullpath to
#  a config file that is also in "cfgs_repo"

# for every line in MANIFEST that begins "DEPLOY_CODE:" the remainder is the fullpath to
#  a code script (bash or python) that is also in "code_repo"

# the "collection operation" MUST Error/Exit if
#  the basename of any two files in DEPLOY_CFG or DEPLOY_CODE have the same name.
#  Otherwise, the files are copied to cfgs_repo or code_repo, respectively.

# if any path does NOT begin with / it is assumed that it is relative to ROOTDIR.

broot = '/p/user_pub/e3sm/bartoletti1/'

manifest = broot + 'alpha/MANIFEST'

# set these in main
cfgs_repo = ''
code_repo = ''
srcroot = ''

def main():


    with open(manifest) as f:
        contents = f.read().split('\n')

    for _ in contents:
        if _[0:9] == 'CFGS_REPO':
            cfgs_repo = _[10:]
        elif _[0:9] == 'CODE_REPO':
            code_repo = _[10:]
        elif _[0:7] == 'SRCROOT':
            srcroot = _[8:]

    print(f'{ cfgs_repo }')
    print(f'{ code_repo }')
    print(f'{ srcroot }')

    deployment = []
    for _ in contents:
        deployment.append( _.split(':') )
    deploy_cfgs = [ _[1] for _ in deployment if _[0] == 'DEPLOY_CFGS' ]
    deploy_code = [ _[1] for _ in deployment if _[0] == 'DEPLOY_CODE' ]

    # ensure no clobbered basenames
    basenames = [ os.path.basename(_) for _ in deploy_cfgs ]
    collision = [k for k,v in Counter(basenames).items() if v>1]
    
    if collision != []:
        print(f'alpha_collect.py:  COLLISIONS: { collision } in { manifest } DEPLOY_CFGS.  Aborting collection.')
        sys.exit(0)

    basenames = [ os.path.basename(_) for _ in deploy_code ]
    collision = [k for k,v in Counter(basenames).items() if v>1]

    if collision != []:
        print(f'alpha_collect.py:  COLLISIONS: { collision } in { manifest } DEPLOY_CODE.  Aborting collection.')
        sys.exit(0)


    additions = []

    for _ in deploy_cfgs: 
        srcpath = _
        if _[0] != '/':
            srcpath = os.path.join(srcroot,_)
        dstpath = os.path.join(cfgs_repo,os.path.basename(_))
        if not os.path.isfile(dstpath):
            additions.append(os.path.basename(_))
        # copy2(srcpath,dstpath)
        copyfile(srcpath,dstpath)

    print()

    for _ in deploy_code:
        srcpath = _
        if _[0] != '/':
            srcpath = os.path.join(srcroot,_)
        dstpath = os.path.join(code_repo,os.path.basename(_))
        if not os.path.isfile(dstpath):
            additions.append(os.path.basename(_))
        # copy2(srcpath,dstpath)
        copyfile(srcpath,dstpath)

    print(f' ADDITIONS: ')
    for _ in additions:
        print(f'    { _ }')

    sys.exit(0)

if __name__ == "__main__":
  sys.exit(main())





