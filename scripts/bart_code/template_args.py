import sys, os
import argparse

# 
target = ''
linknm = ''

def assess_args():
    global target
    global linknm

    parser = argparse.ArgumentParser(description="Simple test of python symlink creation", prefix_chars='-')
    parser._action_groups.pop()
    required = parser.add_argument_group('required arguments')
    optional = parser.add_argument_group('optional arguments')
    required.add_argument('-L', '--linknm', action='store', dest="linknm", type=str, required=True)
    required.add_argument('-T', '--target', action='store', dest="target", type=str, required=True)
    optional.add_argument('--optional_arg')

    args = parser.parse_args()

    if not (args.linknm and args.target):
        print("Error:  Both linkname and target are required. Try -h")
        sys.exit(0)

    target = args.target
    linknm = args.linknm



def main():

    assess_args()

    sys.exit(0)

if __name__ == "__main__":
  sys.exit(main())





