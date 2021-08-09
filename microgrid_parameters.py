import pandas as pd
import equipment
from pathlib import Path
import numpy as np
from datetime import datetime

# #####################################################################################################################
# ################################################# Globals ###########################################################
# #####################################################################################################################
DATA_PATH = Path.cwd() / 'data'

# #####################################################################################################################
# ################################# Defining the parameters for each equipment ########################################
# #####################################################################################################################

# ########################################  Parameters of each phase ##################################################
phase_capacity = {
    'P1': {
        'EL_capacity': 3,  # Nm3/h
        'compressor_capacity': 29.75,  # Nm3/h
        'storage_capacity': 16.33,  # kg
        'FC_capacity': 4,  # kW
        'air_filter': 1,
        'cabinets': 2,
        'labour': 10,  # h
        'material': 1,
        'packing': 1,
        'shipping': 1,
    },
    'P2': {
        # capacities acquired?
        'EL_capacity': 3,  # Nm3/h
        'compressor_capacity': 0,  # Nm3/h
        'storage_capacity': 16.33,  # kg
        'FC_capacity': 0,  # kW
        'air_filter': 0,
        'cabinets': 2,
        'labour': 5,  # h
        'material': 1,
        'packing': 1,
        'shipping': 1,
    },
    'P3': {
        # capacities acquired?
        'EL_capacity': 3,  # Nm3/h
        'compressor_capacity': 29.75,  # Nm3/h
        'storage_capacity': 0,  # kg
        'FC_capacity': 4,  # kW
        'air_filter': 0,
        'cabinets': 2,
        'labour': 5,  # h
        'material': 1,
        'packing': 1,
        'shipping': 1,
    }
}

total_capacity = {
    'EL_capacity': 0,
    'compressor_capacity': 0,
    'storage_capacity': 0,
    'FC_capacity': 0,
    'air_filter': 0,
    'cabinets': 0,
    'labour': 0,
    'material': 0,
    'packing': 0,
    'shipping': 0
}

# Defining Class parameters ############################################################################################
pv_panels_kwargs = {
    'pv_capacity': 12000,
    'unit_nominal_power': 250,
    'panel_unit_area': 1.26084,
    'panel_efficiency': 0.25
}
pv_panel = equipment.PvArray(**pv_panels_kwargs)
# Electrolyzer definition
electrolyzer_kwargs = {
    'electrical_consumption': 4_800,  # Wh/Nm3
    'PE_efficiency': 0.98,  # %
    'installed_capacity': 50_000,
    'unit_capacity': 2_400,  # W
    'temp_out': 50,  # ºC
    'p_out': 50,  # bar
    'number_electrolyzer': 20,
    'water_consumption': 0.4  # L/h
}
electrolyzer = equipment.Electrolyzer(**electrolyzer_kwargs)
# Compressor definition
compressor_kwargs = {
    'max_flow': 20,  # kg/day
    'max_power_consumption': 4_000,
    'avg_consumption': 6,  # kWh/kg
    'ip_efficiency': 0.8,
    'm_efficiency': 0.98,
    'e_efficiency': 0.96
}
compressor = equipment.Compressor(**compressor_kwargs)
# Fuel Cell definition
fuel_cell_kwargs = {
    'fuel_consumption': 0.066,  # g/Wh
    'FC_efficiency': 1  # Not implemented yet.
}
fuel_cell = equipment.FuelCell(**fuel_cell_kwargs)
tank_kwargs = {
    'p_min': 40,  # bar
    'p_max': 400,  # bar
    'm_max': 36  # kg -> this one changes in the second year!

}
hydrogen_tank = equipment.HydrogenStorage(**tank_kwargs)
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
                       'electrical_load',
                       'total_load',
                       'PV_to_load',
                       'grid_to_load',
                       'EL_power_PV',
                       'EL_power_grid',
                       'EL_power_total',
                       'EL_H2_prod_PV kg',
                       'EL_H2_prod_grid kg',
                       'EL_ON',
                       'compressor_power',
                       'FC_Power_Out',
                       'FC_H2_consumption',
                       'FC_ON',
                       'H2_change',
                       'H2_storage',
                       'green_hydrogen_level',
                       'grid_hydrogen_level',
                       'DOH',
                       'OOH',
                       'H2_cutoff',
                       'grid_consumption',
                       'H2_restock',
                       'grid_purchases',
                       'water consumption'
                       ]
for column_name in columns_to_be_added:
    df_main = initialize_column(df_main, column_name)


# ############################################ Creating DateTime Objects ##############################################
def create_date(row):
    # Maybe not use this now to save calculation space
    day = int(row['Day'])
    month = int(row['Month'])
    time = str(row['Hour end'])
    date_str = f'2020-{month:02d}-{day:02d} {time}'
    datetime_object = datetime.strptime(date_str, '%Y-%m-%d %H:%M')
    return datetime_object


def create_hour(row):
    # Maybe not use this now to save calculation space
    day = int(row['Day'])
    month = int(row['Month'])
    time = str(row['Hour end'])
    date_str = f'2020-{month:02d}-{day:02d} {time}'
    datetime_object = datetime.strptime(date_str, '%Y-%m-%d %H:%M')
    return datetime_object.hour


df_main['time'] = df_main.apply(create_date, axis=1)
df_main['hour'] = df_main.apply(create_hour, axis=1)
df_main = pd.merge(df_main, df_grid_prices, left_on='hour', right_on='hour', how='left')

# #####################################################################################################################
# ############################################### Yearly calculations #################################################
# #####################################################################################################################

columns_techno_economical = [
    'year',
    'total_solar_energy',
    'EL_installed_capacity',
    'EL_CAPEX',
    'EL_operation_hours',
    'compressor_installed_capacity',
    'compressor_CAPEX',
    'storage_installed_capacity',
    'storage_CAPEX',
    'FC_installed_capacity',
    'FC_CAPEX',
    'grid_electricity_consumed',
    'grid_cost',
    'other_CAPEX',
    'investment_cost',
    'operation_cost',
]

df_yearly = pd.DataFrame(index=np.arange(25))
for column_name in columns_techno_economical:
    df_yearly = initialize_column(df_yearly, column_name)


def equipment_status(el_on, fc_on):
    if el_on and fc_on:
        return 0
    elif el_on:
        return 1
    elif fc_on:
        return -1
