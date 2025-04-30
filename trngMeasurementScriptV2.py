'''
************************************************************
- Author: Sükrü Saygili
- Date: 27/04/2025
- Title: PicoScope 4000a-series (4824a) streaming data collection script
- Description:This script collects data from a PicoScope 4000a-series (4824a) using streaming mode. 
              It allows for continuous data collection and saves the data to a file. The script can 
              be adjusted for different sampling rates, voltage ranges, and capture modes (time or 
              samples). It also includes error handling and status updates during data collection.
- Code version: 2.0
- Type: source code
*************************************************************
'''

import ctypes
import time
import numpy as np
from picosdk.functions import assert_pico_ok
from picosdk.ps4000a import ps4000a as ps
from picosdk.constants import PICO_STATUS
from functools import partial

samplesCollected = 0  # Global variable to track the number of samples collected

def rangeOfMeasurementX1(voltage):
    """
    Return the appropriate range key based on the desired voltage range.
    """
    ranges = ps.PICO_CONNECT_PROBE_RANGE
    voltage_map = {
        0.01: "PICO_X1_PROBE_10MV",
        0.02: "PICO_X1_PROBE_20MV",
        0.05: "PICO_X1_PROBE_50MV",
        0.1: "PICO_X1_PROBE_100MV",
        0.2: "PICO_X1_PROBE_200MV",
        0.5: "PICO_X1_PROBE_500MV",
        1.0: "PICO_X1_PROBE_1V",
        2.0: "PICO_X1_PROBE_2V",
        5.0: "PICO_X1_PROBE_5V",
        10.0: "PICO_X1_PROBE_10V",
        20.0: "PICO_X1_PROBE_20V",
        50.0: "PICO_X1_PROBE_50V",
        100.0: "PICO_X1_PROBE_100V",
        200.0: "PICO_X1_PROBE_200V",
    }

    return ranges[voltage_map[voltage]]

def openPicoScope(handle, status, serial = None):
    """
    Open a PicoScope 4000a-series (4824a) and return the handle for use in future functions.
    """
    status["openunit"] = ps.ps4000aOpenUnit(ctypes.byref(handle), serial)

    try:
        assert_pico_ok(status["openunit"])
        print("PicoScope connected!")
    except:
        print("PicoScope connection error!")
        powerStatus = status["openunit"]

        if powerStatus == 286:
            status["changePowerSource"] = ps.ps4000aChangePowerSource(handle, powerStatus)
        else:
            raise

        assert_pico_ok(status["changePowerSource"])

    return handle

def setupChannel(handle, channel, coupling, voltageRange, status, analogOffset=0.0, enabled=1):
    """
    Set up a channel on the PicoScope 4000a-series (4824a) and return the status dictionary.
    """
    channelKey = f"PS4000A_CHANNEL_{channel.upper()}"
    couplingKey = f"PS4000A_{coupling.upper()}"
    
    status[f"setCh{channel.upper()}"] = ps.ps4000aSetChannel(
        handle,
        ps.PS4000A_CHANNEL[channelKey],
        enabled,
        ps.PS4000A_COUPLING[couplingKey],
        rangeOfMeasurementX1(voltageRange),
        analogOffset
    )
    assert_pico_ok(status[f"setCh{channel.upper()}"])
    
    return status

def setupBuffers(handle, channel, size, segment, status, buffer):
    """
    Set up data buffers for streaming data collection for a single channel and return the status dictionary.
    """
    channelKey = f"PS4000A_CHANNEL_{channel.upper()}"
    
    status[f"setDataBuffers{channel}"] = ps.ps4000aSetDataBuffers(
        handle,
        ps.PS4000A_CHANNEL[channelKey],
        buffer.ctypes.data_as(ctypes.POINTER(ctypes.c_int16)),
        None,
        size,
        segment,
        ps.PS4000A_RATIO_MODE["PS4000A_RATIO_MODE_NONE"]
    )
    assert_pico_ok(status[f"setDataBuffers{channel}"])

    return status

def runStreaming(handle, sampleInterval, sampleUnits, sizeOfOneBuffer, totalSamples, status, autoStop):
    """
    Run streaming data collection on the PicoScope 4000a-series (4824a) and return the status dictionary.
    """
    sampleUnits = f"PS4000A_{sampleUnits.upper()}"
    
    status["runStreaming"] = ps.ps4000aRunStreaming(
        handle,
        ctypes.byref(sampleInterval),
        ps.PS4000A_TIME_UNITS[sampleUnits],
        0,
        totalSamples,
        autoStop,
        1,
        ps.PS4000A_RATIO_MODE["PS4000A_RATIO_MODE_NONE"],
        sizeOfOneBuffer
    )
    
    assert_pico_ok(status["runStreaming"])
    time.sleep(1)  
    return status

def streamingCallback(handle, noOfSamples, startIndex, overflow, triggerAt, triggered, autoStop, pParameter,
                       thresholdClock, thresholdData, outputFilename, VOLTAGE_RANGE, totalSamples, captureMode,
                       useX10Probe):
    """
    Callback function for streaming data collection on the PicoScope 4000a-series (4824a).
    """

    global bufferClock, bufferData, samplesCollected  # Use the previously, globally defined variables

    if overflow == 0:
        clkData = np.array(bufferClock[:noOfSamples], dtype=np.int16) * (VOLTAGE_RANGE / 32767)
        clkBinary = (clkData >= thresholdClock).astype(int)

        dataData = np.array(bufferData[:noOfSamples], dtype=np.int16) * (VOLTAGE_RANGE / 32767)

        if useX10Probe:
            dataData *= 10

        dataBinary = (dataData >= thresholdData).astype(int)

        risingEdges = np.where(np.diff(clkBinary) == 1)[0]  
        sampledBits = dataBinary[risingEdges]

        # Trim the sampledBits to exactly reach the totalSamples limit if captureMode is "samples"
        if captureMode == "samples":
            remainingSamples = totalSamples - samplesCollected
            sampledBits = sampledBits[:remainingSamples]        # Take only the needed samples

        with open(outputFilename, "a") as file:
            file.write("".join(map(str, sampledBits)))

        samplesCollected += len(sampledBits)  
    else:
        print("Overflow occurred, skipping data.")

def collectData(handle, cFuncPtrToCallbackFunc, outputFilename, status, thresholdClock, thresholdData, mode, durationSeconds, 
                totalSamples, voltageRange, no_signal_duration_threshold=3, statusInterval=10000, timeStatusInterval=5):
    """
    Collect data on the PicoScope 4000a-series (4824a) and write it to a file.
    Parameters:
    - statusInterval: Number of samples between status updates (default 10000), used when mode = "samples".
    - timeStatusInterval: Time between status updates in seconds (default 5), used when mode = "time".
    """
    global bufferClock, bufferData  
    lastStatusUpdate = 0
    lastTimeUpdate = 0

    with open(outputFilename, "w") as file:
        startTime = time.time()
        lastSignalTime = time.time()  # Track last detected signal time

        while True:
            overflow = ctypes.c_int16(0)

            status["getLatest"] = ps.ps4000aGetStreamingLatestValues(
                handle,
                cFuncPtrToCallbackFunc,
                ctypes.byref(overflow)
            )

            # Check if a signal is detected and update lastSignalTime
            if bufferClock is not None and bufferData is not None:
                if not (np.all(np.array(bufferClock) == 0) and np.all(np.array(bufferData) == 0)):  
                    lastSignalTime = time.time()  # Update last detected signal time

            elapsedTime = time.time() - startTime
            # Stopping conditions
            if mode == "time":
                if elapsedTime >= durationSeconds:
                    print("Time limit reached, stopping.")
                    break
                else:
                    if elapsedTime - lastTimeUpdate >= timeStatusInterval:
                        print(f"Samples collected: {samplesCollected} | Elapsed time: {elapsedTime:.2f}/{durationSeconds:.2f} s")
                        lastTimeUpdate = elapsedTime

            elif mode == "samples":
                if samplesCollected >= totalSamples:
                    print("Total samples reached, stopping.")
                    break
                else:
                    if samplesCollected >= lastStatusUpdate + statusInterval:
                        print(f"Samples collected: {samplesCollected}/{totalSamples} | Elapsed time: {elapsedTime:.2f} s")
                        lastStatusUpdate = samplesCollected  # Update last status update milestone

            elif (time.time() - lastSignalTime) >= no_signal_duration_threshold:
                print(f"No signal detected for {no_signal_duration_threshold} seconds, stopping.")
                break  # Stop if no signal is detected for too long

    print(f"Recording stopped after {(time.time() - startTime)*1000:.2f} ms, {samplesCollected} samples collected.")

def stopDataAcquisitionPicoScope(handle):
    """
    Stop data acquisition on the PicoScope 4000a-series (4824a).
    """
    ps.ps4000aStop(handle)
    print("Data acquisition stopped!")

def closePicoScope(handle):
    """
    Close the PicoScope 4000a-series (4824a) and print a message to the console.
    """
    ps.ps4000aCloseUnit(handle)
    print("PicoScope disconnected!")

def main(OUTPUT_FILE):
    '''DO NOT FORGET TO SPECIFY WHETHER YOU'RE USING A X10 PROBE OR NOT FOR THE DATA CHANNEL'''
    # --- Buffer Settings ---
    global bufferClock, bufferData                                          # Allocate a global buffer for both channels
    sizeOfOneBuffer = 500                                                   # Buffer size (500 samples per capture)
    numBuffersToCapture = 10                                                # Number of buffers to capture
    bufferClock = np.zeros(sizeOfOneBuffer, dtype=np.int16)                 # Preallocate buffer for clock
    bufferData = np.zeros(sizeOfOneBuffer, dtype=np.int16)                  # Preallocate buffer for data
    memorySegment = 0                                                       # Memory segment to use for data collection

    # --- User-Adjustable Parameters ---        
    CLK_CHANNEL = "A"                                                       # Channel to connect the clock signal
    DATA_CHANNEL = "B"                                                      # Channel to connect the data signal
    useX10Probe = True                                                      # Use a x10 probe for the data signal
    COUPLING = "DC"                                                         # Coupling mode for the CLK_CHANNEL

    VOLTAGE_RANGE = 5                                                       # Voltage range for both channels  
    THRESHOLD_CLOCK = 1.5                                                   # Voltage threshold for clock signal
    THRESHOLD_DATA = 2                                                      # Voltage threshold for data collection

    CAPTURE_MODE = "samples"                                                # Capture mode: "time" or "samples"
    DURATION_SECONDS = 10                                                   # Duration of data collection (used if CAPTURE_MODE="time")
    TOTAL_SAMPLES = 10000000                                                # Amount of samples(bits) collected (used if CAPTURE_MODE="samples")
    SIGNAL_FREQUENCY = 10000                                                # Signal frequency in Hz

    # --- Sampling ---
    SAMPLE_INTERVAL = ctypes.c_int16(int(1e6 / (SIGNAL_FREQUENCY * 10)))    # Sample interval in microseconds
    SAMPLE_UNITS = "US"                                                     # Sample interval units
    print(f"Setting sample interval to {SAMPLE_INTERVAL} {SAMPLE_UNITS} for a {SIGNAL_FREQUENCY} Hz signal.")

    # --- Capture Mode Configuration ---
    autoStop = 0 if CAPTURE_MODE == "samples" else 0                        # Record continuously for the given duration OR stop when totalSamples is reached

    # --- PicoScope Setup ---
    chandle = ctypes.c_int16()                                              # Unique identifier for the device
    status = {}
    cFuncPtr = ps.StreamingReadyType(
        partial(streamingCallback, thresholdClock=THRESHOLD_CLOCK, thresholdData=THRESHOLD_DATA, 
                outputFilename=OUTPUT_FILE, VOLTAGE_RANGE=VOLTAGE_RANGE, totalSamples=TOTAL_SAMPLES, 
                captureMode=CAPTURE_MODE, useX10Probe=useX10Probe))

    # --- Open and Configure PicoScope ---
    openPicoScope(chandle, status)

    setupChannel(chandle, CLK_CHANNEL, COUPLING, VOLTAGE_RANGE, status)
    setupBuffers(chandle, CLK_CHANNEL, sizeOfOneBuffer, memorySegment, status, bufferClock)

    setupChannel(chandle, DATA_CHANNEL, COUPLING, VOLTAGE_RANGE, status)
    setupBuffers(chandle, DATA_CHANNEL, sizeOfOneBuffer, memorySegment, status, bufferData)

    # --- Start Data Acquisition ---
    runStreaming(chandle, SAMPLE_INTERVAL, SAMPLE_UNITS, sizeOfOneBuffer, TOTAL_SAMPLES, status, autoStop)

    # --- Collect Data ---
    collectData(chandle, cFuncPtr, OUTPUT_FILE, status, THRESHOLD_CLOCK, THRESHOLD_DATA,
                CAPTURE_MODE, DURATION_SECONDS, TOTAL_SAMPLES, VOLTAGE_RANGE)

    # --- Stop and Close PicoScope ---
    stopDataAcquisitionPicoScope(chandle)
    closePicoScope(chandle)


if __name__ == '__main__':
    OUTPUT_FILE = "output.txt"
    main(OUTPUT_FILE)