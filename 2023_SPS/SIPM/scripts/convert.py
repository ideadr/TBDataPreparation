import os, sys, subprocess
from glob import glob
import multiprocessing as mp
from tqdm import tqdm



def getFiles():
    print(rawdataPath)
    files = glob(rawdataPath + "/*.dat")
    files = list(map(os.path.abspath, files))
    files = [f for f in files if os.path.getsize(f) > 1000]
    print(files)
    return files


def moveConverted(fnames):
    toMove = glob(rawdataPath + "/Run*.root")
    for f in toMove:
        newfname = rawntuplePath +"/"+ os.path.basename(f)
        os.rename(f,newfname)
    #for f in fnames:
    #    p = subprocess.Popen(["bzip2", "-z", f])
    #    p.wait()


def runConversion(fname):
    p = subprocess.Popen(["./dataconverter", fname])
    p.wait()


def convertAll(fnames):
    # Run conversion .dat -> .root
    with mp.Pool(mp.cpu_count(), maxtasksperchild=4) as pool:
        list(
            tqdm(
                pool.imap_unordered(runConversion, fnames),
                total=len(fnames),
                unit="file",
                dynamic_ncols=True,
                position=0,
                colour="GREEN",
            )
        )


if __name__ == "__main__":
    import argparse                                                                      
    parser = argparse.ArgumentParser(description='This script onverts the binary FERs files from the Janus software to root ntuples.')
    parser.add_argument('-i', '--inputRawDataPath', dest='rawdataPath', default='/afs/cern.ch/user/i/ideadr/scratch/TB2023_H8/rawData', help='Input path of raw data')
    parser.add_argument('-o', '--outputRawNtuplePath', dest='rawntuplePath', default='/afs/cern.ch/user/i/ideadr/scratch/TB2023_H8/rawNtupleSiPM', help='Output path for the raw ntuples')
    
    par  = parser.parse_args()
    global rawdataPath 
    rawdataPath = par.rawdataPath
    global rawntuplePath
    rawntuplePath = par.rawntuplePath

    if not (os.path.isdir(rawdataPath)):
        print(f"ERROR: {rawdataPath} does not exist")
        exit()

    if not (os.path.isdir(rawntuplePath)):
        print(f"ERROR: {rawntuplePath} does not exist")
        exit()
    
    toConvert = getFiles()

    print(toConvert)

    convertAll(toConvert)
    moveConverted(toConvert)
