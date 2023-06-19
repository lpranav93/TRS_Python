#Author : Pranav Lanka 
# 8th July 2022
#Program for automating TRS measurements using existing python fuctions and libraries

# Prerequisites : Switch on the PIMikroMove Servo
#                       1) Keep the laser switched off or at low power (the stage moves a lot during referencing could cause back reflections)
#                       2) Open the PIMikroMove App
#                       3) Choose the right stage and switch on the servo and reference it automatically
#                       4) Turn on the laser/ amp up to full power
#                       5) Run this program

#PATHS 
# PIPythonpath = 'C:/Users/pranav.lanka/Desktop/PIPython-2.3.0.3/' 
Pospath = '//FS1/Docs4/sanathana.konugolu/My Documents/TRS_Python/Position/'
PIPythonpath = '//FS1/Docs4/sanathana.konugolu/My Documents/TRS_Python/Source/PIPython-2.3.0.3/'
sourcepath = '//FS1/Docs4/sanathana.konugolu/My Documents/TRS_Python/Source/'

codepath = '//FS1/Docs4/sanathana.konugolu/My Documents/TRS_Python/'
savepath = '//FS1/Docs4/sanathana.konugolu/My Documents/TRS_Python/Out/'


# MODULES AND FUNCTIONS NEEDED FOR THE PROGRAM TO RUN
import os
import time
import ctypes as ct
from ctypes import byref
from sys import exit
from matplotlib.pyplot import *
import matplotlib.pyplot as plt
from numpy import *
from pandas import *
import json
from matplotlib.animation import FuncAnimation
from pytictoc import TicToc

t = TicToc()

os.chdir(sourcepath)
from pylablib.devices import Thorlabs # device library for Kinesis Motor (Attenuator Stepper Motor)
phlib = ct.CDLL("phlib64.dll") #DLL for PicoHarp 300 

os.chdir(PIPythonpath)
import setup
from pipython import GCSDevice, pitools  # device library for PI (Prism Rotation Stage)

# Temporary for testing
TESTdf = DataFrame()
TESTSr = Series()
#%% PARAMETERS for PICOHARP 300 (TDC COUNTING BOARD)

LIB_VERSION = "3.0" #DO NOT CHANGE
HISTCHAN = 65536 #DO NOT CHANGE
MODE_HIST = 0 #DO NOT CHANGE
FLAG_OVERFLOW = 0x0040 #DO NOT CHANGE

libVersion = ct.create_string_buffer(b"", 8) #DO NOT CHANGE
hwSerial = ct.create_string_buffer(b'1002529') #DO NOT CHANGE
hwPartno = ct.create_string_buffer(b"", 8) #DO NOT CHANGE
errorString = ct.create_string_buffer(b"", 40) #DO NOT CHANGE
resolution = ct.c_double() #DO NOT CHANGE
countRate0 = ct.c_int() #DO NOT CHANGE
countRate1 = ct.c_int() #DO NOT CHANGE
flags = ct.c_int() #DO NOT CHANGE


binning = 0 # you can change this (What is this?)
offset = 0 # time offset of PH, you can change this 
tacq = 1000 # Measurement time in millisec, you can change this
syncDivider = 1 # you can change this 
CFDZeroCross0 = 5 # you can change this (in mV)
CFDLevel0 = 94 # you can change this (in mV)
CFDZeroCross1 = 12 # you can change this (in mV)
CFDLevel1 = 75 # you can change this (in mV)


#%% OTHER (GENERAL) PARAMETERS  

PRISMSTAGENAME = 'C-863.11'  # Name of the PI Prism Rotation Stage
ATTMOTORNUM = "27260206" # Serial Number of Attenuator Stepper Motor

geometry = 'Reflectance' #Reflectance or Transmittance
SDD = 2 # Source Detector Distance (cm) (thickness of sample in transmittance and 0 in IRF)
ri = 1.5 # Refractive index of the sample 
meas = 'm' # 'i' = IRF, 'm' = MEASUREMENT AND ‘p’ = PHANTOM ###############~~~~~~~~~~###############
rep = 1 # NUMBER OF REPETITIONS YOU WANT AT EACH WAVELENGTH ###############~~~~~~~~~~###############
misc = '' # Miscellaneous comments or Remarks on the measurements (will be stored in the metadata of the output file)


Cntthrshld_low = 300000 # COUNT RATE THRESHOLD / LOWER GOAL
Cntthrshld_high = 400000 # COUNT RATE THRESHOLD / HIGHER GOAL (NOT BEING USED RIGHT NOW)

# t.tic()

if meas == 'i': #IF MEASURING IRF

    Attthrshld = 170 # ATTENUATION MAXIMUM IN DEGREES (STOPS ACQUISITION HERE EVEN IF GOAL IS NOT REACHED)
    ideg = 10  # STEP SIZE OF ATTENUATOR MOVEMENT IN DEGREES
    startpos = 50 # START ATTENUATING FROM A PREDEFINED POSITION  

elif meas == 'm': #IF MEASURING DATA

    Attthrshld = 330 # ATTENUATION MAXIMUM IN DEGREES (STOPS ACQUISITION HERE EVEN IF GOAL IS NOT REACHED)
    ideg = 5 # STEP SIZE OF ATTENUATOR MOVEMENT IN DEGREES
    startpos = 200 # START ATTENUATING FROM A PREDEFINED POSITION  

else: #IF MEASURING PHANTOMS

    Attthrshld = 330 # ATTENUATION MAXIMUM IN DEGREES (STOPS ACQUISITION HERE EVEN IF GOAL IS NOT REACHED)
    ideg = 10  # STEP SIZE OF ATTENUATOR MOVEMENT IN DEGREES
    startpos = 10 # START ATTENUATING FROM A PREDEFINED POSITION  

#Empty DataFrames and arrays
data = DataFrame()
counts = (ct.c_uint * HISTCHAN)()
dev = []

outname = 'm_test.json' ###############~~~~~~~~~~###############
prismname = 'Prism.txt' # INSERT THE FILE WITH THE PRISM STAGE POSITIONS YOU WANT TO MEASURE ###############~~~~~~~~~~###############

os.chdir(codepath)
with open(Pospath + prismname) as f:
    table1 = read_table(f, index_col=0, header=None, names=['A'],
                          lineterminator='\n')

    

#%% FUNCTIONS FOR PH (initialize, check flags and acquire)

def closeDevices():
    phlib.PH_CloseDevice(ct.c_int(0))
    exit(0)

def tryfunc(retcode, funcName):
    if retcode < 0:
        phlib.PH_GetErrorString(errorString, ct.c_int(retcode))
        print("PH_%s error %d (%s). Aborted." % (funcName, retcode,\
              errorString.value.decode("utf-8")))
        closeDevices()

def TRSacquire(tacq1):
        tryfunc(phlib.PH_ClearHistMem(ct.c_int(dev[0]), ct.c_int(0)), "ClearHistMeM")
        
        tryfunc(phlib.PH_GetCountRate(ct.c_int(dev[0]), ct.c_int(0), byref(countRate0)),\
                "GetCountRate")
        tryfunc(phlib.PH_GetCountRate(ct.c_int(dev[0]), ct.c_int(1), byref(countRate1)),\
                "GetCountRate")
        
        print("Countrate0=%d/s Countrate1=%d/s" % (countRate0.value, countRate1.value))
        
        tryfunc(phlib.PH_StartMeas(ct.c_int(dev[0]), ct.c_int(tacq1)), "StartMeas")
            
        print("\nMeasuring for %d milliseconds..." % tacq1)
        
        waitloop = 0
        ctcstatus = ct.c_int(0)
        while ctcstatus.value == 0:
            tryfunc(phlib.PH_CTCStatus(ct.c_int(dev[0]), byref(ctcstatus)), "CTCStatus")
            waitloop+=1
            
        tryfunc(phlib.PH_StopMeas(ct.c_int(dev[0])), "StopMeas")
        tryfunc(phlib.PH_GetHistogram(ct.c_int(dev[0]), byref(counts), ct.c_int(0)),\
                "GetHistogram")
        tryfunc(phlib.PH_GetFlags(ct.c_int(dev[0]), byref(flags)), "GetFlags")
        
        integralCount = 0
        for i in range(0, HISTCHAN):
            integralCount += counts[i]
        
        # print("\nWaitloop=%1d  TotalCount=%1.0lf" % (waitloop, integralCount))
        
        if flags.value & FLAG_OVERFLOW > 0:
            print("  Overflow.")
            
        return countRate0, countRate1, counts    

# This Part of the section initializes the PH board

phlib.PH_GetLibraryVersion(libVersion)
print("Library version is %s" % libVersion.value.decode("utf-8"))
if libVersion.value.decode("utf-8") != LIB_VERSION:
    print("Warning: The application was built for version %s" % LIB_VERSION)

print("Devidx     Status")
retcode = phlib.PH_OpenDevice(ct.c_int(0), hwSerial)
print("  %1d        S/N %s" % (0, hwSerial.value.decode("utf-8")))
dev.append(0)

if len(dev) < 1:
    print("No device available.")
    closeDevices()

print("Using device #%1d" % dev[0])
print("\nInitializing the device...")

tryfunc(phlib.PH_Initialize(ct.c_int(dev[0]), ct.c_int(MODE_HIST)), "Initialize")

tryfunc(phlib.PH_SetSyncDiv(ct.c_int(dev[0]), ct.c_int(syncDivider)), "SetSyncDiv")

tryfunc(phlib.PH_SetInputCFD(ct.c_int(dev[0]), ct.c_int(0), ct.c_int(CFDLevel0),\
                         ct.c_int(CFDZeroCross0)), "SetInputCFD")

tryfunc(phlib.PH_SetInputCFD(ct.c_int(dev[0]), ct.c_int(1), ct.c_int(CFDLevel1),\
                         ct.c_int(CFDZeroCross1)), "SetInputCFD")
    
tryfunc(phlib.PH_SetBinning(ct.c_int(dev[0]), ct.c_int(binning)), "SetBinning")
tryfunc(phlib.PH_SetOffset(ct.c_int(dev[0]), ct.c_int(offset)), "SetOffset")
tryfunc(phlib.PH_GetResolution(ct.c_int(dev[0]), byref(resolution)), "GetResolution")

# Note: after Init or SetSyncDiv you must allow 100 ms for valid count rate readings
time.sleep(0.1)

tryfunc(phlib.PH_GetCountRate(ct.c_int(dev[0]), ct.c_int(0), byref(countRate0)),\
        "GetCountRate")
tryfunc(phlib.PH_GetCountRate(ct.c_int(dev[0]), ct.c_int(1), byref(countRate1)),\
        "GetCountRate")

print("Resolution=%lf Countrate0=%d/s Countrate1=%d/s" % (resolution.value,\
      countRate0.value, countRate1.value))

tryfunc(phlib.PH_SetStopOverflow(ct.c_int(dev[0]), ct.c_int(1), ct.c_int(65535)),\
        "SetStopOverflow")
    
#%% ITREATIVE OPTIMIZATION OF COUNT RATE

properties = {
              "Geometry" : geometry, # METADATA DICTIONARY (ADD OTHER NECESSARY INFORMATION)
              "SDD" : SDD,                            
              "Refractive Index" : ri,                                          
              "Resolution" : resolution.value, 
              "Offset" : offset,
              "AcquisitionTime" : tacq,
              "SyncDivider" : syncDivider,
              "CFDZeroCross0" : CFDZeroCross0,
              "CFDLevel0" : CFDLevel0,
              "CFDZeroCross1" : CFDZeroCross1,
              "CFDLevel1" : CFDLevel1,
              "Meas State": meas,
              "Repetitions": rep,
              "Wavelengths":table1.index.to_list()
              }


tacq_optimize = 200 # acqusition time for optimization (ms)   
slp_t1 = 0.1 # first iteration 
slp_t2 = 0.4 # decrement
lamd = []
optpos = []
save_irfopa = 0

for irot in table1.index:
    t.tic()
    
    with GCSDevice(PRISMSTAGENAME) as pidevice:
        pidevice.ConnectRS232(comport=3, baudrate=115200)  # interface cabling properties RS232, Comport and baudrate      
        pidevice.MOV(1, float(table1[table1.index == irot].values[0])) # Move Prism Stage to the location specified in the file from LINE 35
        istage = 0  
        countRate1.value = 0
        # time.sleep(3)

    with Thorlabs.KinesisMotor(ATTMOTORNUM) as stage:
        
        stage.setup_velocity(0, 20000, 40000,  scale=True)
        stage.move_to(1919* startpos)
        stage.wait_move()
        stage.setup_velocity(0, 20000, 100000,  scale=True)
        
        while   istage < Attthrshld:    
 
            TRSacquire(tacq_optimize) 
            time.sleep(slp_t1)

            if countRate1.value < Cntthrshld_low :

                istage = istage + ideg    
                stage.move_by(1919*ideg) # initiate a move | 1919 = movement of 1 degree                
                time.sleep(slp_t1)
                TRSacquire(tacq_optimize) 

            elif  countRate1.value > Cntthrshld_high :
                stage.move_by(-1919*ideg) # initiate a move | 1919 = movement of 1 degree                
                time.sleep(slp_t2)
                istage = istage + ideg                    
                TRSacquire(tacq_optimize) 
                
            else:
                break
            
                    
            
        # stage.move_by(-1919*10)
        stage.wait_move()            
        stage.stop()

        aa = stage.get_position(scale=False)
        
        for irep in range(1,rep+1):  
            temp = []
            TRSacquire(1000) 
            for i in range(0, HISTCHAN):
                temp.append(ct.c_long(counts[i]).value)
            # data[(irot,irep)] = temp
            data.insert(loc=len(data.columns), column=str(tuple([irot,irep])), value=temp)
            
        stage.move_to(1919* 10)
        fig = figure(figsize = (8,6)) # Figure Showing the Acquired Data after each Wavelength Measured
        ax = fig.add_subplot()
         
        ax.set_xlim(6000,10000)
        ax.set_yscale('log')
        ax.set_ylabel('Counts')
        ax.set_xlabel('Time [ps]')
        ax.plot(counts)
        ax.grid(True)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5) 
        textstr = '\n'.join((
        r'$\mathrm{Wavelength(nm)}=%.2f$' % (irot, ),
        r'$\mathrm{CountRate}=%.0f$' % (countRate1.value, ),
        r'$\mathrm{Att. Pos (°)}=%.0f$' % (int(aa/1919), ),)            
            )
        ax.text(0.05, 0.95,textstr , transform=ax.transAxes, fontsize=14,
                verticalalignment='top', bbox=props)
        fig.canvas.draw()
        plt.gcf().canvas.flush_events()
        t.toc()

      
    TESTSr["tacq_opt"] = tacq_optimize
    TESTSr["CR"] = countRate1.value
    TESTSr["step_size"] = ideg
    TESTSr["start_pos"] = startpos
    TESTSr["Meas_Status"] = meas
    TESTSr["Wavelength"] = irot
    TESTSr["att_pos"] = aa/1919
    TESTSr["time_elapsed"] = t.tocvalue()
    TESTSr["sleep_time_inc"] = slp_t1
    TESTSr["sleep_time_dec"] = slp_t2
    TESTdf = concat([TESTdf, TESTSr], axis=1,ignore_index=True)      

    if save_irfopa == 1: 
        lamd.append(irot)
        optpos.append(aa/1919)
    
        # Create a DataFrame from the data
        optpos_att = {'Lamda': lamd, 'OptPos': optpos}
        IRF_OPA = DataFrame(optpos_att) # IRF optimal position for attenuator
        
        IRF_OPA.to_excel('IRF_OPA.xlsx', index=False)
    
    


data.columns =  data.columns.map(str)           
dictionaryObject = data.to_dict('list') 
supdict = {'properties' : properties,
            'results':   dictionaryObject}
with open(savepath + outname, 'w') as outfile:
    json.dump(supdict,outfile)
         
# t.toc()

fig.savefig('Plots TOF/Figure 1_sleep_time1_0.1_sleep_time2_'+str(slp_t2)+'.png')
fig.savefig('Plots TOF/Figure 2_sleep_time1_0.1_sleep_time2_'+str(slp_t2)+'.png')
fig.savefig('Plots TOF/Figure 3_sleep_time1_0.1_step_time2_'+str(slp_t2)+'.png')

FileName =  'Testing_changing_sleep time1_0.1_sleep_time2__'+str(slp_t2)+'.xlsx'
writer = ExcelWriter(savepath +FileName , engine='xlsxwriter')
TESTdf.to_excel(writer, sheet_name='Sheet1')
# writer.save()
writer.close()

# importing the required modules

closeDevices()

#%%

# import glob
# import pandas as pd
 
# # specifying the path to csv files
# path = '//FS1/Docs4/sanathana.konugolu/My Documents/TRS_Python/Out/19-6-23 collected data'
 
# # csv files in the path
# file_list = glob.glob(path + "/*.xlsx")
 
# # list of excel files we want to merge.
# # pd.read_excel(file_path) reads the 
# # excel data into pandas dataframe.
# excl_list = []
# # newrow = DataFrame()
# s = pd.Series([None])

# for file in file_list:
#     excl_list.append(pd.read_excel(file))
#     # excl_list.append(s)
 
# # concatenate all DataFrames in the list
# # into a single DataFrame, returns new
# # DataFrame.
# excl_merged = pd.concat(excl_list, ignore_index=True, axis = 1)
 
# # exports the dataframe into excel file
# # with specified name.
# excl_merged.to_excel('Testing variables_all_19-6.xlsx', index=False)

