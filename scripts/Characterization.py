import datetime
import gc
import os
import math

import functions as custom_fun
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

# pd.options.display.width = 0

scripts_loc = os.getcwd()
result_loc = '../result files'
data_file = result_loc + '/data_file.csv'

assert os.path.exists(data_file), "Data file does not exist ..."

# record the start time
time_start_main_loop = datetime.datetime.now()
print('\n\nLoading data ...')
gc.collect()

# Read data
dataset = pd.read_csv(data_file)
column_dtypes = {'CYCLE': 'uint16', 'TIME': 'datetime64', 'CAR_ID': 'category',
                 'INS_ID': 'uint16', 'INS_CAT': 'category', 'FLUO': 'category', 'FLUO_CODE': 'category',
                 'CONC': 'float64', 'CONC_CODE': 'category', 'STATE': 'category', 'CHAMBER': 'category',
                 'CHANNEL': 'uint8', 'T': 'float16', 'EXC_P': 'float64', 'EXC_P_CODE': 'category',
                 'DET_P': 'float64', 'MAX_DET_P': 'float16'}
dataset = dataset.astype(column_dtypes)
dataset.sort_values(by=['FLUO', 'INS_ID', 'CONC_CODE', 'CHANNEL', 'CHAMBER', 'CYCLE'],
                    ascending=[True, True, True, True, True, True], inplace=True)
print('\n\nDataset loaded.')


# Keep only T 40 for background cycles (other T for other experiment)
dataset_bkg_T40 = dataset[~((dataset.CONC_CODE == "BKG") & (dataset["T"] >= 50))]
dataset_bkg_T40.groupby(["CONC_CODE", "T"]).size()

print('\n\nFreezing some columns ...')
bkgr_state1 = custom_fun.filtering(dataset_bkg_T40, FLUO_CODE='Main', STATE='1 no disk, undocked', EXC_P_CODE='P_nom')
fluo_state6 = custom_fun.filtering(dataset_bkg_T40, FLUO_CODE='Main', STATE='6 heated at 65degC', EXC_P_CODE='P_nom')

# Average over chamber
output_column = 'DET_P'
fluo_state6_avg_chamber = custom_fun.averaging(fluo_state6, avg_over_factor='CHAMBER', avged_factor=output_column)  # d
bkgr_state1_avg_chamber = custom_fun.averaging(bkgr_state1, avg_over_factor='CHAMBER', avged_factor=output_column)  # e

# average over "CYCLE"
fluo_state6_avg_cycle = custom_fun.averaging(fluo_state6_avg_chamber, avg_over_factor='CYCLE', avged_factor=output_column)
bkgr_state1_avg_cycle = custom_fun.averaging(bkgr_state1_avg_chamber, avg_over_factor='CYCLE', avged_factor=output_column)

# Get background det power avg over INS and FLUO
bkgr_ins_fluo = bkgr_state1_avg_cycle.groupby(['INS_ID', 'FLUO'], as_index=False, observed=True)['DET_P'].mean()  # g
bkgr_ins_fluo.columns = ['INS_ID', 'FLUO', 'BACKGROUND']

# Regression
input_column = 'CONC'
reg_fluo = custom_fun.reg(fluo_state6_avg_cycle, input_column, output_column)  # h
reg_fluo_bkgr = pd.merge(reg_fluo, bkgr_ins_fluo, on=['INS_ID', 'FLUO'])  # i
reg_fluo_bkgr['INTERCEPT'] = reg_fluo_bkgr['OFFSET'] - reg_fluo_bkgr['BACKGROUND']
cols = reg_fluo_bkgr.columns.tolist()
cols = cols[:19] + cols[21:23] + cols[19:21]
reg_fluo_bkgr = reg_fluo_bkgr[cols]
ideal_ins_per_fluo = reg_fluo_bkgr.groupby('FLUO')[['GAIN', 'OFFSET', 'BACKGROUND']].mean()  # j


# Result: select, sort, add columns from ideal df and add new columns
result_reg = reg_fluo_bkgr[["INS_ID", "INS_CAT", "FLUO", "CHANNEL", "GAIN", "OFFSET", "BACKGROUND", "INTERCEPT"]] \
    .reset_index(drop=True) \
    .rename(columns={"INS_ID": "INS ID", "INS_CAT": "INS CAT", "BACKGROUND": "BG"}) \
    .sort_values(by=['CHANNEL', 'FLUO', 'INS ID'], ascending=[True, True, True])

ideal_ins_per_fluo_colprefix = ideal_ins_per_fluo.rename(columns={"BACKGROUND": "BG"}).add_prefix("IDEAL ")
result = result_reg.merge(ideal_ins_per_fluo_colprefix, on="FLUO")
result["IDEAL INTERCEPT"] = result["IDEAL OFFSET"] - result["IDEAL BG"]
result["NORMALIZED GAIN"] = result["GAIN"] / result["IDEAL GAIN"]
result["NORMALIZED OFFSET"] = (result["OFFSET"] - result["IDEAL BG"]) / result["IDEAL GAIN"]
result["NORMALIZED BG"] = (result["BG"] - result["IDEAL BG"]) / result["IDEAL GAIN"]
result["NORMALIZED INTERCEPT"] = (result["INTERCEPT"] - result["IDEAL BG"]) / result["IDEAL GAIN"]


# record the end time and display total processing time
time_end_main_loop = datetime.datetime.now()
time_delta_main_loop = time_end_main_loop - time_start_main_loop
print('\n\nProcessing took ' + str(time_delta_main_loop))

# Write table to excel file
print('\n\nWriting INS Characterization Table')
xls_file = result_loc + '\Instrument Working Zone 12 ins.xlsx'
result.to_excel(xls_file, index=False, header=True)

# Export BKG of each INS per chamber per channel per Temperature
# so only average over 5 cycle in the corresponding T
dataset_bkg = dataset[dataset.CONC_CODE == "BKG"]
dataset_bkg_avg_cycle = custom_fun.averaging(dataset_bkg, avg_over_factor='CYCLE', avged_factor=output_column)
dataset_bkg_avg_cycle.to_excel(result_loc + r"\background_per_temperature.xlsx", index=False, header=True)


print('\n\nPlotting')
FLUO = list(reg_fluo_bkgr['FLUO'].drop_duplicates())
fig, axs = plt.subplots(nrows=2, ncols=5, figsize=(18, 10))
for index, item in enumerate(FLUO):
    Instruments = reg_fluo_bkgr.loc[reg_fluo_bkgr['FLUO'] == item]
    for dummy, INS in Instruments.iterrows():
        for_plot = pd.DataFrame(columns=['conc [uM]', 'DET Power [nW]'])
        for_plot.loc[:, 'conc [uM]'] = INS.loc['X']
        for_plot.loc[:, 'DET Power [nW]'] = INS.loc['Y']
        if INS.loc['INS_CAT'] != 'Ref':
            ALPHA = 0.3
        else:
            ALPHA = 1.0
        sns.regplot(x='conc [uM]', y='DET Power [nW]', data=for_plot, scatter_kws={'alpha': ALPHA}, line_kws={'alpha': ALPHA}, ci=None,
                    label=INS.loc['INS_ID'], ax=axs[math.floor(index/5), index % 5])
        axs[math.floor(index/5), index % 5].set_title(item)
        del for_plot
    axs[math.floor(index / 5), index % 5].legend(loc='upper left', prop={'size': 6})
    axs[math.floor(index / 5), index % 5].grid()
    axs[math.floor(index / 5), index % 5].xaxis.set_label_text('')
    axs[math.floor(index / 5), index % 5].yaxis.set_label_text('')
fig.text(0.5, 0.04, 'conc [uM]', ha='center')
fig.text(0.04, 0.5, 'DET Power [nW]', va='center', rotation='vertical')
mng = plt.get_current_fig_manager()
mng.full_screen_toggle()
plt.show()

print('\n\nExit')


print('\n\nExit')
