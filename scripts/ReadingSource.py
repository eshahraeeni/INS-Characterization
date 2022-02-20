import datetime
import glob
import os
import pandas as pd
import functions as custom_fun

# record the start time
time_start_main_loop = datetime.datetime.now()
scripts_loc = os.getcwd()
os.chdir('..\\source files')
source_loc = os.getcwd()
os.chdir('..\\result files')
result_loc = os.getcwd()

# set check = 1 for a quick check with limited files instead of complete set. Check files to be copied into \\check
# directory within source_loc
check = 0
if check == 1:
    source_loc = source_loc + '\\check'
data_file = result_loc + '\data_file.csv'

try:
    with open(data_file, 'r') as f:
        Files_to_be_read = 0
except FileNotFoundError:
    Files_to_be_read = 1

if Files_to_be_read:

    # find all files
    os.chdir(source_loc)
    files = glob.glob('*BackEndResults*.txt', recursive=True)
    print('Found ', str(len(files)), ' files')

    print('\n\nStart file processing...')
    dataset = []

    for i, file in enumerate(files):
        # process the file
        dataset += custom_fun.processFile(source_loc, file)
        custom_fun.progress(int(100 * i / len(files) + 1))

    df = pd.DataFrame(dataset)

    custom_fun.save_to_file(dataset, 'data_file', result_loc)

    Files_to_be_read = 0
    # record the end time and display total processing time
    print('\n\nExit')

else:
    print('\n\nA saved data file already exists in the folder ...')
    print('\n\nExit')