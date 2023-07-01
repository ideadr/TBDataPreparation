#!/usr/bin/env python3

import glob
import os
import argparse
import re


def returnRunNumber(x: str) -> str:
    """ getRunNumber from the input name. May need modification in the 2023 beam test.

    Args:
        x (str): file name

    Returns:
        str: return runNumber
    """

    m = re.search(r".*run([0-9]+)\.root*",x)

    return m.group(1)


def main():
    """IT MAY NOT BE A GOOD IDEA SINCE THE OUTPUT NAME IS DEFINED IN PhysicsConverter.C script.

    Returns:
        _type_: _description_
    """
    
    parser = argparse.ArgumentParser(description='DRrootify - a script to convert the ASCII output of the Auxiliary/PMT DAQ to root files')

    parser.add_argument('--debug', action='store_true', dest='debug',
                        default=False,
                        help='Print more information')
    parser.add_argument('-o','--output_dir', action='store', dest='ntuplepath',
                        default='/eos/user/i/ideadr/TB2023_H8/recoNtuple/',
                        help='output root file path')
    parser.add_argument('-i','--input_dir', action='store', dest='datapath',
                        default='/eos/user/i/ideadr/TB2023_H8/mergedNtuple/',
                        help='input root file path')
    parser.add_argument('-c','--calibra_file', action='store', dest='calibrationfile',
                        default='/afs/cern.ch/user/i/ideadr/devel/TBDataPreparation/2023_SPS/scripts/RunXXX.json',
                        help='calibration file')
    par = parser.parse_args()
    
    if not os.path.isdir(par.datapath):
        print( 'ERROR! Input directory ' + par.datapath + ' does not exist.' )
        return -1

    if not os.path.isdir(par.ntuplepath):
        print( 'ERROR! Output directory ' + par.ntuplepath + ' does not exist.' )
        return -1

    #One needs to make assumptions here on the format of the filename. Not the best.....

    mrgpath = par.datapath
    mrgfls = [ returnRunNumber(x) for x in glob.glob(mrgpath+"*.root")]
    recpath = par.ntuplepath
    recfls = [ returnRunNumber(x) for x in glob.glob(recpath+"*.root")]
    print(mrgfls)
    print(recfls)
    mrgfls = list(set(mrgfls) - set(recfls))
    
    phspath = par.ntuplepath
    
    print(mrgfls, recfls)
    
    if mrgfls:
        print( str(len(mrgfls))+" new files found")


    calFile=par.calibrationfile
    macroPath = os.getenv('IDEARepo') + "/2023_SPS/scripts/"
    print(macroPath)
    for fl in mrgfls:
        cmnd1 = "root -l -b -q -x '"+macroPath+"PhysicsConverter.C(\""+fl+"\", \""+par.datapath+"\", \""+calFile+"\" )'"
        os.system(cmnd1)
        cmnd2 = "mv physics_sps2023_run"+fl+".root "+phspath  ### Really careful here!
        os.system(cmnd2)

    if not mrgfls:
        print( "No new files found.")


if __name__ == "__main__":
    main()
