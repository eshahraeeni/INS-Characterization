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
    b = custom_fun.filtering(DS, FLUO_CODE='Main', STATE='6 heated at 65degC', EXC_P_CODE='P_nom')
    # b = custom_fun.filtering(DS, FLUO_CODE='Main', EXC_P_CODE='P_nom', CONC_CODE='C0')
    # b = custom_fun.filtering(DS)

    average_over_column = 'CHAMBER'
    output_column = 'DET_P'
    c = custom_fun.averaging(b, average_over_column, output_column)

    file_name = 'data_file_' + average_over_column + '_AVG'
    custom_fun.save_to_file(c, file_name, result_loc)

    input_column = 'CONC'
    d = custom_fun.reg(b, input_column, output_column)
    e = custom_fun.reg(c, input_column, output_column)

    # record the end time and display total processing time
    time_end_main_loop = datetime.datetime.now()
    time_delta_main_loop = time_end_main_loop - time_start_main_loop
    print('\n\nProcessing took ' + str(time_delta_main_loop))

    print('\n\nPlotting')
    fig, ax = plt.subplots(figsize=(15, 8))
    for_plot = pd.DataFrame(columns=['x', 'y', 'hue'])
    for_plot.loc[:, 'x'] = b.loc[:, 'GAIN']
    for_plot.loc[:, 'y'] = b.loc[:, 'OFFSET']
    for_plot.loc[:, 'hue'] = b.loc[:, 'INS_ID'].astype('category')
    sns.scatterplot(x='x', y='y', hue='hue', alpha=0.5, data=for_plot, ax=ax)
    del for_plot
    for_plot = pd.DataFrame(columns=['x', 'y', 'hue'])
    for_plot.loc[:, 'x'] = c.loc[:, 'GAIN']
    for_plot.loc[:, 'y'] = c.loc[:, 'OFFSET']
    for_plot.loc[:, 'hue'] = c.loc[:, 'INS_ID'].astype('category')
    plot = sns.scatterplot(x='x', y='y', hue='hue', data=for_plot, ax=ax, s=75)
    plot.set(xscale='log')
    plot.set(yscale='log')
    handle, label = plot.axes.get_legend_handles_labels()
    plot.axes.legend_.remove()
    plot.legend(handle[1:int(len(handle) / 2)], label[1:int(len(handle) / 2)], ncol=17, loc=9,
                bbox_to_anchor=(0.5, 1.1))
    plot.set(xlabel=r'Gain [nW / $\mu$M]', ylabel='Offset [nW]')
    plt.grid()
    # mng = plt.get_current_fig_manager()
    # mng.frame.Maximize(True)
    plt.show()

    print('\n\nExit')

else:
    print('\n\nData file does not exist ...')
    print('\n\nExit')
