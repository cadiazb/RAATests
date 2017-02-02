#!/usr/bin/env python
# -*- coding: utf-8 -*-

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject, Gdk
from gpiozero import LED
import sys
import subprocess, time, serial
from binascii import unhexlify

class PeristalticPump:
  
    def __init__(self):
	self.FlowRate = 2
	self.Period = 3
	self.TimeON = 2
	self.Status = 'Idle'
	self.WriteCommand = ''
	self.ReadCommand = '\xE9\x01\x02\x52\x4A\xF2'
	self.PumpSerialAddress = '01';
	self.PumpON = '00'
	self.PurgeTimeON = 0
	
	#Create serial port communication
	self.SerialPort = serial.Serial(
	      port='/dev/ttyUSB0',
	      baudrate = 1200,
	      parity = serial.PARITY_EVEN,
	      stopbits = serial.STOPBITS_ONE,
	      bytesize = serial.EIGHTBITS,
	      timeout = 2)
	self.SerialPort.isOpen()
	
    def SetFlowRate(self, NewFlowRate):
	if (NewFlowRate >= 0 and NewFlowRate <= 100):
	  self.FlowRate = NewFlowRate
	  
    def PowerON(self):
	self.PumpON = '01'
	self.BuildSerialCommand()
	self.SerialPort.write(unhexlify(self.WriteCommand))
	self.Status = 'Pumping'
	
    def PowerOFF(self):
	self.PumpON = '00'
	self.BuildSerialCommand()
	self.SerialPort.write(unhexlify(self.WriteCommand))
	self.Status = 'Idle'
	
    def Purge(self):
	self.PumpON = '03'
	self.BuildPurgeSerialCommand()
	self.SerialPort.write(unhexlify(self.WriteCommand))
	self.Status = 'Purging'
	
    def BuildSerialCommand(self):
      flowRateHex = "{:04x}".format(int(self.FlowRate * 10))
      fcr = int(self.PumpSerialAddress,16) ^ int("06", 16) ^ int("57", 16) ^ int("4A", 16) ^ int(flowRateHex[0:1],16) ^ int(flowRateHex[2:],16) ^ int("00", 16) ^ int(self.PumpON, 16) ^ int("00", 16)
	  
      self.WriteCommand = 'E9' + self.PumpSerialAddress + '06' + '57' + '4A' + flowRateHex[0:2] + flowRateHex[2:] + self.PumpON + '00' + '{:02x}'.format(fcr)
		
      if (self.WriteCommand[12:14] == 'E8'):
	  self.WriteCommand = self.WriteCommand[0:13] + '00' + self.WriteCommand[13:]
	  
      if (self.WriteCommand[12:14] == 'E9'):
	  self.WriteCommand = self.WriteCommand[0:13] + '00' + self.WriteCommand[13:]
	  
    def BuildPurgeSerialCommand(self):
      flowRateHex = "{:04x}".format(int(8 * 10))
      fcr = int(self.PumpSerialAddress,16) ^ int("06", 16) ^ int("57", 16) ^ int("4A", 16) ^ int(flowRateHex[0:1],16) ^ int(flowRateHex[2:],16) ^ int("00", 16) ^ int(self.PumpON, 16) ^ int("00", 16)
	  
      self.WriteCommand = 'E9' + self.PumpSerialAddress + '06' + '57' + '4A' + flowRateHex[0:2] + flowRateHex[2:] + self.PumpON + '00' + '{:x}'.format(fcr)
    
	
class WastePump:
  
    def __init__(self):
	self.FlowRate = 0
	self.Period = 1
	self.TimeON = 0.5
	self.Status = 'Idle'
	
class BathStatus:
  
    def __init__(self):
	self.CurrentTemperature = subprocess.check_output("sudo GetTemperature", shell=True)
	
    def GetTemperature(self):
	try:
	    self.CurrentTemperature = subprocess.check_output("sudo GetTemperature", shell=True)
	    return True
	except ValueError:
	    return True
	
class Thermostat:
  
    def __init__(self, gtkWindow):
	self.TemperatureSetPoint = 20
	self.ActualTemperature = 25
	self.Power = False
	self.ManualPower = gtkWindow.wg.ThermostatManualPower_checkbutton.get_active()
	self.StatusCode = 0
	self.WaterIsLow = False
	self.StatusMessage = 'System OK'
	self.RefillPump = LED(20)
	self.RefillPumpTimeON = 5
	self.RefillPumpPumping = False
	
	#Make sure refill pump is OFF on startup
	self.RefillPumpOFF()
	
	#Create timer to update system
	GObject.timeout_add_seconds(10, self.ThermostatUpdate)
	
	#Create serial port communication
	self.SerialPort = serial.Serial(port='/dev/ttyUSB0', baudrate = 19200, timeout = 2)
	self.SerialPort.isOpen()
	self.ThermostatUpdate()
	
    def __del__(self):
	self.SerialPort.close()
	print 'Serial port closed'
	
    def SetTemperature(self, newSetPoint):
	self.SerialPort.write('SS ' + str(newSetPoint) + '\r')
	time.sleep(0.1)
	print self.SerialPort.readline()
	self.ThermostatUpdate()
	
    def PowerON(self):
	if (self.Power):
	    self.SerialPort.write('SO 1\r')
	else:
	    self.SerialPort.write('SO 0\r')
	    
	self.SerialPort.readline()
	
    def RefillPumpON(self):
	#Pin signal is inverted in external circuit
	self.RefillPump.off()
	self.RefillPumpPumping = True
	
    def RefillPumpOFF(self):
	self.RefillPump.on()
	self.RefillPumpPumping = False
	
    def ThermostatClearFault(self):
	self.SerialPort.write('SUFS\r')
	time.sleep(0.1)
	tmpRes = self.SerialPort.readline()
	
    def ThermostatUpdate(self):
	#Get Unit On status
	self.SerialPort.write('RO\r')
	time.sleep(0.04)
	tmpRes = self.SerialPort.read(2)
	self.Power = bool(tmpRes == '1\r')
	
	#Get actual temperature
	self.SerialPort.write('RT\r')
	time.sleep(0.04)
	self.ActualTemperature = self.SerialPort.readline()
	
	#Get set point from thermostat
	self.SerialPort.write('RS\r')
	time.sleep(0.04)
	self.TemperatureSetPoint = self.SerialPort.readline()

	#Get fault status
	self.SerialPort.write('RUFS\r')
	time.sleep(0.04)
	self.StatusCode = self.SerialPort.readline()
	self.FaultStatusMessageUpdate()
	return True
      
    def FaultStatusMessageUpdate(self):
	tmpCodes = [int(i) for i in self.StatusCode.split()]
	tmpBinaryV3 = list(bin(tmpCodes[2]))
	tmpBinaryV3 = [0] * (8-len(tmpBinaryV3)+2) + map(int,tmpBinaryV3[2:])
	if (self.WaterIsLow):
	    print("Water is low")
	if (tmpBinaryV3[7]):
	    self.StatusMessage = 'Code ' + ''.join(str(e) for e in tmpBinaryV3) + ' - Low Level Warning'
	    self.WaterIsLow = True
	   
	if (tmpBinaryV3[4]):
	    self.StatusMessage = 'Code ' + ''.join(str(e) for e in tmpBinaryV3) + ' - Low Level Fault'
	    self.WaterIsLow = True
	    
	if (not(tmpBinaryV3[7]) and not(tmpBinaryV3[4])):
	    self.StatusMessage = 'Code ' + ''.join(str(e) for e in tmpBinaryV3) + ' - OK'
	    if (self.WaterIsLow):
		print("Thermostat cleared fault")
	   # self.WaterIsLow = False
	
	
class DataLogger:
  
    def __init__(self):
	self.StartLogging = False
	self.SaveFolder = '/home/pi/Github/AgingTests/Data'
	self.AutoFileName = True
	self.FileName = 'AgingTest_20160425'
	  
	
class widgetIDs(object):
  
    def __init__(self, gtkWindow):
	self.ControlPanel = gtkWindow.glade.get_object("ControlPanel")
	
	self.peristalticPeriodEntry = gtkWindow.glade.get_object("peristalticPeriodEntry")
	self.peristalticTimeOnEntry = gtkWindow.glade.get_object("peristalticTimeOnEntry")
	self.peristalticFlowEntry = gtkWindow.glade.get_object("peristalticFlowEntry")
	self.peristalticStateLabel = gtkWindow.glade.get_object("peristalticStateLabel")
	self.peristalticStepTimeLabel = gtkWindow.glade.get_object("peristalticStepTimeLabel")
	self.peristalticPower_button = gtkWindow.glade.get_object("peristalticPower_button")
	self.peristalticPurge_button = gtkWindow.glade.get_object("peristalticPurge_button")
	
	#self.thermostatTempEntry = gtkWindow.glade.get_object("thermostatTempEntry")
	#self.thermostatTempLabel = gtkWindow.glade.get_object("thermostatTempLabel")
	#self.ThermostatManualPower_checkbutton = gtkWindow.glade.get_object("ThermostatManualPower_checkbutton")
	#self.ThermostatManualPower_button = gtkWindow.glade.get_object("ThermostatManualPower_button")
	#self.thermostatPowerStatus_label = gtkWindow.glade.get_object("thermostatPowerStatus_label")
	#self.ThermostatRefillPumpEntry = gtkWindow.glade.get_object("ThermostatRefillPumpEntry")
	#self.ThermostatRefillPumpButton = gtkWindow.glade.get_object("ThermostatRefillPumpButton")
	#self.thermostatFaultStatus_label = gtkWindow.glade.get_object("thermostatFaultStatus_label")
	
	#self.wastePumpPeriodEntry = gtkWindow.glade.get_object("wastePumpPeriodEntry")
	#self.wastePumpTimeOnEntry = gtkWindow.glade.get_object("wastePumpTimeOnEntry")
	#self.wastePumpStateLabel = gtkWindow.glade.get_object("wastePumpStateLabel")
	#self.wastePumpStepTimeRead = gtkWindow.glade.get_object("wastePumpStepTimeRead")
	
	self.dataLogPower_button = gtkWindow.glade.get_object("dataLogPower_button")
	self.dataLogChooseFolder = gtkWindow.glade.get_object("dataLogChooseFolder")
	self.dataLogAutoName_checkbutton = gtkWindow.glade.get_object("dataLogAutoName_checkbutton")
	self.dataLogFileNameEntry = gtkWindow.glade.get_object("dataLogFileNameEntry")
	
	self.messageLine = gtkWindow.glade.get_object("messageLine")
	self.BathTemperatureLabel = gtkWindow.glade.get_object("BathTemperatureLabel")
	self.MasterPower_button = gtkWindow.glade.get_object("MasterPower_button")
	#self. = gtkWindow.glade.get_object("")
  
class AgingSystemControl:

    def __init__(self):
        self.gladefile = "DeviceAgingControl.glade" 
        self.glade = Gtk.Builder()
        self.glade.add_from_file(self.gladefile)
        self.glade.connect_signals(self)
        
        #Create widget wtrusture
        self.wg = widgetIDs(self)
        self.wg.ControlPanel = self.glade.get_object("ControlPanel")
        self.wg.ControlPanel.show_all()
	self.wg.ControlPanel.connect("delete-event", Gtk.main_quit)
	#print(dir(self.glade.get_object("ThermostatManualPower_button").props))
	
	
	#Create Peristaltic pump object
	self.pPump = PeristalticPump()
	self.wg.peristalticPeriodEntry.props.text = str(self.pPump.Period)
	self.wg.peristalticTimeOnEntry.props.text = str(self.pPump.TimeON)
	self.wg.peristalticFlowEntry.props.text = str(self.pPump.FlowRate)
	self.wg.peristalticPower_button.connect("notify::active", self.peristalticPower_button_callback)
	self.wg.peristalticFlowEntry.connect("activate", self.peristalticFlowEntry_callback, self.wg.peristalticFlowEntry)
	self.wg.peristalticTimeOnEntry.connect("activate", self.peristalticTimeOnEntry_callback, self.wg.peristalticTimeOnEntry)
	self.wg.peristalticPeriodEntry.connect("activate", self.peristalticPeriodEntry_callback, self.wg.peristalticPeriodEntry)
	self.wg.peristalticPurge_button.connect("toggled", self.peristalticPurge_button_callback)
	
	#Create waste pump object
	#self.wPump = PeristalticPump()
	#self.wg.wastePumpPeriodEntry.props.text = str(self.wPump.Period)
	#self.wg.wastePumpTimeOnEntry.props.text = str(self.wPump.TimeON)
	
	#Create bath status object
	self.agingBath = BathStatus()
	
	#Create Thermostat object
	#self.thermo = Thermostat(self)
	#self.wg.thermostatTempEntry.props.text = str(self.thermo.TemperatureSetPoint)
	#self.wg.ThermostatRefillPumpEntry.props.text = str(self.thermo.RefillPumpTimeON)
	#self.wg.ThermostatManualPower_checkbutton.connect("toggled", self.ThermostatManualPower_callback)
	#self.wg.thermostatTempEntry.connect("activate", self.ThermostatTempEntry_callback, self.wg.thermostatTempEntry)
	#self.wg.ThermostatManualPower_button.connect("notify::active", self.ThermostatManualPower_button_callback)
	#self.wg.ThermostatRefillPumpButton.connect("clicked", self.ThermostatRefillPumpButton_callback)
	#self.wg.ThermostatRefillPumpEntry.connect("activate", self.ThermostatRefillPumpEntry_callback, self.wg.ThermostatRefillPumpEntry)
	
	#Create data logger object
	self.dLogger = DataLogger()
	#print(dir(self.wg.dataLogChooseFolder.props))
	self.dLogger.AutoFileName = self.wg.dataLogAutoName_checkbutton.get_active()
	self.wg.dataLogChooseFolder.set_filename(self.dLogger.SaveFolder)
	#Create timer to log every minute
	GObject.timeout_add_seconds(15, self.LogData)
	
	#connections
	self.wg.dataLogAutoName_checkbutton.connect("toggled", self.AutoFileNameCheckButton_callback)
	self.wg.dataLogPower_button.connect("notify::active", self.DataLogPower_button_callback)
	self.wg.dataLogChooseFolder.connect("selection-changed", self.DataLogChooseFolder_callback)
	
	#Create timer to update system
	self.Timer_Window_Update = GObject.timeout_add_seconds(1, self.WindowUpdate)
	
	#Create timer to check for low level warning
	#self.Timer_CheckLowLevelWarning = GObject.timeout_add_seconds(60, self.CheckLowLevelWarning)
	
	#Create timer to turn peristaltic ON/OFF when thermostat is ON and at temp whenruning just PBS
	#GObject.timeout_add_seconds(300, self.PeristalticAutoPower)
	
	#Create timer to turn peristaltic pump ON when running aging AgingTest with H2O2
	#self.Timer_PeristalticAutoON = GObject.timeout_add_seconds(60 * (self.pPump.Period - self.pPump.TimeON), self.PeristalticAutoON)
	
	#Create timer to refill aging bath if necessary
	#GObject.timeout_add_seconds(300, self.PeristalticAutoPurge)
	
    #Define general use methods
    def is_number(self, s):
	try:
	    float(s)
	    return True
	except ValueError:
	    return False

    #Define callbacks for peristaltic pump
    def peristalticPower_button_callback(self, switch, gparam):
	if switch.get_active():
	    self.pPump.PowerON()
	    
	else:
	    self.pPump.PowerOFF()
	    
	self.WindowUpdate()
	
    def peristalticFlowEntry_callback(self, widget, entry):
	tmpText = entry.get_text()
	if self.is_number(tmpText):
	    if (float(tmpText) >= 0 and float(tmpText) <= 100):
		self.pPump.FlowRate = int(tmpText)
		if (self.pPump.PumpON == '01'):
		    self.pPump.PowerON()
		    
	print self.pPump.FlowRate
	self.WindowUpdate()
	
    def peristalticTimeOnEntry_callback(self, widget, entry):
	tmpText = entry.get_text()
	if self.is_number(tmpText):
	    if (float(tmpText) >= 0):
		self.pPump.TimeON = float(tmpText)
		    
	print self.pPump.TimeON
	self.WindowUpdate()
	
    def peristalticPeriodEntry_callback(self, widget, entry):
	tmpText = entry.get_text()
	if self.is_number(tmpText):
	    if (float(tmpText) >= 0):
		self.pPump.Period = float(tmpText)
		    
	print self.pPump.Period
	self.WindowUpdate()
	
    def peristalticPurge_button_callback(self, button):
	if button.get_active():
	    self.pPump.Purge()
	else:
	    if self.wg.peristalticPower_button.get_active():
		self.pPump.PowerON()
	    
	    else:
		self.pPump.PowerOFF()
	    
	self.WindowUpdate()
	
    def PeristalticAutoPower(self):
	if (self.thermo.Power and float(self.thermo.ActualTemperature[0:4]) > 80):
	    self.pPump.PowerON()
	else:
	    self.pPump.PowerOFF()
	    
	return True
    
    def PeristalticAutoON(self):
	GObject.source_remove(self.Timer_PeristalticAutoON)
	if (self.thermo.Power and float(self.thermo.ActualTemperature[0:4]) > 80):
	    self.wg.peristalticPower_button.set_active(True)
	    GObject.timeout_add_seconds(60 * self.pPump.TimeON, self.PeristalticAutoOFF)
	    self.Timer_PeristalticAutoON = GObject.timeout_add_seconds(60 * self.pPump.Period, self.PeristalticAutoON)
	else:
	    self.Timer_PeristalticAutoON = GObject.timeout_add_seconds(60 * (self.pPump.Period - self.pPump.TimeON), self.PeristalticAutoON)
	
	self.WindowUpdate()
	    
    def PeristalticAutoOFF(self):
	#self.wg.peristalticPower_button.set_active(False)
	
	self.WindowUpdate()
      
    #def PeristalticAutoPurge(self):
	#if (self.thermo.Power and float(self.thermo.ActualTemperature[0:4]) > 90 and float(self.agingBath.CurrentTemperature[0:4]) < 84):
	    #self.pPump.PurgeTimeOn = 
	    #self.pPump.Purge()
	    #time.sleep(
	#else:
	    #self.pPump.PowerOFF()
	    
	#return True
    
    #Define callbacks for thermostat module
    #def ThermostatManualPower_callback(self, button):
	#self.thermo.ManualPower = button.get_active()
	#self.wg.ThermostatManualPower_button.set_active(self.thermo.Power)
	#self.wg.ThermostatManualPower_button.props.visible = button.get_active()

    #def ThermostatManualPower_button_callback(self, switch, gparam):
	#self.thermo.Power = switch.get_active()
	#self.thermo.PowerON()
	#self.WindowUpdate()
	
    #def ThermostatTempEntry_callback(self, widget, entry):
	#tmpText = entry.get_text()
	#if self.is_number(tmpText):
	    #if (float(tmpText) >= 20 and float(tmpText) <= 101):
		#self.thermo.SetTemperature(float(tmpText))
		
	#self.wg.thermostatTempEntry.props.text = str(self.thermo.TemperatureSetPoint)
	#self.WindowUpdate()
	
    #def ThermostatRefillPumpEntry_callback(self, widget, entry):
	#tmpText = entry.get_text()
	#if self.is_number(tmpText):
	    #if (float(tmpText) >= 1 and float(tmpText) <= 60):
		#self.thermo.RefillPumpTimeON = int(tmpText)
		
	#self.wg.ThermostatRefillPumpEntry.props.text = str(self.thermo.RefillPumpTimeON)
	#self.WindowUpdate()
	
    #def ThermostatRefillPumpButton_callback(self, button):
      #self.thermo.RefillPumpON()
      #GObject.timeout_add_seconds(self.thermo.RefillPumpTimeON, self.thermo.RefillPumpOFF)
      #time.sleep(1)
      #GObject.timeout_add_seconds(self.thermo.RefillPumpTimeON, self.thermo.ThermostatClearFault)
      #print("Refill button callback cleared fault")
      #self.thermo.WaterIsLow = False
    
    #def ThermostatRefillTank(self):
      #self.thermo.RefillPumpON()
      #GObject.timeout_add_seconds(self.thermo.RefillPumpTimeON, self.thermo.RefillPumpOFF)
      #time.sleep(1)
      #GObject.timeout_add_seconds(self.thermo.RefillPumpTimeON, self.thermo.ThermostatClearFault)
      #print("Auto refill cleared fault")
      #self.thermo.WaterIsLow = False
      
    #def CheckLowLevelWarning(self):
	#if (self.thermo.WaterIsLow and self.thermo.Power):
	    #self.ThermostatRefillTank()
	    #print("Refilled tank")
	#return True
	    
    #Define callbacks for data logging module
    def DataLogPower_button_callback(self, switch, gparam):
	if (switch.get_active()):
	  self.dLogger.FileName = 'AgingTest_' + time.strftime("%Y%m%d_%H%M%S") + '.txt'
	  print self.dLogger.FileName
	self.dLogger.StartLogging = switch.get_active()
	
    def AutoFileNameCheckButton_callback(self, button):
	self.dLogger.AutoFileName = button.get_active()
	self.wg.dataLogFileNameEntry.props.visible = not button.get_active()
	
    def DataLogChooseFolder_callback(self, button):
	self.dLogger.SaveFolder =  self.wg.dataLogChooseFolder.get_filename()
	    
	  
    #Function to periodically update window
    def WindowUpdate(self):
	try:
	    #Bath status
	    self.agingBath.GetTemperature()
	    self.wg.BathTemperatureLabel.props.label = self.agingBath.CurrentTemperature[0:4] + ' C'
	
	    #Thermostat
	    #self.wg.thermostatTempLabel.props.label = str(self.thermo.ActualTemperature)
	    #self.wg.ThermostatManualPower_button.props.visible = self.thermo.ManualPower
	    #self.wg.ThermostatManualPower_button.props.state = self.thermo.Power
	    #if (self.thermo.Power):
		#self.wg.thermostatPowerStatus_label.props.label = 'ON'
		#self.wg.thermostatPowerStatus_label.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.0, 1.0, 0.0, 1.0))
	    #else:
		#self.wg.thermostatPowerStatus_label.props.label = 'OFF'
		#self.wg.thermostatPowerStatus_label.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1.0, 0.0, 0.0, 1.0))
	    #self.wg.thermostatFaultStatus_label.props.label = self.thermo.StatusMessage
	
	
	    #Peristaltic pump
	    self.wg.peristalticStateLabel.props.label = self.pPump.Status
	    #self.wg.peristalticPower_button.state = ((self.pPump.PumpON == '01' or self.pPump.PumpON == '03'))
	
	
	    #Waste pump
	    #self.wg.wastePumpStateLabel.props.label = self.wPump.Status
	
	    #Data logging
	    self.wg.dataLogPower_button.set_active(self.dLogger.StartLogging)
	    self.wg.dataLogFileNameEntry.props.visible = not self.dLogger.AutoFileName
	    return True
	except ValueError:
	    return True
    
    #Function to log data
    def LogData(self):
	if (self.dLogger.StartLogging):
	  tmpFileName = self.dLogger.SaveFolder + '/' + self.dLogger.FileName
	  tmpLogFile = open(tmpFileName, 'a+')
	  #tmpLogFile.write(time.strftime("%Y%m%d_%H%M%S") + ' \t' + str(self.thermo.ActualTemperature[0:4]) + '\t' + str(self.agingBath.CurrentTemperature[0:4]) + '\t' + self.pPump.Status + '\n')
	  tmpLogFile.write(time.strftime("%Y%m%d_%H%M%S") + ' \t' + str(00.00) + '\t' + str(self.agingBath.CurrentTemperature[0:4]) + '\t' + self.pPump.Status + '\n')
	  tmpLogFile.close()
	  
	return True

if __name__ == "__main__":
    try:
        win = AgingSystemControl()
	Gtk.main()
    except KeyboardInterrupt:
        pass

