"""
    Pira.CZ RDS DECODER SCRIPT
    (C) 2015 Media Realm / Anthony Eden

    http://mediarealm.com.au/
    https://github.com/anthonyeden/Pira-FM-RDS-Decoder
 
------------------------------------------------------------------------------------------
 
    The MIT License (MIT)
    
    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.
"""

from serial import *
from threading import Thread
import io
import time
import json
import urllib

#Load Config Data for this App
try:
	ConfigData_JSON = open("config.json").read()
	ConfigData = json.loads(ConfigData_JSON)

except Exception, e:
	print
	print "##############################################"
	print "Exception loading and parsing App Config JSON File: ", e
	print "##############################################"
	print

	exit()

def tuneToStation(freq):
	# Tune to the specified station
	sio.write(unicode(freq + "*F"))
	sio.flush()
	sio.write(unicode("*R"))
	sio.flush()

# Create serial connection
ser = Serial(
	port = ConfigData['serialport'],
	baudrate = ConfigData['baudrate'],
	bytesize = EIGHTBITS,
	parity = PARITY_NONE,
	stopbits = STOPBITS_ONE,
	timeout = 0.1,
	xonxoff = 0,
	rtscts = 0,
	#interCharTimeout = None
)

changeStation = False
station = 0 # Index of the currently selected station

# Create serial connection
sio = io.TextIOWrapper(io.BufferedRWPair(ser, ser))
tuneToStation(ConfigData['Stations'][station]['freq'])

stationStartTime = time.time()

# Reset all the variables
radioTextA_endPosition = -1
radioTextA_haveEverything = False
radioTextA_text = []
radioTextA_positionsFilled = []

pi = []
for i in range(66):
	radioTextA_text.append('')

for i in range(18):
	radioTextA_positionsFilled.append(False)

for i in range(9):
	pi.append('')

radioTextA_lastChange = time.time()


while True:
	# Receive a line of RDS data from the Pira Decoder serial connection
	line = ser.readline()
	
	# Lines with errors contain dashes ("-") - ignore these lines
	# the Pira P175 does the error checking for us and replaces invalid blocks with dashes
	if line.find("-") < 0 and line.__len__() > 16:
		
		try:
			# Take the hex data and convert it into binary format
			my_hexdata = line.rstrip()
			binary = bin(int(my_hexdata, 16))[2:].zfill(64) #16 = hex, 64 = bits in line, zfill pads it out to correct length
			
			# RadioText-A = 00100 in binary
			if binary[16:21] == "00100":
				
				# Current RadioText-A Start Position
				position = int(bin(int(my_hexdata[7:8], 16))[2:].zfill(4), 2)
				
				# Check to see if this part of the RadioText string has changed since the last update
				if (radioTextA_text[position * 4] != my_hexdata[8:].decode('hex')[:1]):
					radioTextA_lastChange = time.time()
				
				radioTextA_positionsFilled[position] = True
				
				radioTextA_text[position * 4] =  my_hexdata[8:].decode('hex')[:1]
				radioTextA_text[position * 4 + 1] =  my_hexdata[8:].decode('hex')[1:2]
				radioTextA_text[position * 4 + 2] =  my_hexdata[8:].decode('hex')[2:3]
				radioTextA_text[position * 4 + 3] =  my_hexdata[8:].decode('hex')[3:4]
				
				# RadioText should be terminated by a \r line end string
				if my_hexdata[8:].decode('hex').find("\r") >= 0:
					radioTextA_endPosition = position
				
				# Check to ensure every position has been filled in
				if radioTextA_endPosition >= 0 and radioTextA_haveEverything is False:
					radioTextA_haveEverything = True
					
					# Loop over all RadioTextA positions and check to see we've got data from them
					for i in range(radioTextA_endPosition):
						if radioTextA_positionsFilled[i] is False:
							radioTextA_haveEverything = False
			
			# 00000 binary = PI (Station Name)
			elif binary[16:21] == "00000":
				piPos = int(bin(int(my_hexdata[7:8], 16))[2:].zfill(2)[2:4], 2)
				pi[piPos * 2] = my_hexdata[8:].decode('hex')[2:3]
				pi[piPos * 2 + 1] = my_hexdata[8:].decode('hex')[3:4]
				
				
			# 00101 = RadioText-B
			elif binary[14:19] == "00101":
				pass
			   
			else:
				pass
				#print binary
				#print binary[16:21]
				
		except Exception, e:
			print "--- ERROR PARSING SERIAL DATA ---"
			print e
			
	
	print "Timeout in: ", time.time() - stationStartTime - ConfigData['RDS_Timeout']
	
	
	# Check to see if we've got complete RT data and it's be static for ConfigData['RDS_HoldSecs'] seconds
	# If so, publish it and clear all buffers
	if radioTextA_lastChange <= (time.time() - ConfigData['RDS_HoldSecs']) and radioTextA_haveEverything is True:
		
		# So we know to change to the next station once this data has been sent
		changeStation = True
		
		# Stop receiving data so it doesn't get stuck in the buffer
		sio.write(unicode("*r"))
		sio.flush()
		ser.flushInput()
		print "STOPPED INCOMING DATA"
		
		# Turn lists of characters into strings
		pitext = ''. join(pi)
		rttext = ''. join(radioTextA_text)
		
		# URL Encoding for GET Request
		rttext = urllib.quote_plus(rttext)
		pitext = urllib.quote_plus(pitext)
		
		# HTTP GET Request
		try:
			print "SENDING DATA TO SERVER"
			print pitext
			print rttext
			
			print urllib.urlopen(ConfigData['Stations'][station]['uploadurl'] + '&freq=' + ConfigData['Stations'][station]['freq'] + '&ps=' + pitext + '&rt=' + rttext)
		except Exception, e:
			print "ERROR PUSHING DATA TO SERVER"
			print e
		
		# Reset all the variables
		radioTextA_endPosition = -1
		radioTextA_haveEverything = False
		radioTextA_text = []
		radioTextA_positionsFilled = []
	
		pi = []
		for i in range(66):
			radioTextA_text.append('')
	
		for i in range(18):
			radioTextA_positionsFilled.append(False)
	
		for i in range(9):
			pi.append('')
	
	
	if changeStation == True or (time.time() - stationStartTime - ConfigData['RDS_Timeout']) >= 0:
		
		if len(ConfigData['Stations']) > (station + 1):
			station = station + 1
		elif (station + 1) >= len(ConfigData['Stations']):
			station = 0
		
		# Stop receiving RDS data so it doesn't get stuck in the buffer
		sio.write(unicode("*r"))
		sio.flush()
		ser.flushInput()
		print "STOPPED INCOMING DATA"
		
		time.sleep(2)
		sio.write(unicode(ConfigData['Stations'][station]['freq'] + "*F"))
		sio.flush()
		print "CHANGED STATION TO ", ConfigData['Stations'][station]['name'], ConfigData['Stations'][station]['freq']
		
		# Reset all the variables
		radioTextA_endPosition = -1
		radioTextA_haveEverything = False
		radioTextA_text = []
		radioTextA_positionsFilled = []
	
		pi = []
		for i in range(66):
			radioTextA_text.append('')
	
		for i in range(18):
			radioTextA_positionsFilled.append(False)
	
		for i in range(9):
			pi.append('')
		
		# Take a breather
		time.sleep(5)
		
		#Reset the timeout start time to NOW
		stationStartTime = time.time()
		
		# Start requesting RDS data via serial again
		sio.write(unicode("*R"))
		sio.flush()
		print "BEGUN RDS DATA FOR ", ConfigData['Stations'][station]['name']
		changeStation = False
