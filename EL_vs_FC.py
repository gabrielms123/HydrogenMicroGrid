# Importing Libraries
import math
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import equipment
from tqdm import tqdm
from datetime import datetime
from microgrid_parameters import *

# #####################################################################################################################
# ########################################## Hydrogen Storage Parameters ##############################################
# #####################################################################################################################
DOH_target = 3  # Days of hydrogen
DOH_critical = 1
avg_hydrogen_consumption = 20  # kg/day
storage_target = DOH_target * avg_hydrogen_consumption  # In kg. (days * (kg/day))
storage_max_mass = 33  # kg
storage_initial = 30  # kg
storage_lower_limit = 0.3 * storage_max_mass
storage_critical_limit = 0.1 * storage_max_mass
storage_higher_limit = 0.95 * storage_max_mass
# H2_storage = [storage_initial]

# .~.~.~.~.~.~·~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~
# .~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~ Operation  .~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~
# ·~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~

# for y in df_years:

electrolyzer_on = False
electrolyzer_critical = False
# Define this boolean to make the EL work throughout iterations. Turn it off when stock
# is > the higher limit. Make the EL work from the grid only when this variable is on


# For the first years: ################################################################################################

# EL_capacity = 0
# compressor_capacity = 0
# storage_capacity = 0
# FC_capacity = 0

year = 1
while year < 4:
    for item in total_capacity:
        total_capacity[item] += phase_capacity[f'P{year}'][item]
        item = total_capacity[item]
    year += 1

    # Here the whole iterating rows

    # df_main['columns to do simple operations'] = operation ***

    # The indicators that change during the first 3 years:
    # df_yearly.at[year - 1, 'hydrogen_cost'] = sum(df_main['column'])
    # df_yearly.at[year-1, 'OOS'] = sum(df_basecase['OOS'])/96
    # df_yearly.at[year-1, 'hydrogen_consumed'] = sum(df_basecase['hydrogen_consumed'])
    # df_yearly.at[year - 1, 'delivery_cut_off'] = sum(df_basecase['delivery_cut_off'])


    year += 1



    # EL_capacity = total_capacity['EL_capacity']
    # compressor_capacity = total_capacity['compressor_capacity']
    # storage_capacity = total_capacity['storage_capacity']
    # FC_capacity = total_capacity['FC_capacity']

    # Vai complicar que preciso colocar isso na classe depois.

# ######################################### Iterating through the rows  ###############################################

for i, row in tqdm(df_main.iterrows(), total=df_main.shape[0]):  # .head(20_000)
    # unpacking row
    PV_gen, load, lab_H2_load = row['PV_Gen Wh'], row['Load [Wh]'], row['H2_load [kg]']
    hour = row['time'].hour
    grid_price = df_grid_prices.at[hour, 'tariff']

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
        total_load = load + df_main.at[i - 1, 'compressor_power']  # The purifier needs to
        # be another column
        df_main.at[i, 'total_load'] = total_load  # I forgot what this is for
        H2_storage = df_main.at[i - 1, 'H2_storage']

    # Electrical load management #######################################################################################
    H2_show_room = 0
    PV_net = 0
    if PV_gen > total_load:  # produce hydrogen
        # Electrolyzer calculations
        electrolyzer_on = True
        PV_to_load = total_load
        PV_net = PV_gen - PV_to_load  # I would need these variables to be all in tables
        H2_show_room = electrolyzer.h2_production_kg(PV_net)  # in kg
        flux = 1  # energy flux 1 to generate H2, -1 to consume in the FC.
        grid_to_load = 0
        df_main.at[i, 'EL_power_PV'] = PV_net
        df_main.at[i, 'EL_H2_prod_PV kg'] = H2_show_room

    else:  # consume H2
        PV_to_load = PV_gen
        if electrolyzer_on:
            # This means I'm prioritizing producing H2 instead of using the fuel cell. Since the FC is not super
            # efficient, maybe it's better to use the grid directly.
            FC_power = 0
            H2_show_room = 0
            grid_to_load = total_load - PV_to_load
        else:
            # Fuel Cell Calculations
            FC_power = total_load - PV_gen
            H2_show_room = - fuel_cell.h2_consumption(FC_power)  # Overly simplified model
            df_main.at[i, 'FC_Power_Out'] = FC_power  # Writing H2 consumption in the FC column
            PV_net = 0
            grid_to_load = 0

            # Note that here I'm considering the FC will ALWAYS be able to fulfill the electrical load. FC is oversized.
    df_main.at[i, 'FC_H2_consumption'] = H2_show_room
    df_main.at[i, 'PV_to_load'] = PV_to_load
    df_main.at[i, 'grid_to_load'] = grid_to_load

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

    # Electrolyzer activation loop #####################################################################################
    if grid_price < 0.2:  # If in cheap hours
        if not electrolyzer_on and H2_storage <= storage_lower_limit:
            electrolyzer_on = True
        elif electrolyzer_on and H2_storage <= storage_higher_limit:  # Keep running
            electrolyzer_on = True
        else:  # turn off
            electrolyzer_on = False
        # to a certain percentage
    else:
        if H2_storage < storage_critical_limit and not electrolyzer_on:  # This would be the critical level
            electrolyzer_on = True
            electrolyzer_critical = True
        elif electrolyzer_critical and H2_storage > 2 * storage_lower_limit:
            electrolyzer_critical = False
            electrolyzer_on = False
        else:
            electrolyzer_on = False

    if electrolyzer_on or electrolyzer_critical:
        flux = 1
        H2_needed = storage_higher_limit - H2_storage  # in kg

        # Max usage:
        max_capacity_available = (electrolyzer.installed_capacity / 4) - PV_net
        additional_power = min(electrolyzer.grid_hydrogen(H2_needed), max_capacity_available)
        additional_h2 = additional_power / electrolyzer.electrical_consumption * 0.0898  # in kg
        df_main.at[i, 'EL_power_grid'] += additional_power
        df_main.at[i, 'EL_H2_prod_grid kg'] += additional_h2

    else:
        df_main.at[i, 'EL_power_grid'] = 0
        additional_h2 = 0
        H2_needed = 0

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

    # Compressor calculations ##########################################################################################
    if H2_change > 0:
        # Like this, the compressor will work whenever there's a positive hydrogen production.
        compressor_consumption = compressor.compressor_energy(
            electrolyzer.p_out, 400, electrolyzer.temp_out + 273, H2_change
        )
        df_main.at[i, 'compressor_power'] = compressor_consumption

df_main['EL_power_total'] = df_main['EL_power_grid'] + df_main['EL_power_PV']

# ############################################## Writing the Excel ###################################################

df_main.to_excel(r'C:\Users\gabri\Repositories\HydrogenMicroGrid\Results\EL_vs_FC\EL_vs_FC.xlsx', index=False)

# ################################################# storage plot #####################################################
fig, ax = plt.subplots(1, 1, figsize=(10, 10))
storage = list(df_main['H2_storage'])
ax.plot(np.arange(len(storage)), storage)
ax.set_ylabel('$H2 Storage$')
ax.set_xlabel('Time stamp')
plt.show()
# plt.legend(["Balance", "Storage Level"])
# plt.plot(H2_storage)
