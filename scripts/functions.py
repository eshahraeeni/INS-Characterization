import datetime
import gc
import math
import os
from typing import Dict, List, Any, Union
import numpy as np
import pandas as pd
pd.options.mode.chained_assignment = None # default='warn'
from sklearn.linear_model import LinearRegression

pd.options.display.width = 0


def progress(percent=0, width=30):
    left = width * percent // 100
    right = width - left
    print('\r[', '|' * left, ' ' * right, ']',
          f' {percent:.0f}%',
          sep='', end='', flush=True)


def getTodayDateString():
    # get a string of today's date according to yyyy_mm_dd
    datestring = str(datetime.datetime.now().year)
    datestring += '_'
    datestring += right('0' + str(datetime.datetime.now().month), 2)
    datestring += '_'
    datestring += right('0' + str(datetime.datetime.now().day), 2)
    return datestring


def left(s, amount):
    return s[:amount]


def right(s, amount):
    return s[-amount:]


def mid(s, offset, amount):
    return s[offset:offset + amount]


def split(string, separator):
    # this function takes a string and a chosen 'separator' string.
    # It will then cut up the original string everywhere the 'separator' was and return a list of all separated parts
    iterations = 0
    string = string.replace('\n', '')
    returnlist = []
    while separator in string:
        iterations += 1
        extracted = left(string, string.find(separator))
        returnlist.append(num(extracted))
        string = right(string, len(string) - string.find(separator) - 1)
        # as a sanity check: do not allow more than 200 iterations to this algorithm
        if iterations > 200:
            break
    returnlist.append(num(string))
    return returnlist


def num(s):
    # try to convert a string into a number
    try:
        int(s)
        return int(s)
    except ValueError:
        try:
            float(s)
            return float(s)
        except ValueError:
            return s


def getfilename(filepath):
    temp = split(filepath, '\\')
    return temp[-1]


# function to return key for any value
def get_key(my_dict,val):
    for key, value in my_dict.items():
        if val == str(value):
            return key

    return "key doesn't exist"


def processFile(input_path, file):
    # go to the folder with input files
    os.chdir(input_path)

    # include test types from the following list
    testtype_filtering = ['qPCR experiment']

    # set some default values before reading the file
    INS_ID = 'UNKNOWN'
    CAR_ID = 'UNKNOWN'
    START_TIME = 'UNKNOWN'
    SAMPLE_ID = 'UNKNOWN'
    TEST_TYPE = 'qPCR experiment'  # hack to force files to be processed
    concentration_code = 'NULL'
    fluorophore = 'UNKNOWN'
    fluo_code = 'UNKNOWN'
    INS_TYPE = 'UNKNOWN'
    temperature = 65.0

    # define the channels associated with each fluorophore. NOTE: for crosstalk analysis, define for each fluorophore the channel that should be included
    fluo_channels = {'FAM': 1, 'HEX': 2, 'TXR': 3, 'CY5': 4, 'AX70': 5, 'AX75': 6}

    # define the concentration values for each fluorophore
    concentrations = {}
    concentrations['FAM'] = [0, 0.066, 0.25, 0.5, 1]
    concentrations['HEX'] = [0, 0.033, 0.125, 0.3, 0.5]
    concentrations['TXR'] = [0, 0.066, 0.25, 0.5, 1]
    concentrations['CY5'] = [0, 0.033, 0.125, 0.3, 0.5]
    concentrations['AX70'] = [0, 0.125, 0.5, 1.125, 2]
    concentrations['AX75'] = [0, 0.033, 0.125, 0.3, 0.5]

    # define the excitation power for each fluorophore/channel [mW]
    exc_pwrs = {}
    exc_pwrs['FAM'] = [25.1]
    exc_pwrs['HEX'] = [7.4]
    exc_pwrs['TXR'] = [4]
    exc_pwrs['CY5'] = [3.2]
    exc_pwrs['AX70'] = [3.2]
    exc_pwrs['AX75'] = [1.8]

    # define the nominal excitation power for each fluorophore/channel [mW]
    nom_exc_pwrs = {}
    nom_exc_pwrs['FAM'] = 25.1
    nom_exc_pwrs['HEX'] = 7.4
    nom_exc_pwrs['TXR'] = 4
    nom_exc_pwrs['CY5'] = 3.2
    nom_exc_pwrs['AX70'] = 3.2
    nom_exc_pwrs['AX75'] = 1.8

    # define the maximum detection power for each fluorophore/channel [nW]
    max_det_pwrs = {}
    max_det_pwrs['FAM'] = 100
    max_det_pwrs['HEX'] = 100
    max_det_pwrs['TXR'] = 50
    max_det_pwrs['CY5'] = 50
    max_det_pwrs['AX70'] = 50
    max_det_pwrs['AX75'] = 50

    # these lists are needed to process the backendresults file
    columns = ['cycle', 'time', 'A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'C1', 'C2',
               'C3', 'C4', 'C5', 'C6', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'E1', 'E2', 'E3', 'E4', 'E5', 'E6']
    positions = ['A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'C1', 'C2', 'C3', 'C4', 'C5',
                 'C6', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'E1', 'E2', 'E3', 'E4', 'E5', 'E6']

    # initialize an empty dictionary, which will have the entire backendresults contents in it
    datatable = {}
    # process the file
    f = open(file)
    for line in f:
        if '% Slot ID' in line:
            # extract from this line the instrument serial number
            INS_ID = ''.join(c for c in line if c.isdigit())
        if '% Cartridge ID (operator):' in line:
            # extract the cartridge ID from this line
            line = line.replace('*', '')
            startindex = line.find('):') + 3
            CAR_ID = mid(line, startindex, 100).replace('\n', '')
            # for this set of experiments, the CAR ID is used to encode fluorophore name and concentration code
            startindex = CAR_ID.find('-') + 1
            fluorophore = mid(CAR_ID, 0, startindex - 1)
            concentration_code = mid(CAR_ID, startindex, 100).replace('\n', '')
            INS_TYPE = 'Ref'
        if '% Protocol Start Time (ISW time):' in line:
            # extract the start time from this line
            startindex = line.find('):') + 3
            START_TIME = mid(line, startindex, 100).replace('\n', '')
        if '% Sample ID:' in line:
            # extract the SAMPLE ID from this line (not used for this experiment)
            startindex = line.find('D:') + 3
            SAMPLE_ID = mid(line, startindex, 100).replace('\n', '')
        if '% Test Type:' in line:
            # extract the TEST TYPE from this line (not used for this experiment)
            startindex = line.find('e:') + 3
            TEST_TYPE = mid(line, startindex, 100).replace('\n', '')
        if '%' not in line and '\t-1\t' not in line and TEST_TYPE in testtype_filtering:
            # if here: headers are passed and now coming to real data
            splitline = split(line, '\t')  # split the line according to tabs
            cycle = splitline[0]  # the first column is the cycle number
            # store all line contents into a dictionary, named according to channel/chamber positions
            linedict = {}
            for i in range(len(splitline)):
                linedict[columns[i]] = splitline[i]
            # add this entire line to the data table
            datatable[cycle] = linedict
    f.close()
    # the entire file is read, now process (unpivot, etc.)

    record: List[Dict[Union[str, Any], Union[Union[int, str, float], Any]]] = []
    step_length = 5
    if len(datatable) >= step_length and TEST_TYPE in testtype_filtering:  # only process file if file is long enough
        if fluorophore == "XXXX":
            for pos in positions:
                channel = right(pos, 1)
                fluorophore = get_key(fluo_channels, channel)
                chamber = left(pos, 1)

                # walk through the entire protocol (5 cycles)
                for i in range(step_length):
                    cycle = i + 1
                    exc_power = exc_pwrs[fluorophore][0]
                    power_code = 'P_nom'

                    # determining if fluorophore is the primary marker of the channel
                    if fluorophore in fluo_channels.keys():
                        if str(fluo_channels[fluorophore]) == channel:
                            fluo_code = 'Main'
                        else:
                            fluo_code = 'Cross'

                        # extract from the backendresult table the value for this cycle/position
                        det_power = datatable[cycle][pos]

                        # retrieve the concentration used in this experiment
                        concentration = 0
                        conc_code = 'C0'
                        state = "6 heated at 65degC"
                        car_id = CAR_ID

                        DetPowMax = max_det_pwrs[fluorophore]

                        # build the line to be written to the output file
                        newline_record = {'CYCLE': int(cycle), 'TIME': str(START_TIME), 'CAR_ID': str(car_id),
                                          'INS_ID': int(INS_ID), 'INS_CAT': str(INS_TYPE), 'FLUO': str(fluorophore),
                                          'FLUO_CODE': str(fluo_code), 'CONC': float(concentration),
                                          'CONC_CODE': str(conc_code), 'STATE': str(state), 'CHAMBER': str(chamber),
                                          'CHANNEL': int(channel), 'T': float(temperature), 'EXC_P': float(exc_power),
                                          'EXC_P_CODE': str(power_code), 'DET_P': float(det_power),
                                          'MAX_DET_P': float(DetPowMax)}
                        if fluorophore in fluo_channels.keys():
                            record.append(newline_record)
            return record

        elif concentration_code == "XXX":
            for pos in positions:
                channel = right(pos, 1)
                chamber = left(pos, 1)
                fluorophore = get_key(fluo_channels, channel)

                # walk through the entire protocol (5 cycles)
                temperature_step = 5
                for i in range(step_length*temperature_step):
                    cycle = i + 1
                    exc_power = exc_pwrs[fluorophore][0]
                    power_code = 'P_nom'

                    # determining if fluorophore is the primary marker of the channel
                    if fluorophore in fluo_channels.keys():
                        if str(fluo_channels[fluorophore]) == channel:
                            fluo_code = 'Main'
                        else:
                            fluo_code = 'Cross'

                    # extract from the backendresult table the value for this cycle/position
                    det_power = datatable[cycle][pos]

                    # retrieve the concentration used in this experiment
                    concentration = -1
                    conc_code = "BKG"
                    car_id = CAR_ID

                    if cycle <= step_length * 1:
                        temperature = 40
                        state = "1 no disk, undocked"
                    if step_length * 1 < cycle <= step_length * 2:
                        temperature = 50
                        state = "1 no disk, undocked"
                    if step_length * 2 < cycle <= step_length * 3:
                        temperature = 60
                        state = "1 no disk, undocked"
                    if step_length * 3 < cycle <= step_length * 4:
                        temperature = 70
                        state = "1 no disk, undocked"
                    if step_length * 4 < cycle <= step_length * 5:
                        temperature = 80
                        state = "1 no disk, undocked"

                    DetPowMax = max_det_pwrs[fluorophore]

                    # build the line to be written to the output file
                    newline_record = {'CYCLE': int(cycle), 'TIME': str(START_TIME), 'CAR_ID': str(car_id),
                                      'INS_ID': int(INS_ID), 'INS_CAT': str(INS_TYPE), 'FLUO': str(fluorophore),
                                      'FLUO_CODE': str(fluo_code), 'CONC': float(concentration),
                                      'CONC_CODE': str(conc_code), 'STATE': str(state), 'CHAMBER': str(chamber),
                                      'CHANNEL': int(channel), 'T': float(temperature), 'EXC_P': float(exc_power),
                                      'EXC_P_CODE': str(power_code), 'DET_P': float(det_power),
                                      'MAX_DET_P': float(DetPowMax)}
                    if fluorophore in fluo_channels.keys():
                        record.append(newline_record)
            return record
        else:
            for pos in positions:
                channel = right(pos, 1)
                chamber = left(pos, 1)

                # walk through the entire protocol (5 cycles)
                for i in range(5):
                    cycle = i + 1
                    exc_power = exc_pwrs[fluorophore][0]
                    power_code = 'P_nom'

                    # determining if fluorophore is the primary marker of the channel
                    if fluorophore in fluo_channels.keys():
                        if str(fluo_channels[fluorophore]) == channel:
                            fluo_code = 'Main'
                        else:
                            fluo_code = 'Cross'

                    # extract from the backendresult table the value for this cycle/position
                    det_power = datatable[cycle][pos]

                    # retrieve the concentration used in this experiment
                    concentration = concentrations[fluorophore][int(mid(concentration_code, 1, 2))]
                    conc_code = mid(CAR_ID, CAR_ID.find('-') + 1, 3)
                    conc_code = 'C' + str(int(mid(concentration_code, 1, 2)))
                    car_id = CAR_ID
                    state = "6 heated at 65degC"

                    DetPowMax = max_det_pwrs[fluorophore]

                    # build the line to be written to the output file
                    newline_record = {'CYCLE': int(cycle), 'TIME': str(START_TIME), 'CAR_ID': str(car_id),
                                      'INS_ID': int(INS_ID), 'INS_CAT': str(INS_TYPE), 'FLUO': str(fluorophore),
                                      'FLUO_CODE': str(fluo_code), 'CONC': float(concentration),
                                      'CONC_CODE': str(conc_code), 'STATE': str(state), 'CHAMBER': str(chamber),
                                      'CHANNEL': int(channel), 'T': float(temperature), 'EXC_P': float(exc_power),
                                      'EXC_P_CODE': str(power_code), 'DET_P': float(det_power),
                                      'MAX_DET_P': float(DetPowMax)}
                    if fluorophore in fluo_channels.keys():
                        record.append(newline_record)

            return record


def averaging(DS, avg_over_factor, avged_factor):
    print("\n\nAveraging data ...")
    a = DS
    a['ORIGINAL_INDEX'] = a.index
    groupby_factors = [elem for elem in DS.columns if elem not in [avg_over_factor, avged_factor, 'ORIGINAL_INDEX']]
    # ['FLUO', 'INS_ID', 'CONC_CODE', 'CYCLE', 'TIME', 'CAR_ID', 'INS_CAT', 'FLUO_CODE', 'CONC', 'STATE', 'CHANNEL', 'T', 'EXC_P', 'EXC_P_CODE', 'MAX_DET_P']

    a = a.groupby(groupby_factors, as_index=False, observed=True)[['ORIGINAL_INDEX', avged_factor]].mean()  # averaged dataframe
    if DS[avg_over_factor].dtype.name != 'category':
        DS[avg_over_factor] = DS[avg_over_factor].astype('category')
    a[avg_over_factor] = 'avg'
    a = a[DS.columns]
    a.index = a['ORIGINAL_INDEX']
    del a['ORIGINAL_INDEX']
    a = a.rename_axis(None, axis=0)
    print("\n\nDataset averaged.")
    return a


def filtering(DS, **selection):
    selecting = 1
    i = 0
    while selecting:
        # 0 'CYCLE'
        # 1 'TIME'
        # 2 'CAR_ID'
        # 3 'INS_ID'
        # 4 'INS_CAT'
        # 5 'FLUO'
        # 6 'FLUO_CODE',
        # 7 'CONC'
        # 8 'CONC_CODE'
        # 9 'STATE'
        # 10 'CHAMBER'
        # 11 'CHANNEL'
        # 12 'T'
        # 13 'EXC_P'
        # 14 'EXC_P_CODE'
        # 15 'DET_P'
        # 16 'MAX_DET_P'
        # INDEPENDENT Factors consist of [3 'INS_ID', 5 'FLUO', 7 'CONC', 9 'STATE',10 'CHAMBER', 13 'EXC_P']
        # 'FLUO_CODE', 'CONC_CODE' and 'EXC_P_CODE' replaced 'FLUO', 'CONC' and 'EXC_P' to simplify selection process
        # 'INS_ID' is always input because it's the subject of characterization
        selecable_columns = DS.columns[list([6, 8, 9, 10, 14])]
        prompt_Factor = [None] * 2 * len(selecable_columns)
        prompt_Factor[0::2] = list(range(0, len(selecable_columns)))
        prompt_Factor[1::2] = selecable_columns
        prompt_Factor = tuple(prompt_Factor)
        if len(selection) == 0:
            format_str = '\n\n'
            for i, x in enumerate(selecable_columns):
                format_str += '[%s] %s \n'
            print(format_str % prompt_Factor)
            Factor = input('Enter the Factor Code: ')
            selected_Factor = prompt_Factor[int(Factor) * 2 + 1]
        else:
            selected_Factor = list(selection.keys())[i]
        values = DS[selected_Factor]
        values = values.drop_duplicates()
        prompt_Value = [None] * 2 * len(values)
        prompt_Value[0::2] = list(range(0, len(values)))
        prompt_Value[1::2] = list(values.iloc[:])
        prompt_Value = tuple(prompt_Value)
        if len(selection) == 0:
            format_str = '\n\n'
            for i, x in enumerate(values):
                format_str += '[%s] %s \n'
            print(format_str % prompt_Value)
            Value = input('Enter the value code: ')
            selected_value = prompt_Value[int(Value) * 2 + 1]
        else:
            selected_value = list(selection.values())[i]
        DS = DS[DS[selected_Factor] == selected_value]
        if len(selection) == 0:
            selecting = int(input('\n\nContinue with Filtering? (1 = YES, 0 = NO) '))
        else:
            i = i + 1
            if i == len(selection):
                selecting = 0
    return DS


def find_gain_and_offset(x, y):
    X = np.array(x).reshape(-1, 1)
    Y = np.array(y).reshape(-1, 1)
    regressor = LinearRegression()
    regressor.fit(X, Y)
    offset_reg = float(regressor.intercept_)
    offset_direct = float(min(Y))
    offset = max(offset_reg, offset_direct)
    # offset = offset_reg
    gain = float(regressor.coef_)
    output = [gain, offset]
    return output


def reg(DS, input_column, output_column):
    primary_factors = ['FLUO', 'STATE', 'EXC_P_CODE', 'CHAMBER', 'INS_ID', 'CONC', 'DET_P']
    loop_over_factors = [elem for elem in primary_factors if elem not in [input_column, output_column]]
    to_be_removed = []
    for x in loop_over_factors:
        values = DS[x]
        values = values.drop_duplicates()
        if len(values) == 1:
            to_be_removed.append(x)
    for x in to_be_removed:
        loop_over_factors.remove(x)
        sets_DS = DS[
            loop_over_factors].drop_duplicates()  # individual cases of DS where DS is original set before averaging
    for i in range(sets_DS.shape[0]):
        # slicing and sweeping over DS rows based on the values of sets_b
        DS_selected = DS[DS.set_index(loop_over_factors).index.isin(sets_DS.iloc[i:i+1].set_index(loop_over_factors).index)]
        x = list(DS_selected[input_column])
        y = list(DS_selected[output_column])
        [gain, offset] = find_gain_and_offset(x, y)
        sets_DS.loc[sets_DS.index[i], 'GAIN'] = gain
        sets_DS.loc[sets_DS.index[i], 'OFFSET'] = offset
        sets_DS.at[sets_DS.index[i], 'X'] = 0
        sets_DS.at[sets_DS.index[i], 'Y'] = 0
        sets_DS = sets_DS.astype({'X': 'object', 'Y': 'object'})
        sets_DS.at[sets_DS.index[i], 'X'] = x
        sets_DS.at[sets_DS.index[i], 'Y'] = y
        # DS.loc[DS_selected.index, 'GAIN'] = gain
        # DS.loc[DS_selected.index, 'OFFSET'] = offset
    DS.loc[sets_DS.index, 'GAIN'] = sets_DS['GAIN']
    DS.loc[sets_DS.index, 'OFFSET'] = sets_DS['OFFSET']
    DS.at[sets_DS.index, 'X'] = sets_DS['X']
    DS.at[sets_DS.index, 'Y'] = sets_DS['Y']
    reg_result = DS.loc[sets_DS.index]
    return reg_result


def save_to_file(variable, file_name, location):
    print('\n\nSaving data ...')
    os.chdir(location)
    gc.collect()
    tmp = []
    if len(variable)>1e5:
        chunknumber = 3
    else:
        chunknumber = 1
    chunksize = math.ceil(len(variable) / chunknumber)
    write_header = True
    if isinstance(variable, list):
        for i, item in enumerate(variable):
            if i % 10 == 0:
                progress(int(100 * i / len(variable) + 1))
            tmp.append(item)
            if i % chunksize == chunksize - 1:
                df = pd.DataFrame(tmp)
                df.to_csv(file_name + '.csv', header=write_header, index=False, mode='a')
                write_header = False
                df = []
                tmp = []
    elif isinstance(variable, pd.DataFrame):
        for i in range(chunknumber):
            progress(int(100 * (i + 1) / chunknumber ))
            df = variable.iloc[i * chunksize:(i + 1) * chunksize, :]
            df.to_csv(file_name + '.csv', header=write_header, index=False, mode='a')
            write_header = False
            df = []
    print('\n\nDataset saved.')
