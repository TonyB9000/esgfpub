import sys, os
import argparse
import shutil

#  USAGE:  archive_holodeck_setup.sh [-H holodeck] -A full_path_to_a_leaf_archive_directory"


helptext = '''
    The -A archive must name a fully-qualified zstash archive directory (index.db + numbered tarfiles).
    If -H holodeck_name is not given, a directory "Holodeck" will be created in the current directory.
    If such a directory exists, its contents will be deleted.  If -H holodeck_name is supplied, then
    that directory will be applied, but must either not yet exist, or must be empty.
'''

the_cwd = ''
holodeck = ''
archive = ''
holozst = ''
hdefault = False

def assess_args():
    global archive
    global holodeck
    global holozst
    global hdefault

    parser = argparse.ArgumentParser(description=helptext, prefix_chars='-')
    parser._action_groups.pop()
    required = parser.add_argument_group('required arguments')
    optional = parser.add_argument_group('optional arguments')

    required.add_argument('-A', '--archive', action='store', dest="archive", type=str, required=True)
    optional.add_argument('-H', '--holodeck', action='store', dest="holodeck", type=str, required=False)

    args = parser.parse_args()

    if not (args.archive):
        print("Error:  No source archive specified")
        sys.exit(0)

    if not os.path.exists(args.archive):
        print("Error:  Specified archive not found: {}".format(args.archive))
        sys.exit(0)

    archive = args.archive
    the_cwd = os.getcwd()

    if not (args.holodeck):
        holodeck = os.path.join(the_cwd,'Holodeck')
        print("holodeck = {}".format(holodeck))
        shutil.rmtree(holodeck,ignore_errors=True)
        os.mkdir(holodeck)
        holozst=os.path.join(holodeck,'zstash')
        os.mkdir(holozst)
        hdefault = True
    else:
        holodeck = args.holodeck
        hdefault = False
        
    if not hdefault:
        if os.path.exists(holodeck):
            if any( os.scandir(holodeck) ) and not hdefault:  # os.scandir() is an iterator, os.listdir() is not
                print("Error:  Named holodeck directory is not empty: {}".format(holodeck))
                sys.exit(0)
            else:
                holozst=os.path.join(holodeck,'zstash')
                os.mkdir(holozst)
        else:
            if not os.path.isabs(holodeck):
                holodeck = os.path.join(the_cwd,holodeck)
                os.mkdir(holodeck)
            holozst=os.path.join(holodeck,'zstash')
            os.mkdir(holozst)



def main():

    assess_args()

    print('Producing Holodeck {} for archive {}'.format(holodeck,archive))

    for item in os.scandir(archive):
        base = item.path.split('/')[-1]         # get archive item basename
        link = os.path.join(holozst,base)       # create full link name 
        # print(f'Link = { link }')
        os.symlink(item.path,link)

    print("Holodeck prepared for entry. Enjoy your simulation!")

    sys.exit(0)


if __name__ == "__main__":
  sys.exit(main())





