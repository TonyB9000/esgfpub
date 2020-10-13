import os, sys
import argparse
import time
from datetime import datetime

acomment = 'Hangs on Links'

help_text = 'Produce the list filecount,directorypath for all paths containing regular files\n\
(may hang if links are encountered?)'

def assess_args():

    parser = argparse.ArgumentParser(description=help_text)
    parser.add_argument('--targetdir', "-t", dest='targetdir', help="directory to assess")

    args = parser.parse_args()


warehouse = '/p/user_pub/e3sm/staging/prepub'

ts=datetime.now().strftime('%Y%m%d_%H%M%S')
paths_out = 'warehouse_paths-' + ts
stats_out = 'warehouse_status-' + ts

# dsid:  root,model,experiment.resolution. ... .realm.grid.otype.ens.vcode


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
    return comps[1],expname,comps[-2]

def get_dsid_type_key( dsid ):
    comps=dsid.split('.')
    realm = comps[-6]
    gridv = comps[-5]
    otype = comps[-4]
    freq = comps[-3]

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
    else:
        grid = 'reg'
    return '_'.join([realm,grid,freq])

def dataset_print_csv( akey, dkey ):
    print(f'{akey[0]},{akey[1]},{akey[2]},{dkey}')


print_paths = True

def main():

    # assess_args()

    src_selected = []
    for root, dirs, files in os.walk(warehouse):      # aggregate full sourcefile paths in src_selected
        if not dirs:     # at leaf-directory matching src_selector
            src_selected.append(root)
            #for afile in files:
            #    src_selected.append(os.path.join(root,afile))

    wh_nonempty = []
    for adir in src_selected:
        # print(adir)
        # if os.path.islink(adir):
        #     print(f'ISLINK: {adir}')
        #     continue
        for root, dirs, files in os.walk(adir):
            if files:
                wh_nonempty.append( tuple([adir,os.path.basename(adir),len(files)]))

    # print(f'Processed { len(wh_nonempty) } non-empty directories')

    idvals = []
    akeys = []
    dkeys = []
    vcodes = []

    if print_paths:
        with open(paths_out,'w') as f:
            stdout_orig = sys.stdout
            sys.stdout = f
            for atup in wh_nonempty:
                print(f'{atup[0]}')
            sys.stdout = stdout_orig

    for atup in wh_nonempty:

        idval = '.'.join(atup[0].split('/')[5:])
        idvals.append(idval)
        # print(f'idval: {idval}')
        akey = get_dsid_arch_key(idval)
        dkey = get_dsid_type_key(idval)
        vcode = idval.split('.')[-1]
        akeys.append(akey)
        dkeys.append(dkey)
        vcodes.append(vcode)
        # print(f'    {akey} : {dkey} : {vcode}')

    akeys = list(set(akeys))
    dkeys = list(set(dkeys))
    vcodes = list(set(vcodes))
    akeys.sort()
    dkeys.sort()
    vcodes.sort()

    # create a dictionary keyed by 'akey', each value a dictionary keyed by dkey, value a list of vcodes.
    # For each (model,experiment,ensemble), create a dataset_type entry for every allowable dataset-type
    dataset_status = {}
    for akey in akeys:
        dataset_status[akey] = { dkey: []  for dkey in dkeys }

    idcount = 0
    for idval in idvals:
        idcount += 1
        # print(f'idval[{idcount}]: {idval}')
        akey = get_dsid_arch_key(idval)
        dkey = get_dsid_type_key(idval)
        vcode = idval.split('.')[-1]
        if vcode in dataset_status[akey][dkey]:
            print(f'    vcode:{vcode} already given for {akey} : {dkey}')
        dataset_status[akey][dkey].append(vcode)
        dataset_status[akey][dkey].sort()


    stdout_orig = sys.stdout
    with open(stats_out,'w') as f:
        sys.stdout = f

        for idval in idvals:
            akey = get_dsid_arch_key(idval)
            dkey = get_dsid_type_key(idval)
            vlist = dataset_status[akey][dkey]
            statlist = ['__','__','__']
            if 'v0' in vlist:
                statlist[0] = 'v0'
            if 'v1' in vlist:
                statlist[1] = 'v1'
            if 'v2' in vlist:
                statlist[2] = 'v2'
            statcode = '.'.join(statlist)
            print(f'STATUS={statcode}:',end ='')
            dataset_print_csv(akey,dkey)

        sys.stdout = stdout_orig


    sys.exit(0)

if __name__ == "__main__":
  sys.exit(main())

