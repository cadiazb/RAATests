#!/usr/bin/env python
# -*- coding: utf-8 -*-

import serial, time
from binascii import unhexlify

pumpPort = serial.Serial(
	port='/dev/ttyUSB1',
	baudrate = 1200,
	parity = serial.PARITY_EVEN,
	stopbits = serial.STOPBITS_ONE,
	bytesize = serial.EIGHTBITS,
	timeout = 2)
print pumpPort
pumpPort.isOpen()
#Start pump
pumpPort.write('\xE9\x01\x06\x57\x4A\x00\xE8\x00\x00\x00\xF2')
time.sleep(5)
#Stop pump
pumpPort.write('\xE9\x01\x06\x57\x4A\x00\xE8\x00\x00\x00\xF2')

WriteCommand =  'E9' + '01'  + '06'  + '57'  + '4A'  + '00'  + 'F8' +  '{:02x}'.format(1)+  '00'+ 'F2'

print WriteCommand[12:14]		
if (WriteCommand[12:14] == 'E8'):
	 WriteCommand = WriteCommand[0:13] + '00' + WriteCommand[13:]
	  
if (WriteCommand[12:14] == 'E9'):
	 WriteCommand = WriteCommand[0:13] + '01' + WriteCommand[13:]

#pumpPort.write(unhexlify(WriteCommand))
print unhexlify(WriteCommand)
print WriteCommand.encode("hex")
print '\xE9'
pumpPort.close()
