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
# DOH_target = 3  # Days of hydrogen
# DOH_critical = 1
avg_hydrogen_consumption = 20  # kg/day
# storage_target = DOH_target * avg_hydrogen_consumption  # In kg. (days * (kg/day))

# H2_storage = [storage_initial]

# .~.~.~.~.~.~·~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~
# .~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~ Operation  .~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~
# ·~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~

electrolyzer_on = False
electrolyzer_critical = False
fuel_cell_on = False
# Define these booleans to make the EL and FC work throughout iterations. Turn it off when stock is > the higher limit.
# Make the EL work from the grid only when this variable is on


# For the first years: ################################################################################################

EL_capacity = 0
compressor_capacity = 0
storage_capacity = 0
FC_capacity = 0

year = 1
while year < 4:
    for item in total_capacity:
        total_capacity[item] += phase_capacity[f'P{year}'][item]
        item = total_capacity[item]

    # Defining capacities for each year
    EL_capacity = total_capacity['EL_capacity'] * 50_000 / 9  # the installed capacity was in Nm3 there. Do this better?
    equipment.call_electrolyzer(EL_capacity)
    compressor_capacity = total_capacity['compressor_capacity']  # not used yet, as there's no limit to how much the
    # compressor can work
    storage_max_mass = total_capacity['storage_capacity']  # kg
    storage_initial = storage_max_mass * 0.7  # kg
    showroom_tank = 0.2 * storage_max_mass
    grid_tank = 0.8 * storage_max_mass

    storage_lower_limit = 0.3 * storage_max_mass
    storage_critical_limit = 0.1 * storage_max_mass
    storage_higher_limit = 0.95 * storage_max_mass
    FC_capacity = total_capacity['FC_capacity']  # No big impact

    # iteration here *$*$*$*$**
    for i, row in tqdm(df_main.iterrows(), total=df_main.shape[0]):  # .head(20_000)
        # unpacking row
        PV_gen, load, lab_H2_load = row['PV_Gen Wh'], row['Load [Wh]'], row['H2_load [kg]']
        hour = row['hour']
        grid_price = row['tariff']
        # posso calcular isso lá na área dos dados mesmo

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
            H2_change = 0


        # Add the new logic here #######################################################################################

        PV_net = PV_gen - total_load
        if PV_net > 0:
            electrolyzer_on = True
            fuel_cell_on = False
            green_h2 = electrolyzer.h2_production_kg(PV_net)
            grid_h2 = electrolyzer.h2_critical(H2_storage, storage_critical_limit, PV_net)  # Will return 0 if not crit.

            if grid_price < 0.18:  # EL is already ON, so produce as much as possible at a lower fare.






        # ##############################################################################################################
        # skip the first row to avoid i-1 index error

        # #################################### Managing Renewable Energy ###############################################
        H2_show_room = 0
        PV_net = 0
        if PV_gen > total_load:  # produce hydrogen
            # Electrolyzer calculations
            green_power = PV_net = PV_gen - total_load  # I would need these variables to be all in tables
            electrolyzer_on = True
            H2_show_room = electrolyzer.h2_production_kg(PV_net)  # in kg
            PV_to_load = total_load
            df_main.at[i, 'EL_power_PV'] = PV_net
            # If there's renewable energy but storage is full:
            if H2_storage + H2_show_room > storage_max_mass:
                df_main.at[i, 'H2_cutoff'] = (H2_storage + H2_show_room) - storage_max_mass
                H2_show_room = H2_show_room - ((H2_storage + H2_show_room) - storage_max_mass)
            showroom_tank += H2_show_room
            df_main.at[i, 'EL_H2_prod_PV kg'] = H2_show_room
        else:  # consume H2
            # Fuel Cell Calculations
            power_needed = total_load - PV_gen
            PV_to_load = PV_gen
            H2_needed = - fuel_cell.h2_consumption(power_needed)
            # H2_show_room = - fuel_cell.h2_consumption(FC_power)  # Overly simplified model

            if showroom_tank > -1 * H2_needed:
                H2_show_room = H2_needed
                showroom_tank += H2_needed  # H2_needed should be negative here
                FC_power = power_needed
            else:
                H2_show_room = - showroom_tank
                showroom_tank = 0
                FC_power = fuel_cell.electricity_generation(-H2_show_room)
            PV_net = 0
            df_main.at[i, 'FC_Power_Out'] = FC_power
            df_main.at[i, 'FC_H2_consumption'] = H2_show_room
            df_main.at[i, 'green_hydrogen_level'] = showroom_tank

        df_main.at[i, 'PV_to_load'] = PV_to_load

        # Subtracting the Lab's consumption
        lab_load = lab_H2_load / 3 * year

        if lab_load > grid_tank:
            a = 1
            # Consume green hydrogen IF there will be enough there for the next day
        else:
            grid_tank -= lab_load

        H2_change = H2_show_room - lab_load
        H2_storage = grid_tank + showroom_tank  # Grid tank already lost H2 to the lab, and so did the show room.
        # Now the stock management will calculate from after the usages.

        # H2_change = H2_show_room   # Hydrogen load per 15'

        #   H2_storage = np.clip(df_main.at[i - 1, 'H2_storage'] + H2_change, 0, storage_initial)

        # #################################### Hydrogen stock management ###############################################
        additional_power = 0
        additional_h2 = 0

        # Electrolyzer activation loop #################################################################################
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
            H2_needed = storage_higher_limit - H2_storage  # in kg  Should I consider only the grid tank?

            if H2_storage > storage_lower_limit:  # to not produce more when the ELs are using solar and we have a stock
                pass
            else:
                # Max usage:
                max_capacity_available = (electrolyzer.installed_capacity / 4) - PV_net
                additional_power = min(electrolyzer.grid_hydrogen(H2_needed, PV_net if PV_net>0 else 0), max_capacity_available)
                additional_h2 = additional_power / electrolyzer.electrical_consumption * 0.0898  # in kg
                df_main.at[i, 'EL_power_grid'] += additional_power
                df_main.at[i, 'EL_H2_prod_grid kg'] += additional_h2

        else:  # If electrolyzers are off, and level is not critical
            df_main.at[i, 'EL_power_grid'] = 0
            H2_needed = 0
            additional_h2 = 0

        # Boolean columns:
        if H2_storage <= 0:
            df_main.at[i, 'OOH'] = 1
        if electrolyzer_on:
            df_main.at[i, 'EL_ON'] = 1
        if fuel_cell_on:
            df_main.at[i, 'FC_ON'] = 1

        grid_tank += additional_h2
        H2_change += additional_h2

        H2_storage = grid_tank + showroom_tank
        DOH = H2_storage / avg_hydrogen_consumption

        df_main.at[i, 'DOH'] = DOH
        df_main.at[i, 'green_hydrogen_level'] = showroom_tank
        df_main.at[i, 'grid_hydrogen_level'] = grid_tank
        df_main.at[i, 'H2_storage'] = H2_storage
        df_main.at[i, 'H2_change'] = H2_change
        df_main.at[i, 'H2_restock'] = additional_h2
        # Preciso somar os EL ainda. Somar no final? Esse é o final

        # Compressor calculations ######################################################################################
        if H2_change > 0:
            # Like this, the compressor will work whenever there's a positive hydrogen production.
            compressor_consumption = compressor.compressor_energy(
                electrolyzer.p_out, 400, electrolyzer.temp_out + 273, H2_change
            )
            df_main.at[i, 'compressor_power'] = compressor_consumption
        # df_main.at[i, 'compressor_power'] += compressor.power_consumption(additional_h2)  # Is this correct?

    # end of iteration *$*$*$*$*

    df_main['EL_power_total'] = df_main['EL_power_grid'] + df_main['EL_power_PV']
    df_main['total_grid_consumption'] = df_main['grid_consumption'] + df_main['grid_to_load']
    df_main['grid_purchases'] = df_main['total_grid_consumption'] * df_main['tariff']

    # The indicators that change during the first 3 years:
    df_yearly.at[year - 1, 'year'] = year - 1
    df_yearly.at[year - 1, 'EL_installed_capacity'] = EL_capacity
    df_yearly.at[year - 1, 'EL_CAPEX'] = phase_capacity[f'P{year}']['EL_capacity'] * 9_000
    # df_yearly.at[year-1, 'EL_operation_hours'] = count
    df_yearly.at[year - 1, 'compressor_installed_capacity'] = compressor_capacity
    df_yearly.at[year - 1, 'compressor_CAPEX'] = phase_capacity[f'P{year}']['compressor_capacity'] * 80_000
    df_yearly.at[year - 1, 'storage_installed_capacity'] = storage_max_mass
    df_yearly.at[year - 1, 'storage_CAPEX'] = phase_capacity[f'P{year}']['storage_capacity'] * 6_000
    df_yearly.at[year - 1, 'FC_installed_capacity'] = FC_capacity
    df_yearly.at[year - 1, 'FC_CAPEX'] = phase_capacity[f'P{year}']['FC_capacity'] * 20_000
    df_yearly.at[year - 1, 'grid_electricity_consumed'] = sum(df_main['grid_consumption'])  # maybe make a total?
    df_yearly.at[year - 1, 'grid_cost'] = sum(df_main['grid_purchases'])
    df_yearly.at[year - 1, 'hydrogen_produced_PV'] = sum(df_main['EL_H2_prod_PV kg'])
    df_yearly.at[year - 1, 'hydrogen_produced_grid'] = sum(df_main['EL_H2_prod_grid kg'])
    df_yearly.at[year - 1, 'hydrogen_consumed'] = sum(df_main['FC_H2_consumption']) + sum(df_main['H2_load [kg]'])
    # df_yearly.at[year-1, 'other_CAPEX'] = 0
    # df_yearly.at[year-1, 'investment_cost'] = sum()
    # df_yearly.at[year-1, 'operation_cost'] = sum()

    year += 1

# #####################################################################################################################
# ############################################ Calculating over 25 years ##############################################
# #####################################################################################################################

for index, row in df_yearly.iterrows():
    if index > 2:
        df_yearly.at[index, 'year'] = index

        df_yearly.at[index, 'EL_installed_capacity'] = df_yearly.at[2, 'EL_installed_capacity']
        df_yearly.at[index, 'compressor_installed_capacity'] = df_yearly.at[2, 'compressor_installed_capacity']
        df_yearly.at[index, 'storage_installed_capacity'] = df_yearly.at[2, 'storage_installed_capacity']
        df_yearly.at[index, 'FC_installed_capacity'] = df_yearly.at[2, 'FC_installed_capacity']

        df_yearly.at[index, 'EL_operation_hours'] = df_yearly.at[2, 'EL_operation_hours']

        df_yearly.at[index, 'hydrogen_produced_PV'] = df_yearly.at[2, 'hydrogen_produced_PV']
        df_yearly.at[index, 'hydrogen_produced_grid'] = df_yearly.at[2, 'hydrogen_produced_grid']
        df_yearly.at[index, 'hydrogen_consumed'] = df_yearly.at[2, 'hydrogen_consumed']
        df_yearly.at[index, 'grid_electricity_consumed'] = df_yearly.at[2, 'grid_electricity_consumed']
        df_yearly.at[index, 'grid_cost'] = df_yearly.at[2, 'grid_cost']

df_yearly.at[year - 1, 'total_solar_energy'] = sum(df_main['PV_Gen Wh'])
df_yearly['lab_electrical_load'] = sum(df_main['Load [Wh]'])
df_yearly['operation_cost'] = df_yearly['grid_cost']  # + Maintenance? Replacement? Do replacements by hand in the excel

# df_yearly['levelized_cost'] = df_yearly['operation_cost']/((1+interest_rate)**df_yearly['year'])

# ############################################## Writing the Excel ###################################################

df_main.to_excel(r'C:\Users\gabri\Repositories\HydrogenMicroGrid\Results\Main_Case\Results_test.xlsx', index=False)
df_yearly.to_excel(r'C:\Users\gabri\Repositories\HydrogenMicroGrid\Results\Main_Case\yearly_test.xlsx', index=False)

# ################################################# storage plot #####################################################
fig, ax = plt.subplots(1, 1, figsize=(10, 10))
storage = list(df_main['H2_storage'])
ax.plot(np.arange(len(storage)), storage)
ax.set_ylabel('$H2 Storage$')
ax.set_xlabel('Time stamp')
plt.show()
# plt.legend(["Balance", "Storage Level"])
# plt.plot(H2_storage)
