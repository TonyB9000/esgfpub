import os, sys


thePWD = os.getcwd()

srcdir = os.path.join(thePWD,'PathsFound')

disqual = [ 'rest/', 'post/', 'test', 'init', 'run/try', 'run/bench', 'old/run', 'pp/remap', 'a-prime', 'lnd_rerun', 'atm/ncdiff', 'archive/rest', 'fullD', 'photic']

outF = open("headset_list_first_last", "w")

for filename in os.listdir(srcdir):
    thepath = os.path.join('PathsFound',filename)

    qualified = []
    with open(thepath) as f:
        for aline in f:
            if any( aline.startswith(_) for _ in disqual ):
                continue
            qualified.append(aline)
    if len(qualified):
        qualified.sort()
        outF.write(f'{filename}\n')
        outF.write(f'    HEADF:{qualified[0]}')
        outF.write(f'    HEADL:{qualified[-1]}')

print("Stage 2 Completed.  Edit output file \"headset_list_first_last\" and use as input to Stage 3.")

