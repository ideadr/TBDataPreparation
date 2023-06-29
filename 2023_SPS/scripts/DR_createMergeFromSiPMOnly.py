import DR_BlendedDaq2Root
import ROOT

global EvtOffset
EvtOffset = 0
DR_BlendedDaq2Root.EvtOffset = EvtOffset

inputFile = "/afs/cern.ch/user/i/ideadr/scratch/TB2023_H8/rawNtupleSiPM/Run29_list.root"

outputfilename = "/afs/cern.ch/user/i/ideadr/scratch/TB2023_H8/test/Run29_list_test.root"

SiPMTreeName = "SiPMData"
SiPMMetaDataTreeName = "EventInfo"
DaqTreeName = "CERNSPS2023"
SiPMNewTreeName = "SiPMSPS2023"

SiPMinfile = ROOT.TFile.Open(inputFile)
SiPMInputTree = SiPMinfile.Get(SiPMTreeName)



OutputFile = ROOT.TFile.Open(outputfilename,"recreate")

OutputFile.cd()
newSiPMTree = ROOT.TTree(SiPMNewTreeName,"SiPM info")
        
DR_BlendedDaq2Root.CloneSiPMTree(SiPMInputTree,OutputFile)

newSiPMTree.Write()
OutputFile.Close()    
