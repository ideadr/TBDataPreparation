#! /usr/bin/env python3

import ROOT
import os
from array import array
import numpy as np
import glob,time

import DRrootify
import bz2

import subprocess

####### Hard coded information - change as you want
#SiPMFileDir="/afs/cern.ch/user/i/ideadr/scratch/TB2023_H8/rawData"
#DaqFileDir="/afs/cern.ch/user/i/ideadr/scratch/TB2023_H8/rawDataDreamDaq"
#MergedFileDir="/afs/cern.ch/user/i/ideadr/scratch/TB2023_H8/mergedNtuple"

SiPMFileDir="/afs/cern.ch/user/i/ideadr/devel/test_data/rawData"
DaqFileDir="/afs/cern.ch/user/i/ideadr/devel/test_data/rawDataDreamDaq"
MergedFileDir="/afs/cern.ch/user/i/ideadr/devel/test_data/mergedNtuple"

outputFileNamePrefix='merged_sps2023'
SiPMTreeName = "SiPMData"
SiPMMetaDataTreeName = "EventInfo"
SiPMNewTreeName = "SiPMSPS2023"
DaqTreeName = "CERNSPS2023"
EventInfoTreeName = "EventInfo"
EvtOffset = -1000
doNotMerge = False



####### main function to merge SiPM and PMT root files with names specified as arguments
    
def CreateBlendedFile(SiPMInputTree,EventInfoTree,DaqInputTree,outputfilename):
    """ Main function to merge SiPM and PMT trees 
    Args:
        SiPMInputTree (TTree): H0 Tree
        DaqInputTree (TTree): H1-H8 Tree
        outputfilename (str): output merged root file

    Returns:
        int: 0
    """

    OutputFile = ROOT.TFile.Open(outputfilename,"recreate")

    ###### Do something to understand the offset

    global EvtOffset
    EvtOffset = DetermineOffset(SiPMInputTree,DaqInputTree)

    if doNotMerge:
        return 0 

    ###### Now really start to merge stuff
    
    newDaqInputTree = DaqInputTree.CloneTree()
    OutputFile.cd()
    newDaqInputTree.Write()
        
    newEventInfoTree = EventInfoTree.CloneTree()
    OutputFile.cd()
    newEventInfoTree.Write()

    OutputFile.cd()
    newSiPMTree = ROOT.TTree(SiPMNewTreeName,"SiPM info")
        
    CloneSiPMTree(SiPMInputTree,OutputFile,DaqInputTree)
                  
    newSiPMTree.Write()
    OutputFile.Close()    
    return 0

# main function to reorder and merge the SiPM file

def CloneSiPMTree(SiPMInput,OutputFile,DaqInputTree = None):
    """ Create a new tree named SiPMNewTreeName("SiPMSPS2023") record board info after considering the offset.
        The logic is the following: 
        - start with a loop on the Daq tree. 
        - For each event find out which entries of the SiPMInput need to be looked at (those with corresponding TriggerId) with the offset. 
        - Once this information is available, copy the information of the boards and save the tree

    Args:
        DaqInputTree (TTree): DaqTreeName("CERNSPS2023") Tree in H1-H8 root file
        SiPMInput (TTree): SiPMTreeName("SiPMData") Tree in H0 root file
        OutputFile (TFile): Output Root file.
    """
    newTree = OutputFile.Get(SiPMNewTreeName)
    TriggerTimeStampUs = array('d',[0])
    EventNumber = array('i',[0])
    HG_Board = []
    LG_Board = []
    for i in range(0,5):
        HG_Board.append(np.array(64*[0],dtype=np.uint16))
        LG_Board.append(np.array(64*[0],dtype=np.uint16))
    HGinput = np.array(64*[0],dtype=np.uint16)
    LGinput = np.array(64*[0],dtype=np.uint16)

    newTree.Branch("TriggerTimeStampUs",TriggerTimeStampUs,'TriggerTimeStampUs/D')
    newTree.Branch("HG_Board0",HG_Board[0],"HG_Board0[64]/s")
    newTree.Branch("HG_Board1",HG_Board[1],"HG_Board1[64]/s")
    newTree.Branch("HG_Board2",HG_Board[2],"HG_Board2[64]/s")
    newTree.Branch("HG_Board3",HG_Board[3],"HG_Board3[64]/s")
    newTree.Branch("HG_Board4",HG_Board[4],"HG_Board4[64]/s")
    newTree.Branch("LG_Board0",LG_Board[0],"LG_Board0[64]/s")
    newTree.Branch("LG_Board1",LG_Board[1],"LG_Board1[64]/s")
    newTree.Branch("LG_Board2",LG_Board[2],"LG_Board2[64]/s")
    newTree.Branch("LG_Board3",LG_Board[3],"LG_Board3[64]/s")
    newTree.Branch("LG_Board4",LG_Board[4],"LG_Board4[64]/s")
    newTree.Branch("EventNumber",EventNumber,"EventNumber/s")
    SiPMInput.SetBranchAddress("HighGainADC",HGinput)
    SiPMInput.SetBranchAddress("LowGainADC",LGinput)

    '''The logic is the following: start with a loop on the Daq tree. For each event find out which entries of the SiPMInput need to be looked at (those with corresponding TriggerId). Once this information is available, copy the information of the boards and save the tree''' 

    entryDict = {}

    for ievt,evt in enumerate(SiPMInput):
        if evt.TriggerId in entryDict:
            entryDict[evt.TriggerId].append(ievt)
        else:
            entryDict[evt.TriggerId] = [ievt]
            
    totalNumberOfEvents = None 
    if DaqInputTree != None: 
        totalNumberOfEvents = DaqInputTree.GetEntries()
    else:
        totalNumberOfEvents = len(entryDict)

    print( "Total Number of Events from DAQ " + str(totalNumberOfEvents))
    print( "Merging with an offset of " + str(EvtOffset))


    
    for daq_ev in range(0,totalNumberOfEvents):
        if (daq_ev%10000 == 0):
            print( str(daq_ev) + " events processed")

        for iboard in range(0,5):
            HG_Board[iboard].fill(0)
            LG_Board[iboard].fill(0)

        evtToBeStored = []
        try:
            evtToBeStored = entryDict[daq_ev + EvtOffset]
        except:
            evtToBeStored = []

        for entryToBeStored in evtToBeStored:
            SiPMInput.GetEntry(entryToBeStored)
            #### Dirty trick to read an unsigned char from the ntuple
            #myboard = map(ord,SiPMInput.BoardId)[0]
            myboard = [ ord(boardID) for boardID in SiPMInput.BoardId ][0]
            np.copyto(HG_Board[myboard],HGinput)
            np.copyto(LG_Board[myboard],LGinput)
            TriggerTimeStampUs[0] = SiPMInput.TriggerTimeStampUs
        EventNumber[0] = daq_ev
        
        newTree.Fill()


def DetermineOffset(SiPMTree,DAQTree):
    """ Scan possible offsets to find out for which one we get the best match 
        between the pedList and the missing TriggerId which could be caused by pedestal.
        Generate four plots:
            - histo: TH1F of discrete difference along the pedestal series.
            - histo2: TH1F of discrete difference of the events from SiPM file with no trigger.
            - graph: TGraph of pedestals, x-axis is TriggerMask.
            - graph2: TGraph of the events from SiPM file with no trigger, x-axis is TriggerId.
            - graph3: TGraph of points of ( scanned offset, difference length ).

    Args:
        SiPMTree (TTree): SiPMTreeName("SiPMData") Tree in H0 root file
        DAQTree (TTree): DaqTreeName("CERNSPS2023") Tree in H1-H8 root file

    Returns:
        int: the Offset applied on H1-H8 matches H1-H8 to H0.
    """
    x = array('i')
    y = array('i')
    xsipm = array('i')
    ysipm = array('i')
    ##### build a list of entries of pedestal events in the DAQ Tree
    DAQTree.SetBranchStatus("*",0) # disable all branches
    DAQTree.SetBranchStatus("TriggerMask",1) # only process "TriggerMask" branch
    pedList = set() # pedestal
    evList = set()
    for iev,ev in enumerate(DAQTree):
        if ev.TriggerMask == 6:
            pedList.add(iev)
        evList.add(iev)
    DAQTree.SetBranchStatus("*",1)
    ##### Now build a list of missing TriggerId in the SiPM tree
    SiPMTree.SetBranchStatus("*",0) # disable all branches
    SiPMTree.SetBranchStatus("TriggerId",1) # only process "TriggerId" branch
    TriggerIdList = set()
    for ev in SiPMTree:
        TriggerIdList.add(ev.TriggerId)
    SiPMTree.SetBranchStatus("*",1)
    ### Find the missing TriggerId
    TrigIdComplement = evList - TriggerIdList
    print( "from PMT file: events "+str(len(evList))+" pedestals: "+str(len(pedList)))
    print( "from SiPM file: events with no trigger "+str(len(TrigIdComplement)))
    #### do some diagnostic plot
    for p in pedList:
        x.append(p)
        y.append(2)
    for p2 in TrigIdComplement:
        xsipm.append(p2)
        ysipm.append(1)
    hist = ROOT.TH1I("histo","histo",100, 0, 100)
    for i in np.diff(sorted(list(pedList))):
        hist.Fill(i)
    hist.Write()
    hist2 = ROOT.TH1I("histo2","histo2",100,0,100)
    for i in np.diff(sorted(list(TrigIdComplement))):
        hist2.Fill(i)
    hist2.Write()
    graph = ROOT.TGraph(len(x),x,y)
    graph.SetTitle( "pedList; EventNumber; 2" )
    graph2 = ROOT.TGraph(len(xsipm),xsipm,ysipm)
    graph2.SetTitle( "SiPM no trigger; EventNumber; 1" )
    graph2.SetMarkerStyle(6)
    graph2.SetMarkerColor(ROOT.kRed)
    graph.SetMarkerStyle(6)
    graph.Write()
    graph2.Write()

    ### Scan possible offsets to find out for which one we get the best match between the pedList and the missing TriggerId

    minOffset = -1000
    minLen = 10000000
    
    diffLen = {}
    
    scanned_offset = array('i')
    scanned_diffLen = array('i')

    for offset in range(-4,5):
        offset_set = {x+offset for x in pedList}
        diffSet =  offset_set - TrigIdComplement
        diffLen[offset] = len(diffSet)
        if len(diffSet) < minLen:
            minLen = len(diffSet)
            minOffset = offset
        print( "Offset " + str(offset) + ": " + str(diffLen[offset]) + " ped triggers where SiPM fired")
        scanned_offset.append(offset)
        scanned_diffLen.append(len(diffSet))
    print( "Minimum value " + str(minLen) + " occurring for " + str(minOffset) + " offset")
    
    graph3 = ROOT.TGraph(len(scanned_offset),scanned_offset,scanned_diffLen)
    graph3.SetMarkerStyle(6)
    graph3.SetTitle( "offset scan; offset; diffLength" )
    graph3.Write()

    return minOffset

def doRun(runnumber,outfilename):
    inputDaqFileName = DaqFileDir + "/sps2023data.run" + str(runnumber) + ".txt.bz2"
    inputSiPMFileName = SiPMFileDir + "/Run" + str(runnumber) + "_list.dat"
    tmpSiPMRootFile = SiPMFileDir + "/Run" + str(runnumber) + "_list.root"

    print ('Running dataconverter on ' + inputSiPMFileName)

    if os.path.isfile(inputSiPMFileName):
        p = subprocess.Popen(["dataconverter", inputSiPMFileName])
        p.wait()
    else:
        print('ERROR! File ' + inputSiPMFileName + ' not found')
        return False

    # returning trees from temporary SiPM ntuple file

    t_SiPMRootFile = None
    try:
        t_SiPMRootFile = ROOT.TFile(tmpSiPMRootFile)
    except:
        print('ERROR! File ' + tmpSiPMRootFile + ' not created')
        return False

    SiPMTree = t_SiPMRootFile.Get(SiPMTreeName)
    EventInfoTree = t_SiPMRootFile.Get(EventInfoTreeName)

    # creating temporary ntuples Tree from DAQ txt file

    f = None 
    try: 
        f = bz2.open(inputDaqFileName,'rt')
    except: 
        print ('ERROR! File ' + inputDaqFileName + ' not found')
        return False

    DreamDaq_rootifier = DRrootify.DRrootify()
    DreamDaq_rootifier.drf = f

    #### rootify the input data

    if not DreamDaq_rootifier.ReadandRoot():
        print("Cannot rootify file " + inputDaqFileName)
        return False

    ##### and now merge

    return CreateBlendedFile(SiPMTree,EventInfoTree,DreamDaq_rootifier.tbtree,outfilename)
    

def GetNewRuns():
    """_summary_

    Returns:
        _type_: _description_
    """
    retval = []
    sim_list = glob.glob(SiPMFileDir + '/*')
    daq_list = glob.glob(DaqFileDir + '/*')
    merged_list = glob.glob(MergedFileDir + '/*')

    sim_run_list = []

    for filename in sim_list:
        sim_run_list.append(os.path.basename(filename).split('_')[0].lstrip('Run'))

    daq_run_list = [] 

    for filename in daq_list:
        daq_run_list.append(os.path.basename(filename).split('.')[1].lstrip('run'))

    already_merged = set()

    for filename in merged_list:
        already_merged.add(os.path.basename(filename).split('_')[2].split('.')[0].lstrip('run') )

    cand_tomerge = set()

    for runnum in sim_run_list:
        if runnum in daq_run_list:
            cand_tomerge.add(runnum)
        else: 
            print('Run ' + str(runum) + ' is available in ' + SiPMFileDir + ' but not in ' + DaqFileDir)
    tobemerged = cand_tomerge - already_merged

    if (len(tobemerged) == 0):
        print("No new run to be analysed") 
    else:
        print("About to run on the following runs ")
        print(tobemerged)

    return sorted(tobemerged)



###############################################################
        
def main():
    import argparse                                                                      
    parser = argparse.ArgumentParser(description='This script runs the merging of the "SiPM" and the "Daq" daq events. \
        The option --newFiles should be used only in TB mode, has the priority on anything else, \
        and tries to guess which new files are there and merge them. \n \
        Otherwise, the user needs to provide --runNumber to run on an individual run. \
        --runNumber has priority if both sets of options are provided. \
        --runNumber will assume the lxplus default test beam file location.')
    parser.add_argument('--output', dest='outputFileName',default='output.root',help='Output file name')
    parser.add_argument('--no_merge', dest='no_merge',action='store_true',help='Do not do the merging step')           
    parser.add_argument('--runNumber',dest='runNumber',default='0', help='Specify run number. The output file name will be merged_sps2023_run[runNumber].root ')
    parser.add_argument('--newFiles',dest='newFiles',action='store_true', default=False, help='Looks for new runs in ' + SiPMFileDir + ' and ' + DaqFileDir + ', and merges them. To be used ONLY from the ideadr account on lxplus')
    
    par  = parser.parse_args()
    global doNotMerge
    doNotMerge = par.no_merge

    if par.newFiles:
        ##### build runnumber list
        rn_list = GetNewRuns()
        for runNumber in rn_list:
            if par.outputFileName == 'output.root':
                outfilename = MergedFileDir + '/' + outputFileNamePrefix + '_run' + str(runNumber) + '.root'
            print( '\n\nGoing to merge run ' + runNumber + ' and the output file will be ' + outfilename + '\n\n'  )
            allgood = doRun(runNumber, outfilename)
        return 

    allGood = 0

    if par.runNumber != '0':
        print( 'Looking for run number ' + par.runNumber)
        outfilename = par.outputFileName 
        allGood = doRun(par.runNumber,outfilename)
    else: 
        if par.inputSiPM != '0' and par.inputDaq != '0':
            print( 'Running on files ' + par.inputSiPM + ' and ' +  par.inputDaq)
            start = time.time()
            allGood = CreateBlendedFile(par.inputSiPM,par.inputDaq,par.outputFileName)
            end = time.time()
            print( 'Execution time ' + str(end-start))
        else:
            print( 'You need to provide either --inputSiPM and --inputDaq, or --runNumber. Exiting graciously.....')
            parser.print_help()
            return 

    if allGood != 0:
        print( 'Something went wrong. Please double check your options. If you are absolutely sure that the script should have worked, contact iacopo.vivarelli AT cern.ch')

############################################################################################# 

if __name__ == "__main__":    
    main()
