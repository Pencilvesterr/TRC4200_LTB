import pandas as pd


def energy_to_building(df_ltb_temps, df_room_info, freq=15):
    excluded_cols = {'OaRH', 'OaTmp', 'Timestamp', 'FCU-24'}  # Ignoring FCU-24 as it's a cooridor. Not fixed volume
    temp_cols = set([col.split(' ')[0] for col in df_ltb_temps.columns])
    AC_units = list(temp_cols.difference(excluded_cols))

    df_energy_received = pd.DataFrame(df_ltb_temps['Timestamp'])
    for AC_unit in AC_units:
        df_room = _energy_to_room(df_ltb_temps, df_room_info, AC_unit, freq)
        df_energy_received = pd.merge(df_energy_received, df_room, on='Timestamp')

    df_energy_received = df_energy_received.resample(str(freq) + 'min', on='Timestamp').first().dropna()
    return df_energy_received


def _energy_to_room(df_ltb_temps, df_room_info, AC_unit, freq=15):
    U_GLASS = 2.7  # W/m²K
    CEIL_HEIGHT = 3.3
    external_wall = float(df_room_info.loc[df_room_info['AHU / FCU'] == AC_unit]['External Wall Length'])
    room_name = str(df_room_info.loc[df_room_info['AHU / FCU'] == AC_unit]['Room Name'].iloc[0])

    ahu_lookup = {
        'AHU-01': 'AHU-01 Internal ZnTmp_1',
        'AHU-B1-01': 'AHU-B1-01 ZnTmp_1',
        'AHU-B1-02': 'AHU-B1-02 ZnTmp_1'
    }
    if 'FCU' in AC_unit:
        delta_temp = df_ltb_temps[AC_unit + ' ZnTmp'] - df_ltb_temps['OaTmp']
    else:
        zn_tmp = ahu_lookup[AC_unit]
        delta_temp = df_ltb_temps[zn_tmp] - df_ltb_temps['OaTmp']

    delta_t = (freq * 60)  # seconds between timesteps
    ret_df = pd.DataFrame(df_ltb_temps['Timestamp'])
    incoming_watts = U_GLASS * (external_wall * CEIL_HEIGHT) * delta_temp
    ret_df[room_name] = incoming_watts * delta_t / 1000  # kJ transfered during this time period

    return ret_df

