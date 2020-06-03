import pandas as pd

ahu_lookup = {
        'AHU-01': 'AHU-01 Internal ZnTmp_1',
        'AHU-B1-01': 'AHU-B1-01 ZnTmp_1',
        'AHU-B1-02': 'AHU-B1-02 ZnTmp_1'
    }

# @brief: Calculates the energy from all rooms. To use individual rooms, use the energyLossRoom function
def energyLossAllRooms(df_room_info):
    energy_loss_dict = {}
    for _, current_room in df_room_info.iterrows():
        energy_loss = _energyLossRoom(current_room)
        energy_loss_dict[current_room[0]] = energy_loss
    return pd.DataFrame(data=energy_loss_dict)


# @param room_dimen_list a panda dataframe object frame.
# @param time_step integer value of the number of minutes between each temperature reading.
# @param time_frame String list input of the hours of interest.
# @param room_height float value for the height of the wall with respect to the room ceiling.
# @param Cp dry air specific heat constant (J*g/K)
# @param rho density of air
# Output is in kiloJoules.
# Assumptions: wall height is approx. one storey which is 3.3m
def _energyLossRoom(room, time_step=15, time_frame=["06:00", "18:00"], room_height=3.3, Cp=1.00, rho=1275):
    room_height = room_height
    coeff_air = Cp
    update_freq = time_step
    room_area = room[2]
    if room[3] == 0:
        return 0
    wall_area = room[3]*room_height
    current_room_unit = room[1]
    temp_list = _getTempRoom(current_room_unit, update_freq, time_frame)
    return (temp_list)*coeff_air*rho*room_area/1000

# @brief Calclulate the temperature difference of the room given the unit name. Outputs in percentage.
# @param current_room_unit String input of the Cooling unit for the respective room
# @param time_period Integer input of the time_frame of interest.
# @param time_frame String list input of the hours of interest.
def _getTempRoom(current_room_unit, update_freq, time_frame):
    ahu_fcu_sample = df_ltb_temps.resample(str(update_freq)+'min', on='Timestamp').first()
    # Isolate to the specific operating hours of interest:
    sampled_period = ahu_fcu_sample.between_time(time_frame[0], time_frame[1])
    if 'FCU' in current_room_unit:
        temp_idx = current_room_unit + ' ZnTmp'
    else:
        temp_idx = ahu_lookup[current_room_unit]
    # Calculate difference between each cell:
    change_in_temp = sampled_period[temp_idx].diff()
    return change_in_temp


def energy_to_building(df_ltb_temps, df_room_info, time_frame=["06:00", "18:00"], freq=15):
    excluded_cols = {'OaRH','OaTmp','Timestamp', 'FCU-24'}  # Ignoring FCU-24 as it's a cooridor. Not fixed volume
    temp_cols = set([col.split(' ')[0] for col in df_ltb_temps.columns])
    AC_units = list(temp_cols.difference(excluded_cols))
    df_ltb_temps_sampled = df_ltb_temps.set_index('Timestamp').resample(str(freq)+'min').first().dropna()
    df_energy_received = pd.DataFrame(index=df_ltb_temps_sampled.index)
    for AC_unit in AC_units:
        df_room = _energy_to_room(df_ltb_temps_sampled, df_room_info, AC_unit, freq)
        df_energy_received = df_energy_received.join(df_room)
    
    df_energy_received = df_energy_received.between_time(time_frame[0], time_frame[1])

    return df_energy_received
    
        
def _energy_to_room(df_ltb_temps, df_room_info, AC_unit, freq=15):
    U_GLASS = 2.7  # W/m²K
    CEIL_HEIGHT = 3.3
    external_wall = float(df_room_info.loc[df_room_info['AHU / FCU'] == AC_unit]['External Wall Length'])
    room_name = str(df_room_info.loc[df_room_info['AHU / FCU'] == AC_unit]['Room Name'].iloc[0])
    
    if 'FCU' in AC_unit:
        delta_temp = df_ltb_temps[AC_unit + ' ZnTmp'] -  df_ltb_temps['OaTmp']
    else:
        zn_tmp = ahu_lookup[AC_unit]
        delta_temp = df_ltb_temps[zn_tmp] -  df_ltb_temps['OaTmp']
    
    delta_t = (freq * 60)  # seconds between timesteps
    return_df = pd.DataFrame(index=df_ltb_temps.index)
    incoming_watts = U_GLASS * (external_wall * CEIL_HEIGHT) * delta_temp
    return_df[room_name] = incoming_watts * delta_t / 1000 # kJ transfered during this time period
                
    return return_df