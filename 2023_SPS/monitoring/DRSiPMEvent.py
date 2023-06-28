import struct
import numpy as np

FILE_HEADER_SIZE = 21

MAPPING_LUT = [
    0,  40, 8,  32, # 0 - 3
    1,  41, 9,  33, # 4 - 7
    2,  42, 10, 34, # 8 - 11
    3,  43, 11, 35, # 12 - 15
    4,  44, 12, 36, # 16 - 19
    5,  45, 13, 37, # 20 - 23
    6,  46, 14, 38, # 24 - 27
    7,  47, 15, 39, # 28 - 31
    24, 48, 16, 56, # 32 - 35
    25, 49, 17, 57, # 36 - 39
    26, 50, 18, 58, # 40 - 43
    27, 51, 19, 59, # 44 - 47
    28, 52, 20, 60, # 48 - 51
    29, 53, 21, 61, # 52 - 55
    30, 54, 22, 62, # 56 - 59
    31, 55, 23, 63  # 60 - 63
]

NCHANNELS = 64
EVENT_DATA_SIZE = [6, 11]
EVENT_HEADER_SIZE = [27, 27]

class DRSiPMEvent:
  ''' Class that represent a Dual Readout event at TB 2021 @H8 '''
  
  def __init__(self):
    ''' Constructor '''
    self.EventSize = 0
    self.BoardID = 0
    self.TriggerTimeStamp = 0.0
    self.TriggerID = 0
    self.ChannelMask = 0
    self.lgPha = [0]*NCHANNELS      
    self.hgPha = [0]*NCHANNELS 
    self.toa = 0
    self.tot = 0

    def __str__(self):
      """Overload of str operator (for data dump)"""
      return (
            f"\n====================NEW EVENT====================\n"
            f"Event Size \t = {self.EventSize}\n"
            f"Board ID \t = {self.BoardID}\n"
            f"Trigger Time Stamp = {self.TriggerTimeStamp}\n"
            f"Trigger ID \t = {self.TriggerID}\n"
            f"Channel Mask \t = {self.ChannelMask}\n"
            #f"low Gain Channels =  {len(np.nonzero(self.lgPha))}\n"
            #f"high Gain Channels =  {len(np.nonzero(self.hgPha))}\n"
            )   
      

# Parse the evLine and return a DREvent object
def DRdecode(evLine, acqMode):
  """Function that converts a raw data record (event) from
     binary to object oriented representation: DREvent class"""
  # Create new DREvent
  e = DRSiPMEvent()

  
  headersize = EVENT_HEADER_SIZE[acqMode]
  datasize   = EVENT_DATA_SIZE[acqMode] 

  # Split sections
  header  = evLine[:headersize]
  payload = evLine[headersize:]
	
  # Parse header
  # Currently for acquisition modes only Spectroscopy and Spectroscopy+Timing are considered which have the exact same header
  e.EventSize   = int.from_bytes(header[:2], byteorder='little')
  e.BoardID     = int.from_bytes(header[2:3], byteorder='little')
  e.TriggerTimeStamp = struct.unpack("<d", header[3:11])[0]  # TTS is a double. struct.unpack can also be used for int, but int.from_bytes makes intention clearer
  e.TriggerID   = int.from_bytes(header[11:19], byteorder='little')
  e.ChannelMask = bin(int.from_bytes(header[19:27], byteorder='little'))[2:] # [2:] bc first chars from bin() represent binary string
  numActiveChannels = e.ChannelMask.count('1')
  

  expectedEventSize = headersize + numActiveChannels*datasize
  offset = e.EventSize-expectedEventSize # for resetting read pointer if true event size does not match default event size
  
  if offset:
    return None, offset
 
  # Parse payload
  for i in range(NCHANNELS):
    pos = 6*i # byte position of channel i 
    channelID = int.from_bytes(payload[pos:pos+1], byteorder='little')
    lgPha     = int.from_bytes(payload[pos+2:pos+4], byteorder='little')
    hgPha     = int.from_bytes(payload[pos+4:pos+6], byteorder='little')
    
    if acqMode == 1:
      e.toa = int.from_bytes(payload[pos+6:pos+9], byteorder='little')
      e.tot = int.from_bytes(payload[pos+9:pos+11], byteorder='little')
    
    # Map channel to position in calo
    channelID = MAPPING_LUT[channelID] 
    
    # TODO: Understand why there are values > 4096
    if lgPha > 4096: lgPha = 4096
    if hgPha > 4096: hgPha = 4096
    
    e.lgPha[channelID] = lgPha
    e.hgPha[channelID] = hgPha
 
  return e, offset
