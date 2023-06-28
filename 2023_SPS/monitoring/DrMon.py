#!/usr/bin/env python
import sys
import getopt
import glob
import os
import re

import DrSiPMMon
import DrAuxMon
import DrBaseMon
from DrBaseMon import BLUBOLD, BOLD, BLU, RED, YELLOW, NOCOLOR

PathToData = './'

class DrMon(DrBaseMon.DrBaseMon):
  '''Data monitoring class for DualReadout 2021 Test Beam @H8  '''

  ##### DrMon method #######
  def __init__(self, fnameSiPM, fnamePMT, acqMode, maxEvts, sample, trigCut):
    '''Constructor '''
    self.fnameSiPM  = fnameSiPM    # File name for raw data of SiPMs
    self.fnamePMT   = fnamePMT     # File name for raw data of PMTs and auxiliary
    self.acqMode    = acqMode      # Acquisition mode for SiPMs
    self.maxEvts    = maxEvts      # Max number of events to process
    self.sample     = sample       # Sampling fraction
    self.trigCut    = trigCut      # Trigger cut  
    self.evtDict    = {}           # Dictionary of events
    self.hDict      = {}           # Dictionary of histograms
    self.runNum = "0"
    # last number in filename should be run number
    tmp=re.findall('\d+',fnamePMT)
    if len(tmp) != 0:
      self.runNum = tmp[-1]
    self.cmdShCuts  = {        # Mapping between command shortCuts and commands
      "help"    : self.PrintHelp,
    }

    self.drSiPMMon = DrSiPMMon.main(self.fnameSiPM, self.acqMode, self.maxEvts, self.sample)
    self.drAuxMon  = DrAuxMon.main(self.fnamePMT, self.maxEvts, self.sample, self.trigCut)

  def commander(self):
    '''Interactive commander '''
    
    self.createCanvas(1)
    while True:
      # Command
      #self.dumpHelp()
      print("\n__________________________________________________")
      line = input( 'DrMon prompt --> ' + NOCOLOR)
      pars = line.split()
      if len(pars) == 0: continue
      cmd = pars[0]
      opt = ""
      if len(pars) > 1:
        opt = pars[1]

      if   cmd == "q": print("Bye"); sys.exit(0)
      elif cmd in self.cmdShCuts:
        self.cmdShCuts[cmd]()
      elif cmd in self.drSiPMMon.cmdShCuts:  # SHORTCUTS
        self.drSiPMMon.cmdShCuts[cmd]()
      #elif cmd.isdigit():          # SHORTCUTS WITH DIGITS
        #hIdx = int(cmd)
        #if hIdx < len(self.cmdShCuts): 
          #self.cmdShCuts[ self.cmdShCutsV[hIdx] ]()
      elif cmd in self.drAuxMon.cmdShCuts:
        self.drAuxMon.cmdShCuts[cmd]()
      else:
        if self.drSiPMMon.CheckForHisto(cmd):
          self.DrawSingleHisto(cmd, opt, self.drSiPMMon.hDict)
        elif self.drAuxMon.CheckForHisto(cmd):
          self.DrawSingleHisto(cmd, opt, self.drAuxMon.hDict)
        else:
          print("Unknown Histogram")


    ##### DrMon method #######
  def PrintHelp(self):
    '''Help: shows available commands and histograms'''
    print(BLU, "Available Auxiliary Commands:", NOCOLOR)
    for cmd in self.drAuxMon.cmdShCuts:
      print(BLU, cmd, NOCOLOR)
    print("\n--------------------------------------------------")
    print(BLU, "Available SiPM Commans:", NOCOLOR)
    for cmd in self.drSiPMMon.cmdShCuts:
      print(BLU, cmd, NOCOLOR)
    print("\n--------------------------------------------------")
    print(BLU, "To exit type q", NOCOLOR)


def Usage():
  print("Read raw data from text file and create monitor histograms")
  print("Usage: DrMon.py [options]")
  print("   -f fname    Data file to analize (def=the latest data file)")
  print("   -e maxEv    Maximum numver of events to be monitored (def=inf)")  
  print("   -s sample   Analyze only one event every 'sample'")
  print("   -r runNbr   Analyze run number runNbr")
  print("   -t trigCut  Trigger cut [5=phys, 6=pede]")
  sys.exit(2)

def main(fnameSiPM, fnamePMT, acqMode, events, sample, trigCut):
  print(f'Analyzing {fnameSiPM} and {fnamePMT}')
  drMon = DrMon(fnameSiPM, fnamePMT, acqMode, events, sample, trigCut)
  #drMon.bookOthers()
  #drMon.readFile()

  return drMon
  

if __name__ == "__main__":
  # Parse command line
  fnameSiPM   = ""
  fnamePMT    = ""
  acqMode     = 0
  events      = 999999999
  sample      = 1
  trigCut     = 0
  run         = 0
  try:
    opts, args = getopt.getopt(sys.argv[1:], "hf1:f2:a:e:s:r:t:")
  except getopt.GetoptError as err:
    print(str(err))
    Usage()

  try:
    for o,a in opts:
      if    o == "-h":  Usage()
      elif  o == "-f1": fnameSiPM = a
      elif  o == "-f2": fnamePMT  = a
      elif  o == "-a":  acqMode   = int(a)
      elif  o == "-e":  events    = int(a)
      elif  o == "-s":  sample    = int(a)
      elif  o == "-t":  trigCut   = int(a)
      elif  o == "-r":  run       = int(a)
  except(AttributeError): pass

  if run > 0:
    fnameSiPM = f"Run{run}_list.dat"
    fnameSiPM = PathToData + fnameSiPM
    fnamePMT  = f"sps2021data.run{run}.txt"
    fnamePMT  = PathToData + fnamePMT
  else:
    if (len(fnameSiPM)<1) :
      list_of_SiPMfiles = glob.glob(PathToData + 'Run*_list.dat' ) 
      fnameSiPM = max(list_of_SiPMfiles, key=os.path.getctime)
    if (len(fnamePMT)<1):
      list_of_PMTfiles = glob.glob(PathToData + 'sps2021data*txt' ) 
      fnamePMT = max(list_of_PMTfiles, key=os.path.getctime)

  if not os.path.isfile(fnameSiPM):
    print(RED, "[ERROR] File ", fnameSiPM, " not found", NOCOLOR)
    sys.exit(404)
  if not os.path.isfile(fnamePMT):
    print(RED, "[ERROR] File ", fnamePMT, " not found", NOCOLOR)
    sys.exit(404)

  # Install signal handler to interrupt file reading
  #signal(SIGINT, handler)
  drMon = main(fnameSiPM, fnamePMT, acqMode, events, sample, trigCut)
  drMon.commander()
