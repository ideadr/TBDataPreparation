#!/usr/bin/env python3

##**************************************************
## \file DRrootify.py
## \brief: converter from ASCII files to EventDR objects 
##         to ROOT files
## \author: Lorenzo Pezzotti (CERN EP-SFT-sim) @lopezzot
##          Andrea Negri (UniPV & INFN)
## \start date: 16 August 2021
##
## Updated for TB2023 by Yuchen Cai and Iacopo Vivarelli 
##**************************************************


import DREvent
from ROOT import *
from array import array
import sys
import glob
import os

class DRrootify:
    '''Class to rootify raw ASCII files'''

    def __init__(self, fname):
        '''Class Constructor'''
        self.drfname = fname+".txt"
        self.drfile = TFile(fname+".root","RECREATE")
        self.tbtree = TTree("CERNSPS2023","CERNSPS2023")
        self.EventNumber = array('i',[0])
        self.NumOfPhysEv = array('i',[0])
        self.NumOfPedeEv = array('i',[0])
        self.NumOfSpilEv = array('i',[0])
        self.TriggerMask = array('l',[0])
        self.ADCs = array('i',[-1]*96)
        self.TDCsval = array('i',[-1]*48)
        self.TDCscheck = array('i',[-1]*48)

        self.tbtree.Branch("EventNumber",self.EventNumber,'EventNumber/I')
        self.tbtree.Branch("NumOfPhysEv",self.NumOfPhysEv,'NumOfPhysEv/I')
        self.tbtree.Branch("NumOfPedeEv",self.NumOfPedeEv,'NumOfPedeEv/I')
        self.tbtree.Branch("NumOfSpilEv",self.NumOfSpilEv,'NumOfSpilEv/I')
        self.tbtree.Branch("TriggerMask",self.TriggerMask,'TriggerMask/L')
        self.tbtree.Branch("ADCs",self.ADCs,'ADCs[96]/I')
        self.tbtree.Branch("TDCsval",self.TDCsval,'TDCsval[48]/I')
        self.tbtree.Branch("TDCscheck",self.TDCscheck,'TDCscheck[48]/I')

    def ReadandRoot(self):
        '''Read ASCII files line by line and rootify'''
        print( "--->Start rootification of " + self.drfname )
        for i, line in enumerate(open(self.drfname)):
            if i%5000 == 0 : print( "------>At line "+str(i)+" of "+str(self.drfname) )
            evt = DREvent.DRdecode(line) 
            self.EventNumber[0] = evt.EventNumber
            self.NumOfPhysEv[0] = evt.NumOfPhysEv
            self.NumOfPedeEv[0] = evt.NumOfPedeEv
            self.NumOfSpilEv[0] = evt.NumOfSpilEv
            self.TriggerMask[0] = evt.TriggerMask
	    #if evt.TriggerMask > 10:
	    #	print evt.TriggerMask
            for ch,val in evt.ADCs.items() :
                self.ADCs[ch] = val
            for ch,vals in evt.TDCs.items():
                self.TDCsval[ch] = vals[0]
                self.TDCscheck[ch] = vals[1]
            self.tbtree.Fill()
        print( "--->End rootification of " + self.drfname )
    
    def Write(self):
        self.tbtree.Write()
        self.drfile.Close()


def main():
    import argparse
    #Parse arguments from the command line
    parser = argparse.ArgumentParser(description='DRrootify - a script to convert the ASCII output of the Auxiliary/PMT DAQ to root files')

    parser.add_argument('--debug', action='store_true', dest='debug',
                        default=False,
                        help='Print more information')
    parser.add_argument('-o','--output_dir', action='store', dest='ntuplepath',
                        default='/eos/user/i/ideadr/TB2023_H8/rawNtuple',
                        help='output root files will be stored in this directory')
    parser.add_argument('-i','--input_dir', action='store', dest='datapath',
                        default='/eos/user/i/ideadr/TB2023_H8/rawDataDreamDaq',
                        help='output root files will be stored in this directory')
    par = parser.parse_args()



    #Get list of files on rawData and rawNtuple
    #
    datapath = par.datapath
    ntuplepath = par.ntuplepath

    print( 'Input directory ' + datapath )
    print( 'Output directory ' + ntuplepath )

    if not os.path.isdir(datapath):
        print( 'ERROR! Input directory ' + datapath + ' does not exist.' )
        return -1

    if not os.path.isdir(ntuplepath):
        print( 'ERROR! Output directory ' + ntuplepath + ' does not exist.' )
        return -1

    datafls = [x.split(".bz2")[0] for x in glob.glob(datapath+"/sps*.bz2")]
    datafls = [os.path.basename(x) for x in datafls]

    ntuplfls = [x.split(".root")[0]+".txt" for x in glob.glob(ntuplepath+"/*.root")]
    ntuplfls = [os.path.basename(x) for x in ntuplfls]
    newfls = list(set(datafls)-set(ntuplfls))



    if par.debug: 
        print ('\n This is the list of potential raw data files to be converted \n')
        for x in datafls:
            print( x)

        print ('\n This is the list of data files already converted \n')
        for x in ntuplfls:
            print( x)
                
        print ('\n This is the list of data files that will be converted \n')
        for x in newfls:
            print( x)
        quit()

    #Rootify those data
    
    print ("Hi!")
    if newfls:
        print( str(len(newfls))+" new files found")

    for fl in newfls:
        print( "->Found new file to be rootified: " + str(fl) )
        os.system("bzip2 -d -k "+datapath+ '/' + str(fl)+".bz2")
        print( "--->"+str(fl)+".bz2 decompressed")
        fname = fl[0:-4] # remove .txt in the name
        dr = DRrootify(datapath+'/' +fname)
        dr.ReadandRoot()
        dr.Write()
        os.system("rm "+datapath+'/' + fl) # remove decompressed txt files
        os.system("mv "+datapath+ '/' + str(fl[0:-4])+".root "+ntuplepath + '/') # move output ntuple to output dir
    else:
        print( "->No new files found"            )

    print( "Bye!")

##**************************************************


if __name__ == "__main__":
    main()
