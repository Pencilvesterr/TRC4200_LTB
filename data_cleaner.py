import pandas as pd

START_DATE = '2020-02-02 01:10:0'  # Nth data set starts Feb 2nd 1:10:00, so limits range of all datasets
END_DATE = '2020-02-29 23:59:59'


def create_temp_df(fcu_sth_raw, fcu_nth_raw, ahu_raw, start_date=START_DATE, end_date=END_DATE, freq=15):
    """ Create a cleaned data frame for all raw temperature related data."""
    fcu_sth_raw['Timestamp'] = pd.to_datetime(fcu_sth_raw['Timestamp'], dayfirst=True)
    fcu_nth_raw['Timestamp'] = pd.to_datetime(fcu_nth_raw['Timestamp'], dayfirst=True)
    ahu_raw['Timestamp'] = pd.to_datetime(ahu_raw['Timestamp'], dayfirst=True)

    # Merge into single dataframe
    # Sth is in 5 min increments so merged table is in 5 mins
    df_ltb_temps = pd.merge(fcu_sth_raw, fcu_nth_raw, on='Timestamp')
    df_ltb_temps = pd.merge(df_ltb_temps, ahu_raw, on='Timestamp')

    # Clean column titles
    df_ltb_temps.columns = [
        col.replace(' Extended Trend Log', '')
           .replace(' - Trend - Extd', '')
           .replace('-00', '')
           .replace('OaTmp_x', 'OaTmp')
           .replace('OaRH_x', 'OaRH')
        for col in df_ltb_temps.columns
    ]
    df_ltb_temps.drop(['hour', 'OaRH_y', 'OaTmp_y'], axis=1, inplace=True)  # OaRh_y & OaTmp_y are duplicates

    # Limit range
    date_mask = (df_ltb_temps['Timestamp'] >= start_date) & (df_ltb_temps['Timestamp'] <= end_date)
    df_ltb_temps = df_ltb_temps.loc[date_mask]
    df_ltb_temps = df_ltb_temps.set_index('Timestamp').resample(str(freq) + 'min').first()

    return df_ltb_temps


def create_room_info_df(room_info_raw):
    """Clean room info data consistently."""
    # Cleaned the file instead, makes this redundant
    return room_info_raw


def create_chiller_boiler_power_df(chiller_boiler_raw):
    """Create a cleaned data frame for all raw boiler and chiller data."""
    chiller_boiler_raw['Timestamp'] = pd.to_datetime(chiller_boiler_raw['Timestamp'], dayfirst=True)

    # Convert all columns to float
    exclude_timestamp_col = [col for col in chiller_boiler_raw.columns if col != 'Timestamp']
    chiller_boiler_raw = chiller_boiler_raw.replace(',', '', regex=True)
    chiller_boiler_raw[exclude_timestamp_col] = chiller_boiler_raw[exclude_timestamp_col].apply(pd.to_numeric)

    # Clean column titles
    chiller_boiler_raw.columns = [
        col.replace(' - Extended Trend Log', '')
           .replace(' - Ext', '')
           .replace(' Extended Trend Log', '')
           .replace(' Trend Log', '')
        for col in chiller_boiler_raw.columns
    ]

    date_mask = (chiller_boiler_raw['Timestamp'] >= START_DATE) & (chiller_boiler_raw['Timestamp'] <= END_DATE)
    df_chiller_boiler_power = chiller_boiler_raw.loc[date_mask]

    return df_chiller_boiler_power


def get_power_used(df_chiller_boiler_power, start_date=None, end_date=None) -> tuple:
    """Return boiled and chiller kWh for a given time period from raw data.

    Date inputs in 'yyyy-MM-dd' (optional hh:mm:ss)
    """
    # Filter for only date range. If none give, use full daterange
    if start_date and end_date:
        date_mask = (df_chiller_boiler_power['Timestamp'] >= start_date) & (df_chiller_boiler_power['Timestamp'] < end_date)
        df_chiller_boiler_power = df_chiller_boiler_power.loc[date_mask]

    # Clear values of erroneous row
    df_chiller_boiler_power.loc[df_chiller_boiler_power['Timestamp'] == '28/02/2020  1:00:00',
                                df_chiller_boiler_power.columns] = 0

    totals = {}  # Leaving this here incase raw values need to be inspected
    boiler = chiller = 0
    for column in df_chiller_boiler_power:
        if column != 'Timestamp':
            column_sum = sum(df_chiller_boiler_power[column])
            totals[column] = column_sum
            if column.startswith('LTB CH'):
                chiller += column_sum
            elif column.startswith('LTB  BLR'):
                boiler += column_sum

    # kWh to kJ
    boiler = boiler * 3600
    chiller = chiller * 3600

    # Limit sig figs
    boiler = round(boiler, 2)
    chiller = round(chiller, 2)

    return chiller, boiler


if __name__ == '__main__':
    # Personal testing
    df_fcu_sth_raw = pd.read_csv('data/Gnd floor FCU Sth 16032020.csv')
    df_fcu_nth_raw = pd.read_csv('data/Gnd floor FCU North 16032020.csv')
    df_ahu_raw = pd.read_csv('data/Gnd AHU multi list 16032020.csv')
    room_info_raw = pd.read_csv('data/Room Details.csv')
    df_chiller_boiler_raw = pd.read_csv('data/more_Data/chillers boilers thermal Feb 23032020.csv')

    #df_chiller_boiler_power = create_chiller_boiler_power_df(df_chiller_boiler_raw)
    # df_rooms_info = create_room_info_df(room_info_raw)
    df_ltb_temps = create_temp_df(df_fcu_sth_raw, df_fcu_nth_raw, df_ahu_raw)




