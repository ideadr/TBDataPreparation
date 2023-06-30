#!/usr/bin/env python
import ROOT

BLUBOLD='\033[94m\033[1m'
BOLD   ='\033[1m'
BLU    ='\033[94m'
RED    ='\033[31m'
YELLOW ='\033[33m'
NOCOLOR='\033[0m'

class DrBaseMon:
  '''Data monitoring class for DualReadout 2021 Test Beam @H8  '''

  ##### DrBaseMon method #######
  def __init__():
    '''Constructor '''
    #self.fname      = fname    # File name
    #self.acqMode    = acqMode
    #self.maxEvts    = maxEvts  # Max number of events to process
    #self.sample     = sample   # Sampling fraction
    #self.evtDict    = {}       # Dictionary of events
    #self.hDict      = {}       # Dictionary of histograms
    #self.lastEv     = None     # Last DREvent object
    self.canvas     = None     # ROOT canvas
    self.canNum     = 0        # Number of pads in canvas
    self.runNum     = "0"
    # last number in filename should be run number
    tmp=re.findall('\d+',fname)
    if len(tmp) != 0:
      self.runNum = tmp[-1]
    '''
    self.cmdShCuts  = {        # Mapping between command shortCuts and commands
      "all"     : self.DrawAll,
      "board"   : self.DrawBoard,
      "pha"     : self.DrawPHA,
      "trigger" : self.DrawTrigger,
      "help"    : self.PrintHelp,
    }
    '''

  ##### DrBaseMon method #######
  def checkOverUnderFlow(self, h):
    '''Check and print out over- and underflow of histogram '''
    nbins = h.GetNbinsX()
    hname = h.GetName()
    uFlow = h.GetBinContent(0)
    oFlow = h.GetBinContent(nbins+1)
    if uFlow+oFlow > 0:
      print(BOLD)
      print(hname, ":")
      print(YELLOW)
      print("Underflow:", uFlow)
      print("Overflow :", oFlow)
      print(NOCOLOR)

  ##### DrBaseMon method #######
  def book1D(self, hname, hDict, bins, mi, ma, axTitle="", ymin=None):
    '''Utility to book histograms 1D '''
    h = ROOT.TH1I(hname, hname, bins, mi, ma) 
    h.GetXaxis().SetTitle(axTitle)
    if ymin is not None:
      h.SetMinimum(ymin)
    hDict[hname] = h
    return h

  ##### DrBaseMon method #######
  def createCanvas(self, dim):
    '''Create a canvas'''
    s="Run" + self.runNum + ": "
    if   dim == 4: 
      self.canvas = ROOT.TCanvas('c4', s+'IDEA-DR4', 0, 0, 800, 800)
      self.canvas.Divide(2,2)
    elif dim == 6: 
      self.canvas = ROOT.TCanvas('c6', s+'IDEA-DR6', 0, 0, 1000, 600)
      self.canvas.Divide(3,2)
    elif dim == 2: 
      self.canvas = ROOT.TCanvas('c2', s+'IDEA-DR2', 0, 0, 1000, 500)
      self.canvas.Divide(2,1)
    elif dim == 3: 
      self.canvas = ROOT.TCanvas('c3', s+'IDEA-DR3', 0, 0, 1500, 500)
      self.canvas.Divide(3,1)
    elif dim == 9: 
      self.canvas = ROOT.TCanvas('c9', s+'IDEA-DR9', 0, 0, 900, 900)
      self.canvas.Divide(3,3)
    elif dim == 8: 
      self.canvas = ROOT.TCanvas('c8', s+'IDEA-DR8', 0, 0, 800, 1000)
      self.canvas.Divide(2,4)
    else: 
      self.canvas = ROOT.TCanvas('c1', s+'IDEA-DR', 0, 0, 800, 600)
    self.canNum = dim

  ##### DrBaseMon method #######
  def DrawSingleHisto(self, cmd, opt, hDict=None):
    '''Draw single histogram'''
  
    if self.canNum != 1:
      self.createCanvas(1)
    if hDict is None: hDict=self.hDict
    h = None
    hname = cmd

    commandfound = True
    if hname in hDict:
      h = hDict[hname]
    elif (hasattr(self, 'histoMap')):
      if (hname in self.histoMap):
        h = hDict[ self.histoMap[hname] ]
      else: commandfound = False
    else: commandfound = False

    if not commandfound:  
      print(RED, BOLD, 'Unknown command', NOCOLOR)
      return
    if opt == "same":
      h.SetFillColor( h.GetFillColor() + 3 )
    h.Draw(opt)
    self.checkOverUnderFlow(h)
    self.canvas.Update()


