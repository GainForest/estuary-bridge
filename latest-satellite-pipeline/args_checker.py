###########################################################################################
# Check the arguments provided to `latest_sat_img`

import itertools
import re
from datetime import datetime, timedelta

###############################################################
# Helper functions

def check_S2_date(day):
    """
        Check if `day` is in the correct YYYY-MM-DD format, and if it is comprised
        in the temporal bounds of the Sentinel-2 dataset.
    """

    date_format = '%Y-%m-%d' 
    try: date = datetime.strptime(day, date_format)
    except ValueError: raise Exception('Incorrect date format, should be YYYY-MM-DD.')

    # Dataset Availability : 2017-03-28 - basically current date
    beg_avail = datetime(2017, 3, 28)
    end_avail = datetime.today() - timedelta(days=7)
    if not (beg_avail <= date <= end_avail) :
        raise Exception('Provided date not in the range supported by Sentinel-2.')


def subtract_one_month(dt0):
    """
        Substracts one month to date `dt0`.
    """
    dt1 = dt0.replace(day=1)
    dt2 = dt1 - timedelta(days=1)
    dt3 = dt2.replace(day=1)
    return dt3


def add_one_month(dt0):
    """
        Adds one month to date `dt0`.
    """
    dt1 = dt0.replace(day=1)
    dt2 = dt1 + timedelta(days=32)
    dt3 = dt2.replace(day=1)
    return dt3


def check_NICFI_date(day, date_format = '%Y-%m'): 
    """
        Check if `day` is in the correct YYYY-MM format, and if it is comprised
        in the temporal bounds of the NICFI dataset.
    """
    try: date = datetime.strptime(day, date_format)
    except ValueError: raise Exception('Incorrect date format, should be YYYY-MM.')
    # Dataset Availability : 2015-12-01 - 2021-06-29 (bi-annual release)
    beg_avail = datetime(2015, 12, 1)
    end_avail = datetime.today()
    for _ in range(6) : end_avail = subtract_one_month(end_avail)
    if not (beg_avail <= date <= end_avail) :
        raise Exception('Provided date not in the range supported by NICFI.')


def get_timescale(day, time_delta, op) :
    """
        day : provided by the user, format 'YYYY-MM-DD'
        time_delta : number of days before/after `day` the user wants to consider 
        op : `add` or `sub`, operations to perform to get the second date

        returns the timescale (earliest_day, latest_day)
    """

    date = datetime.strptime(day, '%Y-%m-%d')
    if op == 'add' :
        first_day = day
        last_date = date + timedelta(days=time_delta)
        last_day = last_date.strftime("%Y-%m-%d")
    
    elif op == 'sub' :
        first_date = date - timedelta(days=time_delta)
        first_day = first_date.strftime("%Y-%m-%d")
        last_day = day 
    
    return first_day, last_day


def get_month(day, num_months, op):
    """
        day : provided by the user, format 'YYYY-MM'
        num_months : number of months before/after `day` the user wants to consider 
        op : `add` or `sub`, operations to perform to get the second date

        returns the timescale (earliest_day, latest_day), as the first day of the 
        provided month and that of the next, eg. get_month('2021-03') -> '2021-03-01', '2021-04-01'

    """
    date = datetime.strptime(day, '%Y-%m')
    if op == 'add' :
        first_day = date.strftime("%Y-%m-%d")
        last_date = date
        for _ in range(num_months) :
            last_date = add_one_month(last_date)
        last_day = last_date.strftime("%Y-%m-%d")
    elif op == 'sub' :
        last_day = date.strftime("%Y-%m-%d")
        first_date = date
        for _ in range(num_months) :
            first_date = subtract_one_month(first_date)
        first_day = first_date.strftime("%Y-%m-%d")
    return first_day, last_day


def xor(x, y): 
    """
        Implementation of the logical XOR operation.
    """
    return ((x and not y) or (not x and y))


###############################################################
# Actual arguments checker

def is_valid(args):
    print("...checking arguments' validity")

    # sat : either S2 or NICFI
    sat = args.sat 
    if not sat : raise Exception('No satellite selected.')
    if sat not in ['S2', 'NICFI'] : raise Exception('Satellite not supported.')

    start = args.start
    end = args.end
    days = args.d
    weeks = args.w
    months = args.m
    window = (days or weeks or months)
    
    # support either (start, end) or (start, window) or (end, window)
    if not ((start and end) or (start and window) or (end and window)) : 
        raise Exception('No timeframe provided.')
    if (start and end) and window : 
        raise Exception('Cannot support (start,end) as well as timewindow.')
    if any([(a and b) for a,b in itertools.combinations([days, weeks, months], 2)]) : 
        raise Exception('Cannot support timewindow in multiple units.')

    # either start or end is set
    if xor(start,end) : 
        
        if sat == 'S2' : 
            if days : time_delta = days
            elif weeks : time_delta = 7 * weeks
            elif months : time_delta = 28 * weeks

            if start : 
                check_S2_date(start)
                first_day, last_day = get_timescale(start, time_delta, 'add')
                check_S2_date(last_day)

            elif end : 
                check_S2_date(end)
                first_day, last_day = get_timescale(end, time_delta, 'sub')
                check_S2_date(first_day)
            
            first_day, last_day
        
        elif sat == 'NICFI' : 
            if days : raise Exception('NICFI only covers monthly mosaics.')
            elif weeks : raise Exception('NICFI only covers monthly mosaics.')

            if start : 
                check_NICFI_date(start)
                first_day, last_day = get_month(start, months, 'add')
                check_NICFI_date(last_day, date_format = '%Y-%m-%d')
            elif end : 
                check_NICFI_date(end)
                first_day, last_day = get_month(end, months, 'sub')   
                check_NICFI_date(first_day, date_format = '%Y-%m-%d')
            
            first_day, last_day

    # both start and end are set
    else : 

        if sat == 'S2' : 
            check_S2_date(start)
            check_S2_date(end)
        elif sat == 'NICFI' : 
            check_NICFI_date(start)
            check_NICFI_date(end)
        
        first_day, last_day = start, end

    # file : has to be a .geojson
    file = args.file
    if not file : raise Exception('No file provided.')
    if not file.endswith('.geojson') : raise Exception('File provided is not a .geojson')

    # cloud cover in percentage, only for S2
    cloud_cover = args.cloud
    if cloud_cover != 100 : 
        if not (0 <= cloud_cover <= 100) : raise Exception('The cloud cover has to be in [0,100].')
        if sat != 'S2' : raise Exception('Cloud cover filtering is only supported with Sentinel-2.')

    # if name is not supplied, get it from filename
    if not args.name :
        if '/' in file : site_name = re.findall(r'/(\w+)', file)[-1][:-8]
        else : site_name = file[:-8]
    else : site_name = args.name
    
    # continent only supported for NICFI
    continent = args.cont
    if continent and (sat != 'NICFI') : 
        raise Exception('Continent selection is only supported with NICFI.')
    elif (sat == 'NICFI') and (not continent) : 
        raise Exception('Continent selection required for NICFI.')
    elif (sat == 'NICFI') and continent and (continent not in ['asia', 'americas', 'africa']) :
        raise Exception('Continent has to be one of : asia, americas, africa.')

    # - est : save to estuary, default=True
    save_to_estuary = args.est

    return sat, first_day, last_day, file, site_name, cloud_cover, continent, save_to_estuary


