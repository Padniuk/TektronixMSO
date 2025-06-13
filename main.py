import schedule
import time
import subprocess
import datetime
import sys
import os
import pyvisa
import numpy as np
import pandas as pd

start_time = datetime.datetime.now()

def collect_data(visa_address, path, avr=10):
    rm = pyvisa.ResourceManager()
    scope = rm.open_resource(visa_address)
    scope.timeout = 1000000  # ms
    scope.encoding = 'latin_1'
    scope.read_termination = '\n'
    scope.write_termination = None

    scope.write('*cls')  # clear ESR

    scope.write(f'ACQUIRE:NUMAVG {avr}')
    scope.write('ACQuire:MODe AVERAGE')

    # --- Setup acquisition and recording parameters ---
    record = int(scope.query('horizontal:recordlength?'))
    scope.write('data:start 1')
    scope.write(f'data:stop {record}')
    scope.write('wfmoutpre:byt_n 2')
    scope.write('WFMOutpre:ENCdg ASCii')

    scope.write('acquire:state 0')
    scope.write('acquire:stopafter SEQUENCE')
    scope.write('acquire:state 1')

    t5 = time.perf_counter()
    r = scope.query('*opc?')  # sync
    t6 = time.perf_counter()
    # print(f'acquire time: {t6 - t5} s')

    # --- Time axis config (same for both channels) ---
    tscale = float(scope.query('wfmoutpre:xincr?'))
    tstart = float(scope.query('wfmoutpre:xzero?'))
    total_time = tscale * record
    tstop = tstart + total_time
    scaled_time = np.linspace(tstart, tstop, num=record, endpoint=False)

    # --- CH1 ---
    scope.write('data:source CH1')
    ch1_wave = scope.query_ascii_values('curve?', container=np.array)
    ch1_vscale = float(scope.query('wfmoutpre:ymult?'))
    ch1_voff = float(scope.query('wfmoutpre:yzero?'))
    ch1_vpos = float(scope.query('wfmoutpre:yoff?'))
    ch1_scaled = (np.array(ch1_wave) - ch1_vpos) * ch1_vscale + ch1_voff

    # --- CH2 ---
    scope.write('data:source CH2')
    ch2_wave = scope.query_ascii_values('curve?', container=np.array)
    ch2_vscale = float(scope.query('wfmoutpre:ymult?'))
    ch2_voff = float(scope.query('wfmoutpre:yzero?'))
    ch2_vpos = float(scope.query('wfmoutpre:yoff?'))
    ch2_scaled = (np.array(ch2_wave) - ch2_vpos) * ch2_vscale + ch2_voff

    # --- Error check ---
    r = int(scope.query('*esr?'))
    # print(f'event status register: 0b{r:08b}')
    r = scope.query('allev?').strip()
    # print(f'all event messages: {r}')

    scope.close()
    rm.close()

    # --- Save to CSV ---
    wave_data_full = np.vstack((1e6*scaled_time, 1e3*ch1_scaled, 1e3*ch2_scaled)).T
    pd.DataFrame(wave_data_full, columns=['Time, us', 'CH1, mV', 'CH2, mV']).to_csv(path, index_label="#")


def run_script():
    data_folder = 'data'
    elapsed_time = int((datetime.datetime.now() - start_time).total_seconds())
    
    subfolder = data_folder+"/"+str(elapsed_time)
    if not os.path.exists(subfolder):
        os.makedirs(subfolder)
    else:
        for file in os.listdir(os.path.join(data_folder, str(elapsed_time))):
            file_path = os.path.join(data_folder, file)
            if os.path.isfile(file_path):
                os.unlink(file_path)

    for file in os.listdir(subfolder):
        file_path = os.path.join(subfolder, file)
        if os.path.isfile(file_path):
            os.unlink(file_path)

    rm = pyvisa.ResourceManager()

    instruments = rm.list_resources()
    
    for i in range(7): # adjust the amount of traces, now is set to 7 per 2 minutes
        collect_data(instruments[0], f"{data_folder}/{elapsed_time}/{i}.csv", avr=10)

    rm.close()

schedule.every(2).minutes.do(run_script)

run_script()

while True:
    schedule.run_pending()
    time.sleep(1)