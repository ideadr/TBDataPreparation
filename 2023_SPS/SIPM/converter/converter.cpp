#include "converter.h"

Verbose VERBOSE = Verbose::kQuiet;

uint32_t getFileSize(const std::string& fileName) {
  std::ifstream inputStream(fileName, std::ios::binary | std::ios::ate);
  logging("Opening file: " + fileName, Verbose::kInfo);

  if (!inputStream) {
    logging("Cannot open file: " + fileName, Verbose::kError);
    exit(EXIT_FAILURE);
  }

  const uint32_t fileSize = static_cast<uint32_t>(inputStream.tellg());

  inputStream.close();
  if (inputStream.is_open()) {
    logging("Cannot close file file: " + fileName, Verbose::kError);
    exit(EXIT_FAILURE);
  }
  logging("File size: " + std::to_string(fileSize / (1024 * 1024)) + " Mb", Verbose::kInfo);
  return fileSize;
}

std::vector<char> readRawData(const std::string& fileName, const uint32_t size) {
  std::vector<char> data(size);
  std::ifstream inputStream(fileName, std::ios::binary | std::ios::in);
  if (!inputStream) {
    logging("Cannot open file: " + fileName, Verbose::kError);
    exit(EXIT_FAILURE);
  }
  logging("Reading raw data...", Verbose::kInfo);

  inputStream.read(data.data(), size);
  inputStream.close();
  if (inputStream.is_open()) {
    logging("Cannot close file file: " + fileName, Verbose::kError);
    exit(EXIT_FAILURE);
  }
  return data;
}

FileHeader getFileHeader(const std::vector<char>& rawData) {
  FileHeader header;
  uint8_t dfv1, dfv2, swv1, swv2, swv3;

  std::memcpy(&dfv1, &rawData[0], sizeof(uint8_t));
  std::memcpy(&dfv2, &rawData[1], sizeof(uint8_t));
  std::memcpy(&swv1, &rawData[2], sizeof(uint8_t));
  std::memcpy(&swv2, &rawData[3], sizeof(uint8_t));
  std::memcpy(&swv3, &rawData[4], sizeof(uint8_t));
  std::memcpy(&header.acqMode, &rawData[5], sizeof(uint8_t));
  std::memcpy(&header.acqStart, &rawData[6], sizeof(uint64_t));

  header.dataFormatVersion = std::to_string(dfv1) + "." + std::to_string(dfv2);
  header.softwareVersion = std::to_string(swv1) + "." + std::to_string(swv2) + "." + std::to_string(swv3);
  return header;
}

FileInfo getFileInfo(const std::vector<char>& rawData, const FileHeader& header) {
  FileInfo fileInfo;
  const uint64_t fileSize = rawData.size(); // Size in bytes of whole file
  uint32_t iByte = FILE_HEADER_SIZE;        // Skip bytes (header)
  uint32_t errors = 0;                      // Errors in file

  fileInfo.eventStartByte.reserve(1000000); // Reasonable number

  logging("Starting to parse file...", Verbose::kInfo);

  // Context to keep stack clean
  {
    uint8_t acquisitionMode;
    uint64_t acquisitionStart;
    std::memcpy(&acquisitionMode, &rawData[5], sizeof(uint8_t));
    std::memcpy(&acquisitionStart, &rawData[6], sizeof(uint64_t));
    switch (acquisitionMode) {
    case 1:
      fileInfo.acquisitionMode = AcquisitionMode::kSpectroscopy;
      break;
    case 2:
      fileInfo.acquisitionMode = AcquisitionMode::kTiming;
      break;
    case 3:
      fileInfo.acquisitionMode = AcquisitionMode::kSpectroscopyTiming;
      break;
    case 4:
      fileInfo.acquisitionMode = AcquisitionMode::kCounting;
      break;
    }
    logging("Acquisition mode: " + std::to_string(acquisitionMode), Verbose::kInfo);
  }

  uint64_t iEvent = 0;
  while (iByte < fileSize) {
    uint16_t eventSize;   // Current event size as per stored in file
    uint8_t boardId;      // Current board id
    uint64_t channelMask; // Byte mask of channels read out

    // Get data from binary data
    std::memcpy(&eventSize, &rawData[iByte], sizeof(uint16_t));
    std::memcpy(&boardId, &rawData[iByte + 2], sizeof(uint8_t));
    std::memcpy(&channelMask, &rawData[iByte + 19], sizeof(uint64_t));

    // How many channels are activated (usually 64)
    const uint8_t nChannlesActive = popcount(channelMask);

    // Works for spectroscopy (tricky for timing)
    // TODO: Fix timing
    const uint32_t expectedEventSize =
        EVENT_HEADER_SIZE[(int)fileInfo.acquisitionMode] + nChannlesActive * EVENTS_SIZE[(int)fileInfo.acquisitionMode];

    if (eventSize == 0) {
      logging("===============================================", Verbose::kError);
      logging("= Something went very wrong! Event size is 0! =", Verbose::kError);
      logging("===============================================", Verbose::kError);
      exit(EXIT_FAILURE);
    } else if (boardId > 15) {
      logging("================================================", Verbose::kError);
      logging("= Something went very wrong! Board ID is > 15! =", Verbose::kError);
      logging("================================================", Verbose::kError);
      exit(EXIT_FAILURE);
    }

    if (eventSize != expectedEventSize) {
      logging("Caught error in file!", Verbose::kWarn);
      logging("Event number:" + std::to_string(iEvent), Verbose::kWarn);
      logging("Error position:" + std::to_string(iByte), Verbose::kWarn);
      logging("This is a warning. Event will be skipped!", Verbose::kWarn);
      errors++;
    } else {
      // Increase count of single board
      fileInfo.nEventsPerBoard[boardId] += 1;
      // Store byte position of the start of event
      fileInfo.eventStartByte.emplace_back(iByte);
      // Increase number of boards in case a new one is found
      if (fileInfo.nBoards < boardId) {
        fileInfo.nBoards = boardId;
      }
      // Increase event counts (count events without errors)
      fileInfo.nEvents++;
    }
    // Go to next event
    iByte += eventSize;
    // Increase event count (also with errors)
    iEvent++;
  }
  // Number of boards is max id + 1
  fileInfo.nBoards += 1;

  logging("Errors found in file: " + std::to_string(errors), Verbose::kInfo);
  logging("Number of boards detected: " + std::to_string(fileInfo.nBoards), Verbose::kInfo);
  logging("Total number of events to process: " + std::to_string(fileInfo.nEvents), Verbose::kInfo);
  for (int i = 0; i < fileInfo.nBoards; ++i) {
    logging("Events in board " + std::to_string(i) + ":" + std::to_string(fileInfo.nEvents), Verbose::kInfo);
  }

  return fileInfo;
}

std::vector<Event> parseData(const std::vector<char>& rawData, const FileInfo& fileInfo) {
  logging("Starting to parse file... ", Verbose::kInfo);
  std::vector<Event> events;
  switch (fileInfo.acquisitionMode) {
  case AcquisitionMode::kSpectroscopy:
    events = parseSpectroscopyData(rawData, fileInfo);
    break;
  case AcquisitionMode::kSpectroscopyTiming:
    events = parseSpectroscopyTimingData(rawData, fileInfo);
    break;
  }
  return events;
}

void writeDataToRoot(const std::vector<Event>& eventsVector, const FileInfo& fileInfo, const std::string& fileName) {
  switch (fileInfo.acquisitionMode) {
  case AcquisitionMode::kSpectroscopy:
    writeSpectroscopyToRoot(eventsVector, fileInfo, fileName);
    break;
  case AcquisitionMode::kSpectroscopyTiming:
    writeSpectroscopyTimingToRoot(eventsVector, fileInfo, fileName);
    break;
  }
}

std::vector<Event> parseSpectroscopyData(const std::vector<char>& rawData, const FileInfo& fileInfo) {

  // Retrieve number of events
  const uint32_t nEvents = fileInfo.eventStartByte.size();
  std::vector<Event> output(nEvents);

  // Loop on events
  for (uint32_t i = 0; i < nEvents; ++i) {
    // Prepare single event
    Event event;
    // Starting byte of event
    const uint32_t startByte = fileInfo.eventStartByte[i];

    // Read and store event header data
    std::memcpy(&event.boardId, &rawData[startByte + 2], sizeof(uint8_t));
    std::memcpy(&event.triggerTimeStamp, &rawData[startByte + 3], sizeof(double));
    std::memcpy(&event.triggerId, &rawData[startByte + 11], sizeof(uint64_t));

    // 27 is event header size - 411 is event size
    const uint32_t eventDataStartByte = startByte + 27;
    // Loop on channels
    // Assume to read always 64 channels
    for (int j = 0; j < NCHANNELS; ++j) {
      uint8_t channelId;
      uint16_t lgPha, hgPha;
      // Read event data
      std::memcpy(&channelId, &rawData[eventDataStartByte + 6 * j], sizeof(uint8_t));
      std::memcpy(&lgPha, &rawData[eventDataStartByte + 6 * j + 2], sizeof(uint16_t));
      std::memcpy(&hgPha, &rawData[eventDataStartByte + 6 * j + 4], sizeof(uint16_t));
      // Map channel to position in calorimeter
      channelId = MAPPING_LUT[channelId];
      // TODO: Understand why there are values > 4096 (Hardware/Firmware problem?)
      if (lgPha > 4096) {
        lgPha = 4096;
      }
      if (hgPha > 4096) {
        hgPha = 4096;
      }
      // Store event data
      event.lgPha[channelId] = lgPha;
      event.hgPha[channelId] = hgPha;
    } // Loop on channels
    // Store event
    output[i] = event;
  } // Loop on events

  return output;
}

std::vector<Event> parseSpectroscopyTimingData(const std::vector<char>& rawData, const FileInfo& fileInfo) {
  std::vector<Event> output(fileInfo.nEvents);

  for (uint32_t i = 0; i < fileInfo.nEvents; ++i) {
    Event event;
    const uint32_t startByte = fileInfo.eventStartByte[i];

    uint8_t boardId;
    double triggerTime;
    uint64_t triggerId;

    std::memcpy(&boardId, &rawData[startByte + 2], sizeof(uint8_t));
    std::memcpy(&triggerTime, &rawData[startByte + 3], sizeof(double));
    std::memcpy(&triggerId, &rawData[startByte + 11], sizeof(uint64_t));

    event.boardId = boardId;
    event.triggerTimeStamp = triggerTime;
    event.triggerId = triggerId;

    // 27 is event header size - 795 is event size
    const uint32_t eventDataStartByte = startByte + 27;
    for (int j = 0; j < NCHANNELS; ++j) {
      uint8_t channelId;
      uint16_t lgPha, hgPha, tot;
      uint32_t toa;
      std::memcpy(&channelId, &rawData[eventDataStartByte + 12 * j], sizeof(uint8_t));
      std::memcpy(&lgPha, &rawData[eventDataStartByte + 12 * j + 2], sizeof(uint16_t));
      std::memcpy(&hgPha, &rawData[eventDataStartByte + 12 * j + 4], sizeof(uint16_t));
      std::memcpy(&toa, &rawData[eventDataStartByte + 12 * j + 6], sizeof(uint32_t));
      std::memcpy(&tot, &rawData[eventDataStartByte + 12 * j + 10], sizeof(uint16_t));
      channelId = MAPPING_LUT[channelId]; // Map channel to position in calo
      // TODO: Understand why there are values > 4096
      if (lgPha > 4096) {
        lgPha = 4096;
      }
      if (hgPha > 4096) {
        hgPha = 4096;
      }
      event.lgPha[channelId] = lgPha;
      event.hgPha[channelId] = hgPha;
      event.toa[channelId] = toa;
      event.tot[channelId] = tot;
    }
    output[i] = event;
  }
  std::sort(output.begin(), output.end());
  return output;
}

void writeSpectroscopyToRoot(const std::vector<Event>& events, const FileInfo& fileInfo, const std::string& fileName) {

  // Change extension to file name
  const std::string rootFileName = fileName.substr(0, fileName.find_last_of(".")) + ".root";

  // Create ROOT file
  logging("Creating ROOT file...", Verbose::kPedantic);
  TFile rootFile(rootFileName.c_str(), "RECREATE");
  if (!rootFile.IsOpen()) {
    logging("Cannot open ROOT file!", Verbose::kError);
    exit(EXIT_FAILURE);
  }

  // Create tree with global event informations
  TTree rootTreeInfo("EventInfo", "Informations about event");
  logging("Starting to write data to: " + rootFileName, Verbose::kInfo);

  // Temporary struct to be stored in root file
  RootFileInfo rootfileinfo;
  rootTreeInfo.Branch("FileInfo", &rootfileinfo,
                      "AcquisitionStartMs/l:NumberOfEvents:NumberOfBoards/b:AcquisitionMode");
  rootfileinfo.acquisitionStartTimeMs = fileInfo.startAcqMs;
  rootfileinfo.nEvents = fileInfo.nEvents;
  rootfileinfo.nBoards = fileInfo.nBoards;
  rootfileinfo.acquisitionMode = (int)fileInfo.acquisitionMode;
  rootTreeInfo.Fill();
  rootTreeInfo.Write();

  // Create tree with per channel informations
  TTree rootTreeEvent("SiPMData", "Data from SiPM");
  uint16_t HighGainADC[NCHANNELS];
  uint16_t LowGainADC[NCHANNELS];
  uint64_t triggerId;
  double triggerTime;
  uint8_t boardId;
  rootTreeEvent.Branch("HighGainADC", HighGainADC, "HighGainADC[64]/s", 128000);
  rootTreeEvent.Branch("LowGainADC", LowGainADC, "LowGainADC[64]/s", 128000);
  rootTreeEvent.Branch("TriggerId", &triggerId, "Triggerid/l", 128000);
  rootTreeEvent.Branch("TriggerTimeStampUs", &triggerTime, "TriggerTimeStampUs/D", 128000);
  rootTreeEvent.Branch("BoardId", &boardId, "BoardId/b", 128000);

  logging("Starting to write per channel data...", Verbose::kPedantic);
  for (const auto& event : events) {
    boardId = event.boardId;
    triggerId = event.triggerId;
    triggerTime = event.triggerTimeStamp;
    std::memcpy(HighGainADC, event.hgPha.begin(), NCHANNELS * sizeof(uint16_t));
    std::memcpy(LowGainADC, event.lgPha.begin(), NCHANNELS * sizeof(uint16_t));
    rootTreeEvent.Fill();
  }
  rootTreeEvent.AutoSave();
  logging("Finished to write data...", Verbose::kPedantic);

  // Create histograms for fast debugging
  rootFile.mkdir("Histograms");
  rootFile.cd("Histograms");

  // Per channel histograms
  std::vector<std::vector<TH1I>> histoshg(fileInfo.nBoards, std::vector<TH1I>(NCHANNELS));
  std::vector<std::vector<TH1I>> histoslg(fileInfo.nBoards, std::vector<TH1I>(NCHANNELS));

  logging("Starting to write per channel histograms...", Verbose::kPedantic);
  for (uint32_t i = 0; i < fileInfo.nBoards; ++i) {
    for (uint32_t j = 0; j < NCHANNELS; ++j) {
      const std::string titleHG = "HighGainADC Board " + std::to_string(i) + "Channel " + std::to_string(j);
      const std::string titleLG = "LowGainADC Board " + std::to_string(i) + "Channel " + std::to_string(j);
      histoslg[i][j] = TH1I(titleLG.c_str(), "LowGainADC;ADC", 4096, 0, 4095);
      histoshg[i][j] = TH1I(titleHG.c_str(), "HighGainADC;ADC", 4096, 0, 4095);
    }
  }

  // Fill histograms
  for (const auto& event : events) {
    const uint8_t bid = event.boardId;
    for (uint32_t j = 0; j < NCHANNELS; ++j) {
      histoslg[bid][j].Fill(event.lgPha[j]);
      histoshg[bid][j].Fill(event.hgPha[j]);
    }
  }

  // Write histograms to file
  for (uint32_t i = 0; i < fileInfo.nBoards; ++i) {
    for (uint32_t j = 0; j < NCHANNELS; ++j) {
      histoslg[i][j].Write();
      histoshg[i][j].Write();
    }
  }
  logging("Finished writing histograms...", Verbose::kPedantic);

  // Empty directory to store calbrations constants and data taking parameters
  rootFile.mkdir("Calibrations");
  rootFile.cd("Calibrations");

  // Create tree with calibrations
  TTree rootTreeCalibration("SiPMCalibrations", "Calibrations and settings of SiPM");

  // Write tree with calibrations
  rootTreeCalibration.Write();

  // Close file
  rootFile.Close();
  if (rootFile.IsOpen()) {
    logging("Cannot close ROOT file!", Verbose::kError);
    exit(EXIT_FAILURE);
  }
}

void writeSpectroscopyTimingToRoot(const std::vector<Event>& events, const FileInfo& fileInfo,
                                   const std::string& fname) {
  const std::string rootfname = fname.substr(0, fname.find_last_of(".")) + ".root";

  TFile rootFile(rootfname.c_str(), "RECREATE");

  TTree rootTreeInfo("EventInfo", "Informations about event");

  RootFileInfo rootfileinfo;
  rootTreeInfo.Branch("FileInfo", &rootfileinfo,
                      "AcquisitionStartMs/l:NumberOfEvents:NumberOfBoards/b:AcquisitionMode");
  rootfileinfo.acquisitionStartTimeMs = fileInfo.startAcqMs;
  rootfileinfo.nEvents = fileInfo.nEvents;
  rootfileinfo.nBoards = fileInfo.nBoards;
  rootfileinfo.acquisitionMode = (int)fileInfo.acquisitionMode;
  rootTreeInfo.Fill();
  rootTreeInfo.Write();

  TTree rootTreeEvent("SiPMData", "Data from SiPM");
  uint16_t HighGainADC[NCHANNELS];
  uint16_t LowGainADC[NCHANNELS];
  uint32_t Toa[NCHANNELS];
  uint16_t Tot[NCHANNELS];
  uint64_t triggerId;
  double triggerTime;
  uint8_t boardId;
  rootTreeEvent.Branch("HighGainADC", HighGainADC, "HighGainADC[64]/s", 128000);
  rootTreeEvent.Branch("LowGainADC", LowGainADC, "LowGainADC[64]/s", 128000);
  rootTreeEvent.Branch("TimeOfArrival", LowGainADC, "Toa[64]/i", 128000);
  rootTreeEvent.Branch("TimeOverThreshold", LowGainADC, "Tot[64]/s", 128000);
  rootTreeEvent.Branch("TriggerId", &triggerId, "Triggerid/l", 128000);
  rootTreeEvent.Branch("TriggerTimeStampUs", &triggerTime, "TriggerTimeStampUs/D", 128000);
  rootTreeEvent.Branch("BoardId", &boardId, "BoardId/b", 128000);

  for (const auto& event : events) {
    boardId = event.boardId;
    triggerId = event.triggerId;
    triggerTime = event.triggerTimeStamp;
    std::memcpy(HighGainADC, event.hgPha.begin(), NCHANNELS * sizeof(uint16_t));
    std::memcpy(LowGainADC, event.lgPha.begin(), NCHANNELS * sizeof(uint16_t));
    std::memcpy(Toa, event.toa.begin(), NCHANNELS * sizeof(uint32_t));
    std::memcpy(Tot, event.tot.begin(), NCHANNELS * sizeof(uint16_t));
    rootTreeEvent.Fill();
  }
  rootTreeEvent.AutoSave();

  rootFile.mkdir("Histograms");
  rootFile.cd("Histograms");

  std::vector<std::vector<TH1I>> histoslg(fileInfo.nBoards, std::vector<TH1I>(NCHANNELS));
  std::vector<std::vector<TH1I>> histoshg(fileInfo.nBoards, std::vector<TH1I>(NCHANNELS));
  std::vector<std::vector<TH1I>> histostot(fileInfo.nBoards, std::vector<TH1I>(NCHANNELS));
  std::vector<std::vector<TH1I>> histostoa(fileInfo.nBoards, std::vector<TH1I>(NCHANNELS));

  for (uint32_t i = 0; i < fileInfo.nBoards; ++i) {
    for (uint32_t j = 0; j < NCHANNELS; ++j) {
      const std::string titleHG = "HighGainADC Board " + std::to_string(i) + "Channel " + std::to_string(j);
      const std::string titleLG = "LowGainADC Board " + std::to_string(i) + "Channel " + std::to_string(j);
      const std::string titleTOT = "TotTDC Board " + std::to_string(i) + "Channel " + std::to_string(j);
      const std::string titleTOA = "ToaTDC Board " + std::to_string(i) + "Channel " + std::to_string(j);
      histoslg[i][j] = TH1I(titleLG.c_str(), "LowGainADC;ADC", 4096, 0, 4095);
      histoshg[i][j] = TH1I(titleHG.c_str(), "HighGainADC;ADC", 4096, 0, 4095);
      histostot[i][j] = TH1I(titleHG.c_str(), "TotTDC;TDC", 4096, 0, 4095);
      histostoa[i][j] = TH1I(titleHG.c_str(), "ToaTDC;TDC", 4096, 0, 4095);
    }
  }

  for (const auto& event : events) {
    uint8_t bid = event.boardId;
    for (int j = 0; j < NCHANNELS; ++j) {
      histoslg[bid][j].Fill(event.lgPha[j]);
      histoshg[bid][j].Fill(event.hgPha[j]);
      histostot[bid][j].Fill(event.tot[j]);
      histostoa[bid][j].Fill(event.toa[j]);
    }
  }

  for (int i = 0; i < fileInfo.nBoards; ++i) {
    for (int j = 0; j < NCHANNELS; ++j) {
      histoslg[i][j].Write();
      histoshg[i][j].Write();
      histostot[i][j].Write();
      histostoa[i][j].Write();
    }
  }

  rootFile.mkdir("Calibrations");
  rootFile.cd("Calibrations");

  TTree rootTreeCalibration("SiPMCalibrations", "Calibrations and settings of SiPM");

  rootTreeCalibration.Write();

  // Close file
  rootFile.Close();
  if (rootFile.IsOpen()) {
    logging("Cannot close ROOT file!", Verbose::kError);
    exit(EXIT_FAILURE);
  }
}

void logging(const std::string& message, const Verbose level) {
  if ((int)level <= (int)VERBOSE || VERBOSE == Verbose::kPedantic) {
    switch (level) {
    case Verbose::kInfo:
      std::cout << "[INFO]:    " << message << std::endl;
      break;
    case Verbose::kWarn:
      std::cout << "[WARNING]: " << message << std::endl;
      break;
    case Verbose::kError:
      std::cout << "[ERROR]:   " << message << std::endl;
      break;
    }
  }
}

int main(int argc, char const* argv[]) {
  if (argc < 2) {
    logging("Missing file name", Verbose::kError);
    printHelp();
    exit(EXIT_FAILURE);
  }

  if (argc > 2) {
    for (int i = 0; i < argc; ++i) {
      const std::string verboseLevel = argv[i];
      if (verboseLevel == "v") {
        VERBOSE = Verbose::kError;
      } else if (verboseLevel == "vv") {
        VERBOSE = Verbose::kWarn;
      } else if (verboseLevel == "vvv") {
        VERBOSE = Verbose::kInfo;
      } else if (verboseLevel == "vvvv") {
        VERBOSE = Verbose::kPedantic;
      } else if (verboseLevel == "V") {
        VERBOSE = Verbose::kPedantic;
      } else {
        VERBOSE = Verbose::kQuiet;
      }
    }
  }
  const std::string fileName = argv[1];

  const uint32_t fileSizeBytes = getFileSize(fileName);

  // Read all file
  const std::vector<char> rawData = readRawData(fileName, fileSizeBytes);

  // Get file header (file size, starting time, ...)
  const FileHeader header = getFileHeader(rawData);

  // Get file info (nBoards, nEvents, acqMode, ...)
  const FileInfo fileInfo = getFileInfo(rawData, header);

  // Parse data
  const std::vector<Event> events = parseData(rawData, fileInfo);

  writeDataToRoot(events, fileInfo, fileName);
  return 0;
}
