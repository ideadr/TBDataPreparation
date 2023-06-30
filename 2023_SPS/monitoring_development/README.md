# Monitoring of test beam data

Development of monitoring tool based on DrMon.py used at 2021 test beam.

This software was NOT actually used at the 2023 test beam at SPS. This directory is dedicated to the development of a combined monitoring of auxiliary detectors and SiPMs.

## Structure
### DrSiPMMon.py & DRSiPMEvent.py
New files were created which were based on the monitoring of the auxiliary detectors, but instead are responsible for the monitoring of the SiPMs. DrSiPMMon.py is the file used to start the monitoring

### DrAuxMon.py
This is the file that most closely corresponds to DrMon.py in the 2021 test beam version. A few changes have been made to adapt the script to the current structure.

### DrBaseMon.py
A base class for shared functions between DrAuxMon.py and DrSiPMMon.py for instance booking of histograms.

### DrMon.py
New main file for the project which is supposed to control both DrAuxMon and DrSiPMMon internally and call corresponding functions. This class was not developed to the end and is missing functionality.