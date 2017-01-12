import csv
import datetime
import os
import pandas as pd
import sys
from collections import defaultdict
from collections import OrderedDict

# This adddress hosts the MTA turnstile data
MTA_url = 'http://web.mta.info/developers/data/nyct/turnstile/'


def get_filenames(start_date, n_weeks):
    """This function returns a list of MTA data file names for the
    period from start_date  spanning n_weeks.
    """
    
    ONE_WEEK = datetime.timedelta(days=7)

    # Identify first Saturday on or after specified date. Files are
    # named for the day when published, which is always a Saturday.

    if None == start_date:
        start_date = datetime.date.today() - n_weeks * ONE_WEEK
        
    first_saturday = start_date + datetime.timedelta(days=5 - start_date.weekday())
    
    # Compose list of requested dates
    
    dates = [first_saturday + ONE_WEEK * i for i in range(n_weeks)]
    
    # Return file names sorted chronologically
    
    return sorted(['turnstile_' + d.strftime('%y%m%d') + '.txt' for d in dates])
    

def read_data(n_weeks=4, start_date=None):
    # Get files to read

    frames = []
    for name in get_filenames(start_date, n_weeks):

        # Create data frame for each file.  If the file exists locally,
        # use it. Otherwise, download it and save a copy for the next
        # time

        if os.path.exists(name):
            print 'reading local', name
            frames.append(pd.read_csv(name))
        else:
            print 'reading url', MTA_url + name
            frames.append(pd.read_csv(MTA_url + name))
            frames[-1].to_csv(name, index=False)

    # Concatenate data frames

    return pd.concat(frames)

def make_dict(df):
    """Convert turnstile data frame to dictionary that maps each STATION
    to a list of { DATE : [TIME, ENTRIES, EXITS], ... } values

    df: Pandas data frame with raw turnstile data
    """

    #   Build dictionary

    d = OrderedDict()
    for row in df.values:
        key = tuple(row[:4])
        date, time, entries, exits = (row[6], row[7], row[9], row[10])
        dt = datetime.datetime.strptime(date + ' ' + time, '%m/%d/%Y %H:%M:%S')
        if 0 == dt.minute + dt.second: # discard invalid times
            d.setdefault(key, []).append([dt, entries, exits])

    #   Convert cumulative counts to increments
    
    for key, counts in d.items():
        for i in range(len(counts) - 1, 0, -1):
            dt1, entries1, exits1 = tuple(counts[i])
            dt2, entries2, exits2 = tuple(counts[i-1])
            if dt1 == dt2 + datetime.timedelta(hours=4):
                counts[i][1] = abs(entries1 - entries2)
                counts[i][2] = abs(exits1 - exits2)
            else:
                counts[i][1] = 0
                counts[i][2] = 0
        counts.pop(0)

    #   :TODO: Clean data

    #   Aggregate counts for each station

    agg = OrderedDict()
    for key, counts in d.items():
        station = key[3]
        for vals in counts:
            dt = vals[0]
            agg.setdefault((station, dt), []).append(vals[1:])

    d = OrderedDict()
    for key, counts in agg.items():
        station, dt = key
        entries, exits = zip(*counts)
        d.setdefault(station, []).append([dt.date(), dt.weekday() + 1, dt.hour, sum(entries), sum(exits)])
        
    return d

def dataframe_from_dict(d):
    flattened = []
    for station, tally in d.items():
        for data in tally:
            flattened.append([station] + data)
    return pd.DataFrame(flattened, columns=['STATION', 'DATE-TIME', 'DATE' 'DAY', 'TIME', 'ENTRIES', 'EXITS'])
        
            
def main(name, action='help', *args):
    df = read_data(12, datetime.date(2016, 6, 1))
    d = make_dict(df)


    with open('mta-summer2016-rev01.csv', 'wb') as csvfile:
        writer = csv.writer(csvfile, delimiter=',')
        writer.writerow(['STATION', 'DATE', 'DAY', 'TIME', 'ENTRIES', 'EXITS'])
        for k, v in d.items():
            for e in v:
                writer.writerow([k] + e)


if __name__ == '__main__':
     main(*sys.argv)
