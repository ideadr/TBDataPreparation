CXX:=g++
CXXFLAGS:=$(shell root-config --cflags) $(shell root-config --libs) -O3 -mavx2 -std=c++17
INCLUDE:=converter.h hardcoded.h

readerfast: converter.cpp
	$(CXX) converter.cpp $(CXXFLAGS) -o dataconverter
