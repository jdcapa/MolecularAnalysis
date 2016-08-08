#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Install script for the molecular analysis scripts."""
import argparse
import os
import shutil
import sys

# Scripts
scripts = ["GeoOpt/gopt",
           "XYZ/xyz",
           "HarmonicAnalysis/harmonics",
           "CoreLevel/corelevel",
           "InputMultiplicities/inp_mult"]


# parser set-up
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('directory',
                    metavar='bin directory',
                    type=str,
                    help=('The directory where the scripts are installed, '
                          'which should be added to the $PATH environment.'))
parser.add_argument('-l', '--link',
                    action="store_true",
                    default=False,
                    dest="link_flag",
                    help=('Links the executables instead of copying them.'))
parser.add_argument('-o', '--overwrite',
                    action="store_true",
                    default=False,
                    dest="overwrite_flag",
                    help=('Overwrites existing scripts.'))

args = parser.parse_args()


if __name__ == '__main__':
    # First we need to test if we've got all the packages.
    if sys.version_info.major < 3:
        sys.exit("Please install Python3.4 or newer")
    elif sys.version_info.minor < 4:
        sys.exit("Please install Python3.4 or newer")
    try:
        import moleculartoolbox
        moleculartoolbox.Harmonic
        moleculartoolbox.printfunctions
        moleculartoolbox.OrcaOutput
        moleculartoolbox.Atom
    except ImportError as e:
        cmd = ("pip3 install --user "
               "git+https://github.com/jdcapa/MolecularToolbox")
        sys.exit("{}\nInstall with {}".format(e, cmd))
    try:
        import chemphysconst
        chemphysconst.PeriodicTable()
        chemphysconst.Constants()
    except ImportError as e:
        cmd = "pip3 install --user git+https://github.com/jdcapa/ChemPhysConst"
        sys.exit("{}\nInstall with {}".format(e, cmd))

    # Copy or link the executables
    if not os.path.exists(args.directory):
        sys.exit("The path '{}' does not exist.".format(args.directory))
    for script in scripts:
        new_script_path = os.path.join(args.directory,
                                       os.path.basename(script))
        script = os.path.join(os.getcwd(), script)
        if os.path.exists(new_script_path):
            if args.overwrite_flag:
                print("Removing {}".format(new_script_path))
                os.remove(new_script_path)
            else:
                continue
        if args.link_flag:
            print("Linking {} to {}".format(script, new_script_path))
            os.symlink(script, new_script_path)
        else:
            print("Copying {} to {}".format(script, new_script_path))
            shutil.copy2(script, new_script_path)
