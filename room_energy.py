import pandas as pd

CEIL_HEIGHT = 2.7  # m
COEFF_AIR = 1.012  # J/(g⋅K)
RHO = 1225  # g/m3
U_GLASS = 2.7  # W/m²K Assuming 4mm / 16mm air / 4mm
U_CONCRETE = 1.45 #Source for this here: http://www.concrete.org.uk/fingertips-document.asp?id=593
ahu_lookup = {
        'AHU-01': 'AHU-01 Internal ZnTmp_1',
        'AHU-B1-01': 'AHU-B1-01 ZnTmp_1',
        'AHU-B1-02': 'AHU-B1-02 ZnTmp_1'
    }

## Air Leakage Params:
AIR_PERMEABILITY = 0.8 #litre/hour

# @brief: Calculates the energy from all rooms. To use individual rooms, use the energyLossRoom function
def energyLossAllRooms(df_ltb_temps, df_room_info, time_frame=["06:00", "18:00"], calc_type='normal'):
    # Update time period
    df_ltb_temps_sampled = df_ltb_temps.between_time(time_frame[0], time_frame[1])
    arg = calc_type
    energy_loss_dict = {}
    for _, current_room_row in df_room_info.iterrows():
        energy_loss = _energyLossRoom(current_room_row, df_ltb_temps_sampled, arg)
        energy_loss_dict[current_room_row['Room Name']] = energy_loss

    df = pd.DataFrame(data=energy_loss_dict)
    df_energy_change = df.reindex(sorted(df.columns), axis=1)  # Sort columns alphabetically

    return df_energy_change


# @param room_dimen_list a panda dataframe object frame.
# @param time_step integer value of the number of minutes between each temperature reading.
# @param time_frame String list input of the hours of interest.
# @param room_height float value for the height of the wall with respect to the room ceiling.
# @param Cp dry air specific heat constant (J*g/K)
# @param rho density of air
# Output is in kiloJoules.
# Assumptions: wall height is approx. one storey which is 3.3m
def _energyLossRoom(room_row, df_ltb_temps, arg):
    room_area = room_row['Total Area']
    room_volume = room_area * CEIL_HEIGHT
    current_room_unit = room_row['AHU / FCU']
    temp_list = _getTempRoom(current_room_unit, df_ltb_temps)
    if arg == 'airLeak':
        leak_num = AIR_PERMEABILITY*room_volume/(3600*20)
        return (temp_list) * COEFF_AIR * RHO * room_volume * leak_num / 1000
    else:
        return (temp_list) * COEFF_AIR * RHO * room_volume / 1000

# @brief Calclulate the temperature difference of the room given the unit name. Outputs in percentage.
# @param current_room_unit String input of the Cooling unit for the respective room
# @param time_period Integer input of the time_frame of interest.
# @param time_frame String list input of the hours of interest.
def _getTempRoom(current_room_unit, df_ltb_temps):
    # Isolate to the specific operating hours of interest:
    if 'FCU' in current_room_unit:
        temp_idx = current_room_unit + ' ZnTmp'
    else:
        temp_idx = ahu_lookup[current_room_unit]
    # Calculate difference between each cell:
    change_in_temp = df_ltb_temps[temp_idx].diff()
    return change_in_temp


def energy_to_building(df_ltb_temps, df_room_info, time_frame=["06:00", "18:00"], freq=15):
    AC_units = df_room_info['AHU / FCU']
    df_energy_received = pd.DataFrame(index=df_ltb_temps.index)
    for AC_unit in AC_units:
        df_room_energy = _energy_to_room(df_ltb_temps, df_room_info, AC_unit, freq)
        df_energy_received = df_energy_received.join(df_room_energy)
    
    df = df_energy_received.between_time(time_frame[0], time_frame[1])
    df_energy_received = df.reindex(sorted(df.columns), axis=1)  # Sort columns alphabetically

    return df_energy_received
    
        
def _energy_to_room(df_ltb_temps, df_room_info, AC_unit, freq=15):
    external_wall = float(df_room_info.loc[df_room_info['AHU / FCU'] == AC_unit]['External Wall Length'])
    room_name = str(df_room_info.loc[df_room_info['AHU / FCU'] == AC_unit]['Room Name'].iloc[0])
    zn_tmp = AC_unit + ' ZnTmp' if 'FCU' in AC_unit else ahu_lookup[AC_unit]
    # Assuming that that heat is gained/lost from the external facing wall of each too
    # and equal length internal facing wall made of the same glass.
    # Internal temp is based off FCU in a corridor to main area
    delta_temp_external = df_ltb_temps['OaTmp'] - df_ltb_temps[zn_tmp]
    delta_temp_internal = df_ltb_temps['FCU-24 ZnTmp'] - df_ltb_temps[zn_tmp]

    watts_external = U_GLASS * (external_wall * CEIL_HEIGHT) * delta_temp_external
    watts_internal_glass = U_GLASS * (external_wall * CEIL_HEIGHT) * delta_temp_internal
    watts_internal_concrete = U_CONCRETE * (external_wall * CEIL_HEIGHT)* 2 * delta_temp_internal

    delta_t = (freq * 60)  # seconds between timesteps
    return_df = pd.DataFrame(index=df_ltb_temps.index)
    return_df[room_name] = (watts_external + watts_internal_glass + watts_internal_concrete) * delta_t / 1000  # kJ transferee during this time period
                
    return return_df


if __name__ == '__main__':
    # Unit testing
    from data_cleaner import *

    df_fcu_sth_raw = pd.read_csv('data/Gnd floor FCU Sth 16032020.csv')
    df_fcu_nth_raw = pd.read_csv('data/Gnd floor FCU North 16032020.csv')
    df_ahu_raw = pd.read_csv('data/Gnd AHU multi list 16032020.csv')
    df_chiller_boiler_raw = pd.read_csv('data/more_Data/chillers boilers thermal Feb 23032020.csv')
    room_info_raw = pd.read_csv('data/Room Details.csv')

    df_ltb_temps = create_temp_df(df_fcu_sth_raw, df_fcu_nth_raw, df_ahu_raw)
    df_chiller_boiler_power = create_chiller_boiler_power_df(df_chiller_boiler_raw)
    df_room_info = create_room_info_df(room_info_raw)

    df_ltb_temps = df_ltb_temps.drop(
        ['AHU-B1-02 ZnTmp_1', 'AHU-B1-02 ZnTmp_2', 'FCU-16 ZnTmp', 'FCU-15 ZnTmp'], axis=1)
    df_room_info = df_room_info[df_room_info['AHU / FCU'] != 'AHU-B1-02']
    df_room_info = df_room_info[df_room_info['AHU / FCU'] != 'FCU-16']
    df_room_info = df_room_info[df_room_info['AHU / FCU'] != 'FCU-15']

    #df_energy_change = energyLossAllRooms(df_ltb_temps, df_room_info)
    df_energy_in = energy_to_building(df_ltb_temps, df_room_info)

    print(df_energy_in)

