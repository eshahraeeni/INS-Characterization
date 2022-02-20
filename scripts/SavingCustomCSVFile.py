import datetime
import gc
import os

import functions as custom_fun
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

pd.options.display.width = 0

time_start_main_loop = datetime.datetime.now()
scripts_loc = os.getcwd()
os.chdir('..\..\source files')
source_loc = os.getcwd()
os.chdir('..\\result files')
result_loc = os.getcwd()
data_file = result_loc + '\data_file.csv'

try:
    with open(data_file, 'r') as f:
        DataFiles_Exist = 1
except FileNotFoundError:
    DataFiles_Exist = 0

if DataFiles_Exist:
    # record the start time
    time_start_main_loop = datetime.datetime.now()
    print('\n\nLoading data ...')
    gc.collect()
    column_dtypes = {}
    DS = pd.read_csv(data_file, dtype=column_dtypes)
    column_dtypes = {'CYCLE': 'uint16', 'TIME': 'datetime64', 'CAR_ID': 'category',
                     'INS_ID': 'uint16', 'INS_CAT': 'category', 'FLUO': 'category', 'FLUO_CODE': 'category',
                     'CONC': 'float64', 'CONC_CODE': 'category', 'STATE': 'category', 'CHAMBER': 'category',
                     'CHANNEL': 'uint8', 'T': 'float16', 'EXC_P': 'float64', 'EXC_P_CODE': 'category',
                     'DET_P': 'float64', 'MAX_DET_P': 'float16'}
    DS = DS.astype(column_dtypes)
    print('\n\nDataset loaded.')

    print('\n\nFreezing some columns ...')
    b = custom_fun.filtering(DS, FLUO_CODE='Main', STATE='1 no disk, undocked', EXC_P_CODE='P_nom', CONC_CODE='C0')
    # b = custom_fun.filtering(DS, FLUO_CODE='Main', EXC_P_CODE='P_nom', CONC_CODE='C0')
    # b = custom_fun.filtering(DS)

    average_over_column = 'CHAMBER'
    output_column = 'DET_P'
    c = custom_fun.averaging(b, average_over_column, output_column)

    file_name = 'dat_file_' + average_over_column + '_AVG'
    custom_fun.save_to_file(c, file_name, result_loc)

    # record the end time and display total processing time
    time_end_main_loop = datetime.datetime.now()
    time_delta_main_loop = time_end_main_loop - time_start_main_loop
    print('\n\nProcessing took ' + str(time_delta_main_loop))

    print('\n\nExit')

else:
    print('\n\nData file does not exist ...')
    print('\n\nExit')
