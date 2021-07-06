# Importing Libraries
import math
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import equipment
from tqdm import tqdm
from datetime import datetime

# #####################################################################################################################
# ################################################# Globals ###########################################################
# #####################################################################################################################
DATA_PATH = Path.cwd() / 'data'

# #####################################################################################################################
# ################################# Defining the parameters for each equipment ########################################
# #####################################################################################################################

# #################################### Other Parameters ##################################################
# Water purifier
purifier_power_consumption = 0  # Leave it like this now. It will be a function of water consumption

# Capacities at Y0

electrolyzer_capacity = 50_000

# ################################################## Classes ##########################################################
pv_panels_kwargs = {
    'pv_capacity': 10000,
    'unit_nominal_power': 250,
    'panel_unit_area': 1.26084,
    'panel_efficiency': 0.25
}
pv_panel = equipment.PvArray(**pv_panels_kwargs)

# Electrolyzer definition
''' Here I'm just copying the technique used by Sebastian'''
electrolyzer_kwargs = {
    'electrical_consumption': 4_800,  # Wh/Nm3
    'PE_efficiency': 0.98,  # %
    'installed_capacity': 50_000,
    'unit_capacity': 2_400

    # W  How could I do like several simulations for different installed capacities at
    # once, to compare them?
    # I am oversizing the installed capacity to make sure we reach our load.
}
electrolyzer = equipment.Electrolyzer(**electrolyzer_kwargs)

# Compressor definition
compressor_kwargs = {
    'max_flow': 20,  # kg/day
    'max_power_consumption': 4_000,
    'avg_consumption': 6  # kWh/kg
}
compressor = equipment.Compressor(**compressor_kwargs)

# Fuel Cell definition
fuel_cell_kwargs = {
    'fuel_consumption': 0.066,  # g/Wh
    'FC_efficiency': 1  # Not implemented yet.
}
fuel_cell = equipment.FuelCell(**fuel_cell_kwargs)




# #####################################################################################################################
# ########################################### Code to load the data  ##################################################
# #####################################################################################################################
df_grid_prices = pd.read_csv(DATA_PATH / 'grid_tariffs/grid_tariffs.csv')
df_full_irradiation = pd.read_csv(DATA_PATH / 'solar_avg.csv')
df_electrical_load = pd.read_csv(DATA_PATH / 'load_data.csv')
df_hydrogen_load = pd.read_csv(DATA_PATH / 'hydrogen_load_data.csv')
df_GHI = df_full_irradiation[['Day', 'Month', 'Hour end', 'GHI [Wh/m2]']]
df_main = df_GHI.join(df_electrical_load['Load [Wh]'])
df_main = df_main.join(df_hydrogen_load['H2_load [kg]'])
# I start by using an approach of creating columns for each calculation, as in an excel. Then, my idea is to refer a
# previous time-stamp for each line, considering the previous moment's actions.

df_main['PV_Gen Wh'] = pv_panel.power_production(df_main['GHI [Wh/m2]'])


# Solar generation simplified as incoming global horizontal irradiation per m2, times the area, times total efficiency.
# PS! The load needs to consider the compressor's power requirements.

# #####################################################################################################################
# ############################################### Initializing Columns ################################################
# #####################################################################################################################
def initialize_column(df, column_name, fill_value: float = 0.0):
    df[column_name] = fill_value
    return df


# Add new columns
columns_to_be_added = ['Hour',
                       'Minutes',
                       'electrical_load'
                       'total_load',
                       'EL_power_PV',
                       'EL_power_grid',
                       'EL_power_total',
                       'EL_H2_prod_PV kg',
                       'compressor_power',
                       'FC_Power_Out',
                       'FC_H2_consumption',
                       'H2_change',
                       'H2_storage',
                       'DOH',
                       'grid_consumption',
                       'H2_restock',
                       'grid purchases',
                       'water consumption',
                       'purifier power consumption'
                       ]
for column_name in columns_to_be_added:
    df_main = initialize_column(df_main, column_name)


# #####################################################################################################################
# ############################################ Creating DateTime Objects ##############################################
# #####################################################################################################################
def create_date(row):
    # Maybe not use this now to save calculation space
    day = int(row['Day'])
    month = int(row['Month'])
    time = str(row['Hour end'])
    date_str = f'2020-{month:02d}-{day:02d} {time}'
    datetime_object = datetime.strptime(date_str, '%Y-%m-%d %H:%M')
    return datetime_object


df_main['time'] = df_main.apply(create_date, axis=1)

# #####################################################################################################################
# ########################################## Hydrogen Storage Parameters ##############################################
# #####################################################################################################################
DOH_target = 3  # Days of hydrogen
DOH_critical = 1
avg_hydrogen_consumption = 20  # kg/day
storage_target = DOH_target * avg_hydrogen_consumption  # In kg. (days * (kg/day))
storage_max_mass = 100  # kg
storage_initial = 10  # kg
storage_lower_limit = 0.3 * storage_max_mass
storage_critical_limit = 0.1 * storage_max_mass
storage_higher_limit = 0.95 * storage_max_mass
# H2_storage = [storage_initial]

# #####################################################################################################################
# ############################################### Number of Equipment  ################################################
# #####################################################################################################################

# Number of Electrolyzers

number_electrolyzers = math.ceil()

# Number of Compressors
# Number of Storage tanks
# Number of Fuel Cells


# .~.~.~.~.~.~·~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~
# .~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~ Operation  .~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~
# ·~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~

electrolyzer_on = False  # Define this boolean to make the EL work throughout iterations. Turn it off when stock
# is > the higher limit. Make the EL work from the grid only when this variable is on

# ######################################### Iterating through the rows  ###############################################
for i, row in tqdm(df_main.iterrows(), total=df_main.shape[0]):  # .head(20_000)
    # unpacking row
    PV_gen, load, lab_H2_load = row['PV_Gen Wh'], row['Load [Wh]'], row['H2_load [kg]']
    hour = row['time'].hour

    # #################################### Calculating total load at i ################################################
    #
    # skip the first row to avoid i-1 index error
    if i == 0:
        electrical_load = row['Load [Wh]']
        df_main.at[0, 'electrical_load'] = electrical_load
        df_main.at[0, 'DOH'] = storage_initial / avg_hydrogen_consumption  # Divide by approximate daily consumption
        df_main.at[0, 'H2_storage'] = storage_initial
        continue
    else:
        total_load = load + df_main.at[i - 1, 'compressor_power'] + purifier_power_consumption  # The purifier needs to
        # be another column
        df_main.at[i, 'total_load'] = total_load  # I forgot what this is for
        H2_storage = df_main.at[i - 1, 'H2_storage']

    # #################################### Managing Renewable Energy ##################################################
    H2_show_room = 0
    if PV_gen > total_load:  # produce hydrogen
        # Electrolyzer calculations
        electrolyzer_consumption = PV_gen - total_load  # I would need these variables to be all in tables
        H2_show_room = electrolyzer.h2_production_kg(electrolyzer_consumption)  # in kg
        compressor_consumption = compressor.power_consumption(H2_show_room)
        df_main.at[i, 'EL_power_PV'] = electrolyzer_consumption
        df_main.at[i, 'EL_H2_prod_PV kg'] = H2_show_room
        df_main.at[i, 'compressor_power'] = compressor_consumption
    else:  # consume H2
        # Fuel Cell Calculations
        FC_power = total_load - PV_gen
        H2_show_room = - fuel_cell.h2_consumption(FC_power)  # Overly simplified model
        df_main.at[i, 'FC_Power_Out'] = FC_power  # Writing H2 consumption in the FC column
        df_main.at[i, 'FC_H2_consumption'] = H2_show_room

    # Subtracting the Lab's consumption
    H2_change = H2_show_room - lab_H2_load  # Hydrogen load per 15'
    # H2_storage += H2_change
    #   H2_storage = np.clip(df_main.at[i - 1, 'H2_storage'] + H2_change, 0, storage_initial)

    # #################################### Hydrogen stock management ##################################################
    '''
    In the Stock Management algorithm, the electrolysis system will be activated once the storage level reaches a lower 
    limit (Set as ___ but can be a simulation parameter). Once the storage goes under this level, electrolyzers are 
    activated, and they will run until a higher stock capacity is achieved (95% for now).
    
    The idea is to activate the electrolyzers only at night, to avoid higher grid prices. 
    So they have to be deactivated during the day
    
    However, if the storage level reaches a critical limit (<10%), then the electrolyzers are activated independent of
    grid prices.
    
    The code needs to be written in a clear manner as to alter these constraints with ease, in order to simulate hydrogen 
    strategy impact in CAPEX and OPEX.
    
    '''
    additional_power = 0
    additional_h2 = 0
    DOH = H2_storage / avg_hydrogen_consumption
    if H2_storage <= storage_lower_limit:

        # def function H2 at night
        # def function H2 anytime ?
        # H2 calculations...
        if H2_storage > storage_critical_limit and 6 < hour < 20:
            electrolyzer_on = False
        elif H2_storage <= storage_critical_limit:
            electrolyzer_on = True

        pass

    if hour <= 6 or hour >= 20:  # CORRECT     if electrolyzer_on = True, then yes, calculate it
        H2_needed = (DOH_target - DOH) * avg_hydrogen_consumption  # in kg. Maybe here instead I should just refil it
        # to a certain percentage
        if DOH < DOH_target:  # Non critical level
            electrolyzer_on = True
            additional_power = electrolyzer.grid_hydrogen(H2_needed)
            additional_h2 = additional_power / electrolyzer.electrical_consumption * 0.0898  # in kg
            df_main.at[i, 'EL_power_grid'] += additional_power
    else:
        if DOH < DOH_critical:  # This would be the critical level
            additional_power = electrolyzer.grid_hydrogen(H2_needed)  # andando em círculo ?
            df_main.at[i, 'EL_power_grid'] = additional_power  # Wh
            additional_h2 = additional_power / electrolyzer.electrical_consumption * 0.0898  # in kg
        else:
            pass

    df_main.at[i, 'grid purchases'] = additional_power / 1000 * df_grid_prices.at[hour, 'tariff']

    H2_change += additional_h2
    H2_storage += H2_change
    DOH = H2_storage / avg_hydrogen_consumption
    df_main.at[i, 'compressor_power'] += compressor.power_consumption(additional_h2)
    df_main.at[i, 'DOH'] = DOH
    df_main.at[i, 'H2_storage'] = H2_storage
    df_main.at[i, 'H2_change'] = H2_change
    df_main.at[i, 'H2_restock'] = H2_needed
    # Preciso somar os EL ainda. Somar no final? Esse é o final

df_main['EL_power_total'] = df_main['EL_power_grid'] + df_main['EL_power_PV']

# ############################################## Writing the Excel ###################################################

df_main.to_excel(r'C:\Users\gabri\Repositories\HydrogenMicroGrid\Results.xlsx', index=False)

# ################################################# storage plot #####################################################
fig, ax = plt.subplots(1, 1, figsize=(10, 10))
storage = list(df_main['grid purchases'])
ax.plot(np.arange(len(storage)), storage)
ax.set_ylabel('$grid purchases$')
ax.set_xlabel('Time stamp')
plt.show()
# plt.legend(["Balance", "Storage Level"])
# plt.plot(H2_storage)
