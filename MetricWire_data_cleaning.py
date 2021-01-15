#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pandas as pd
import numpy as np
import os
from zipfile import ZipFile 
import datetime 
import re
from datetime import datetime, timedelta, date
from IPython.display import clear_output


# ## Loading information with start and end dates of the survey
# 
# study_end_dates.csv (rename to whatever necessary) is assumed to contain survey start and end dates for each participant, their userID, and whether they had GPS tracking on or not during this survey period.
# 
# The last line ensures that there are no empty spaces in the username

# In[2]:


study_info = pd.read_csv('study_end_dates.csv', 
                         dtype={'participantId': np.int16, 
                                'userId': np.str,
                                'tracking_on': np.bool_},
                         parse_dates=['date_study_ends', 'date_study_starts'], 
                         infer_datetime_format=True)   
study_info['userId'] = study_info['userId'].str.strip() 


# ## Automatically extracting zip files in a folder

# In[ ]:


for file_name in os.listdir('/path/to/the/folder'):
    try:
        if file_name[-4:]=='.zip':
            with ZipFile(file_name, 'r') as zip: 
                zip.extractall(path=file_name[:-4])
    except:
        print('{} failed'.format(file_name))


# # QA and Combining csvs
# 1. Ensure 'timeZoneMinutes' == -240, studyId == '5e3b2de163332d0f77a4b055', userId & deviceId are the same
# 2. Drop columns ['_id', 'time', 'timeZoneMinutes', 'studyId', 'triggerId', 'triggerTime']
# 3. Find out time gaps, drop weird entries?
# 4. Is there missing data?
# 
# Exports information about the above errors to the "errors.txt" file

# In[3]:


def qa_check(df, participant_num):
    print('\n{}\n{}\n'.format(participant_num, df.userId.unique()[0]))
    
    if not (df.timeZoneMinutes.unique() == -240).all():
        print('timeZoneMinutes: not one timezone or not EDT\n')
    if len(df.userId.unique()) > 1:
        print('userId: more than 1\n')
    if study_info[study_info.userId == df.userId.unique()[0]].participantId.iloc[0] != participant_num:
        print('userId or participantId: does not match with Pilot Study xls\n')
    if not (df.studyId.unique() == '5e3b2de163332d0f77a4b055').all():
        print('studyId: different study(ies) -> {}\n'.format(df.studyId.unique()))
    if len(df.deviceId.unique()) > 1:
        print('deviceId: {} devices registered\n'.format(len(df.deviceId.unique())))
    
    try:
        df.drop(['time', 'timeZoneMinutes', 'studyId', 'submissionId', 'triggerId', 
                 'triggerTime', 'userId', 'deviceId'], axis=1, inplace=True)
    except:
        print('Could not drop all other columns')
        
    try: 
        df.drop(['_id'], axis=1, inplace=True)
    except:
        pass
    
    end_date = study_info[study_info.participantId == participant_num].date_study_ends.iloc[0] + timedelta(days=1)
    start_date = study_info[study_info.participantId == participant_num].date_study_starts.iloc[0]
    df = df[(df.timestamp < end_date) & (df.timestamp >= start_date)]
    print('{}/{} :: {}/{}'.format(start_date.month,start_date.day,end_date.month, end_date.day-1))
    
    if df.isnull().values.any():
        print('Missing values in the dataset\n')
        
    return df


# In[ ]:


os.chdir('path_to_the/Participant location data/')
         
for folder in os.listdir():
    print('\n' + folder, end ="  ")
    num = re.search(r'\d{4}', folder) # participant number with a length of 4 digits
    try:
        num_participant = int(num.group())
        dfs = []  # an 
        for file_name in os.listdir(folder):
            if '.csv' in file_name:
                dfs.append(pd.read_csv(folder+'/'+file_name, parse_dates=['timestamp'], 
                                       infer_datetime_format=True,
                                      engine='python'))
        data = pd.concat(dfs, ignore_index=True, sort=False)
        del dfs
        data.sort_values(by=['timestamp'], inplace=True)  #sort by time

        with open("errors.txt", 'a') as errors_file:
            data = qa_check(data, num_participant, errors_file)  
        data.to_csv("{}.csv".format(num_participant), index=False)

    except Exception as e:
        print('Could not execute.  ', getattr(e, 'message', repr(e)))
        break


# # Time gaps

# In[14]:


def get_part_of_day(hour):
    return (
        1 if 20 <= hour <= 23
        else
        1 if 0 <= hour <= 7
        else
        0
    )

def calculate_gaps(df, participant_num):
    # Take the diff of the first column (drop 1st row since it's undefined)
    deltas = df.timestamp.diff()[1:]
    gaps_list = []  # contains time gaps stats

    # Filter diffs (here days > 1, but could be seconds, hours, etc)
    gaps = deltas[deltas >= timedelta(minutes=30)]
    gaps_2h = deltas[(deltas >= timedelta(minutes=30)) & (deltas < timedelta(hours=2))]
    gaps_5h = deltas[(deltas >= timedelta(hours=2)) & (deltas < timedelta(hours=5))]
    gaps_9h = deltas[(deltas >= timedelta(hours=5)) & (deltas < timedelta(hours=9))]
    gaps_more = deltas[deltas >= timedelta(hours=9)]
    dict1 = {'participantId': participant_num, 
             'userId': study_info[study_info.participantId == participant_num].userId.iloc[0],
             'tracking_on_metricwire': study_info[study_info.participantId == participant_num].tracking_on.iloc[0],
             'total_records': len(df), '30m_2h': len(gaps_2h), 
             '2h_5h': len(gaps_5h), 
             '2h_5h_nighttime': [get_part_of_day(df.timestamp[i-1].hour) for i, g in gaps_5h.iteritems()].count(1),
             '5h_9h': len(gaps_9h), 
             '5h_9h_nighttime': [get_part_of_day(df.timestamp[i-1].hour) for i, g in gaps_9h.iteritems()].count(1),
             'more_9h': len(gaps_more)
            }

    #####################
    
    d = study_info[study_info.participantId == participant_num].date_study_ends.iloc[0]
    end_date = date(d.year, d.month, d.day)
    d = study_info[study_info.participantId == participant_num].date_study_starts.iloc[0]
    start_date = date(d.year, d.month, d.day)
    delta = end_date - start_date 

    for i in range(delta.days + 1):
        day = start_date + timedelta(days=i)
        if day in df.timestamp.dt.date.unique():
            dict1['day_' + str(i+1)] = 1
            
        else:
            dict1['day_' + str(i+1)] = np.nan   
        
    gaps_list.append(dict1)
        
    ####################
    
    gaps_per_person = []  #gaps for each participant that are more than 4h
    gaps_4h = deltas[(deltas > timedelta(hours=4))]
    for i, g in gaps_4h.iteritems():
        gap_start = df['timestamp'][i-1]
        gaps_per_person.append(
            {
                'start' : datetime.strftime(gap_start, "%m/%d/%y %H:%M"),
                'duration': str(g.to_pytimedelta()),
                'is_nighttime' : get_part_of_day(gap_start.hour)
            }
        )
    pd.DataFrame(gaps_per_person).to_csv('time_gaps/'+str(participant_num)+'.csv', index=False)
    
    return pd.DataFrame(gaps_list)


# In[ ]:


for file_name in os.listdir():
    print('\n' + file_name, end ="  ")
    num = re.search(r'\d{4}', file_name)
    if num and '.csv' in file_name:
        try:
            num_participant = int(num.group())
            data = pd.read_csv(file_name, parse_dates=['timestamp'], infer_datetime_format=True)
            if len(data)==0:
                print('||  empty file', end ="")
                continue
            gaps = calculate_gaps(data, num_participant)
            if not os.path.isfile('time_gaps/time_statistics.csv'):
                gaps.to_csv('time_gaps/time_statistics.csv', index=False, header ='column_names')
            else:
                gaps.to_csv('time_gaps/time_statistics.csv', mode='a', index=False, header=False)
        except Exception as e:
            print('Could not execute.  ', getattr(e, 'message', repr(e)))         
    else:
        print('not a participant csv')

