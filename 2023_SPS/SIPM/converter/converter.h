
#include "TFile.h"
#include "TH1F.h"
#include "TROOT.h"
#include "TTree.h"
#include <algorithm>
#include <array>
#include <cstring>
#include <fstream>
#include <functional>
#include <iostream>
#include <stdexcept>
#include <stdlib.h>
#include <string>
#include <vector>

#include "hardcoded.h"

// Contain info of global file
struct FileHeader {
  uint64_t acqStart;
  uint8_t vSoftware, acqMode;
  std::string dataFormatVersion;
  std::string softwareVersion;
};

// Contain info of events in file
struct FileInfo {
  std::vector<uint32_t> eventStartByte;
  uint64_t nEventsPerBoard[MAX_BOARDS] = {0};
  uint64_t nEvents = 0;
  uint64_t startAcqMs;
  uint8_t nBoards = 0;
  AcquisitionMode acquisitionMode;
};

// Single event informations (all info of all acq modes)
struct Event {
  std::array<uint16_t, NCHANNELS> lgPha;
  std::array<uint16_t, NCHANNELS> hgPha;
  std::array<uint32_t, NCHANNELS> toa;
  std::array<uint16_t, NCHANNELS> tot;
  uint64_t triggerId;
  double triggerTimeStamp;
  uint8_t boardId;
  bool operator<(const Event& lhs) const { return this->triggerId < lhs.triggerId; }
};

// Struct used only in root file writing
typedef struct {
  uint64_t acquisitionStartTimeMs, nEvents;
  uint8_t nBoards, acquisitionMode;
} RootFileInfo;

uint32_t getFileSize(const std::string&);

std::vector<char> readRawData(const std::string&, const uint32_t);

// Wrappers functions
std::vector<Event> parseData(const std::vector<char>&, const FileInfo&);
void writeDataToRoot(const std::vector<Event>&, const FileInfo&, const std::string&);

// Specific parsing functions
std::vector<Event> parseSpectroscopyData(const std::vector<char>&, const FileInfo&);
std::vector<Event> parseSpectroscopyTimingData(const std::vector<char>&, const FileInfo&);

void writeSpectroscopyToRoot(const std::vector<Event>&, const FileInfo&, const std::string&);
void writeSpectroscopyTimingToRoot(const std::vector<Event>&, const FileInfo&, const std::string&);

void logging(const std::string&, const Verbose);

// Optimized by compiler (popcount = number of bits set to 1)
inline uint8_t popcount(uint64_t x) {
  u_int8_t v = 0;
  while (x != 0) {
    x &= x - 1;
    v++;
  }
  return v;
}

void printHelp() {
  std::cout << "=================================" << std::endl;
  std::cout << "= CAEN FERS 5200 Data Converter =" << std::endl;
  std::cout << "=================================" << std::endl;
  std::cout << "\nINVOKE WITH: ./dataconverter filename.dat" << std::endl;
  std::cout << "edoardo.proserpio@gmail.com" << std::endl;
}
