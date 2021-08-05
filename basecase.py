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
# TODO 0. LT = 1 day, Order when stock is at half, or weekly delivery.
# TODO 1. Change the calculation here to a "import H2" function that will work when electrolyzer capacity is zero.
# TODO 2. Create a power provide function that would use the FC when installed cap>0, or from the grid when no FC is av.
# TODO 3. Create a Lab FC separate function to calculate the electricity that could be collected from the lab.

# #####################################################################################################################
# ################################################# Globals ###########################################################
# #####################################################################################################################
DATA_PATH = Path.cwd() / 'data'
clamp = lambda n, minn, maxn: max(min(maxn, n), minn)

# ############################################### loading data  #######################################################
df_grid_prices = pd.read_csv(DATA_PATH / 'grid_tariffs/grid_tariffs.csv')  # €/kWh
df_full_irradiation = pd.read_csv(DATA_PATH / 'solar_avg.csv')
df_electrical_load = pd.read_csv(DATA_PATH / 'load_data.csv')
df_hydrogen_load = pd.read_csv(DATA_PATH / 'hydrogen_load_data.csv')
df_GHI = df_full_irradiation[['Day', 'Month', 'Hour end', 'GHI [Wh/m2]']]
df_basecase = df_GHI.join(df_electrical_load['Load [Wh]'])
df_basecase = df_basecase.join(df_hydrogen_load['H2_load [kg]'])


# #####################################################################################################################
# ################################################## Functions  #######################################################
# #####################################################################################################################
def initialize_column(df, column_name, fill_value: float = 0.0):
    df[column_name] = fill_value
    return df


def hydrogen_delivery(storage_level, max_storage, lead_time, hydrogen_price, delivering: bool):
    if storage_level < max_storage / 2:  # Place an order
        if delivering and i < size_basecase - 1:
            pass
        else:
            try:
                buy_bottles = np.ceil((max_capacity / 2 + lead_time * avg_h2_day) / bottle_cap)
                df_basecase.at[i, 'buy_order'] = 1
                delivery_index = 35039 if i + lead_time * 96 > 35039 else i + lead_time * 96
                df_basecase.at[delivery_index, 'buy_quantity'] = buy_bottles
                waiting_delivery = True
            except IndexError:
                pass

    return 1



# #####################################################################################################################
# ################################## Function to Create DateTime Objects ##############################################
# #####################################################################################################################
def create_date(row):
    # Maybe not use this now to save calculation space
    day = int(row['Day'])
    month = int(row['Month'])
    time = str(row['Hour end'])
    date_str = f'2020-{month:02d}-{day:02d} {time}'
    datetime_object = datetime.strptime(date_str, '%Y-%m-%d %H:%M')
    return datetime_object


# #####################################################################################################################
# ##################################################### Parameters ####################################################
# #####################################################################################################################
bottle_cap = 8.9 * 0.0898  # kg
bottle_pressure = 200  # bar. Probably won't use.
hydrogen_price = 6  # €/kg
max_capacity = 100  # Rounding down the calculation below
# 7 * 96 * np.average(df_basecase['H2_load [kg]']) * 2  # Max capacity is the equivalent of 1 week
# consumption
max_bottles = np.ceil(max_capacity / bottle_cap)  # Not exceeding a week's worth of stock
avg_h2_day = 6.4  # made-up daily average
# avg_h2_week = 45  # made-up weekly average

lead_time = 2  # days
interest_rate = 0.06
# #####################################################################################################################
# ############################################ Creating a 15 min table ################################################
# #####################################################################################################################

# Add new columns
columns_to_be_added = ['hour',
                       'Minutes',
                       'h2_load_MA',
                       'hydrogen_consumed',
                       'electrical_load',
                       'grid_cost',
                       'H2_storage',
                       'DOH',
                       'buy_order',
                       'buy_quantity',
                       'buy_price',
                       'OOS',
                       'delivery_cut_off'
                       ]
for column_name in columns_to_be_added:
    df_basecase = initialize_column(df_basecase, column_name)

df_basecase['time'] = df_basecase.apply(create_date, axis=1)
df_basecase['h2_load_MA'] = pd.Series(df_basecase['H2_load [kg]'].rolling(7 * 96, center=True, min_periods=1)
                                      .mean())  # Moving Average. For some reason it's not very smooth

# ######### Plotting Loads #######
h2_consumption_1D = np.array(df_basecase['H2_load [kg]'])
number_quarters = 96  # data points in a day
number_days = int(h2_consumption_1D.shape[0] / number_quarters)
h2_consumption_2D = h2_consumption_1D.reshape(number_days, number_quarters)
# plt.imshow(h2_consumption_2D, cmap='hot')
# plt.xlabel('Time of day')
# plt.ylabel('Day of year')
# plt.colorbar()
# plt.show()

# #####################################################################################################################
# ############################################ Creating a 25 year table ###############################################
# #####################################################################################################################
columns_techno_economical = [
    'year',
    'grid_electricity_consumed',
    'yearly_grid_cost',
    'investment_cost',
    'hydrogen_consumed',
    'hydrogen_cost',
    'operation_cost',
    'OOS',
    'levelized_cost'
]

df_yearly = pd.DataFrame(index=np.arange(25))

for column_name in columns_techno_economical:
    df_yearly = initialize_column(df_yearly, column_name)

df_yearly['year'] = df_yearly.index

# #####################################################################################################################
# ############################################ Calculating over one year ##############################################
# #####################################################################################################################

df_basecase['hour'] = df_basecase['time'].dt.hour
df_basecase = df_basecase.merge(df_grid_prices, on='hour', how='left')
df_basecase['grid_cost'] = df_basecase['tariff'] * df_basecase['Load [Wh]'] / 1000
size_basecase = len(df_basecase)

year = 1  # Investment day
while year < 4:
    df_basecase['H2_storage'] = 0.0000001
    df_basecase['buy_quantity'] = 0.0
    df_basecase['buy_order'] = 0.0
    df_basecase['buy_price'] = 0.0
    df_basecase['DOH'] = 0.0
    df_basecase['OOS'] = 0.0
    # It would be nice to store these variables in the df_yearly later!
    for i, row in tqdm(df_basecase.iterrows(), total=df_basecase.shape[0]):  # .head(20_000)
        # unpacking row
        electrical_load, lab_H2_load = row['Load [Wh]'], row['H2_load [kg]']  # Taking a super long time here!
        lab_H2_load = lab_H2_load * year
        # max_capacity = max_capacity * year / 3 Quebrou o código
        # When placing an order, store the i.
        df_basecase.at[i, 'hydrogen_consumed'] = lab_H2_load
        if i == 0:
            waiting_delivery = False
            df_basecase.at[0, 'electrical_load'] = electrical_load
            df_basecase.at[0, 'H2_storage'] = storage = max_capacity - lab_H2_load
            df_basecase.at[0, 'DOH'] = storage / avg_h2_day  # initial storage in kg.
            continue
        elif i > size_basecase:
            continue
        else:
            df_basecase.at[i, 'electrical_load'] = electrical_load

            receiving_stock = df_basecase.at[i, 'buy_quantity'] * bottle_cap
            if receiving_stock > 0 and waiting_delivery:
                waiting_delivery = False  # Marking as received
            total_H2 = df_basecase.at[i - 1, 'H2_storage'] - lab_H2_load + receiving_stock
            H2_storage = clamp(total_H2, 0, max_capacity)

            if H2_storage <= 0:
                df_basecase.at[i, 'OOS'] = 1
            elif total_H2 > max_capacity:
                df_basecase.at[i, 'delivery_cut_off'] = total_H2 - max_capacity

            #         H2_storage = df_basecase.at[i - 1, 'H2_storage'] - lab_H2_load + receiving_stock
            avg_h2_week = df_basecase.at[i, 'h2_load_MA'] * 96 * 7
            avg_h2_day = df_basecase.at[i, 'h2_load_MA'] * 96
            DOH = H2_storage / avg_h2_day  # Multiplying by the number of lines in a day for the
            df_basecase.at[i, 'H2_storage'] = H2_storage
            df_basecase.at[i, 'DOH'] = DOH

            if H2_storage < max_capacity/2:  # Place an order
                if waiting_delivery and i < size_basecase - 1:
                    pass
                else:
                    try:
                        buy_bottles = np.ceil((max_capacity/2 + lead_time * avg_h2_day) / bottle_cap)
                        df_basecase.at[i, 'buy_order'] = 1
                        delivery_index = 35039 if i + lead_time * 96 > 35039 else i + lead_time * 96
                        df_basecase.at[delivery_index, 'buy_quantity'] = buy_bottles
                        waiting_delivery = True
                    except IndexError:
                        pass
            else:
                pass
    df_basecase['buy_price'] = df_basecase['buy_quantity'] * bottle_cap * hydrogen_price
    df_basecase['grid_cost'] = df_basecase['electrical_load'] * df_basecase['tariff'] * 0.001

    # The indicators that change during the first 3 years:
    df_yearly.at[year - 1, 'hydrogen_cost'] = sum(df_basecase['buy_price'])
    df_yearly.at[year-1, 'OOS'] = sum(df_basecase['OOS'])/96
    df_yearly.at[year-1, 'hydrogen_consumed'] = sum(df_basecase['hydrogen_consumed'])
    df_yearly.at[year - 1, 'delivery_cut_off'] = sum(df_basecase['delivery_cut_off'])
    year += 1

# #####################################################################################################################
# ############################################ Calculating over 25 years ##############################################
# #####################################################################################################################

for index, row in df_yearly.iterrows():
    if index > 2:
        df_yearly.at[index, 'hydrogen_cost'] = df_yearly.at[2, 'hydrogen_cost']
        df_yearly.at[index, 'OOS'] = df_yearly.at[2, 'OOS']
        df_yearly.at[index, 'hydrogen_consumed'] = df_yearly.at[2, 'hydrogen_consumed']
        df_yearly.at[index, 'delivery_cut_off'] = df_yearly.at[2, 'delivery_cut_off']
df_yearly['grid_electricity_consumed'] = sum(df_basecase['Load [Wh]'])
df_yearly['yearly_grid_cost'] = sum(df_basecase['grid_cost'])
df_yearly['operation_cost'] = df_yearly['yearly_grid_cost'] + df_yearly['hydrogen_cost'] + 1800  # + Bottle rental
df_yearly['levelized_cost'] = df_yearly['operation_cost']/((1+interest_rate)**df_yearly['year'])


# Testing stuff #######################################################################################################
print("No errors calculating.")

# Writing Excel #######################################################################################################
df_basecase.to_excel(r'C:\Users\gabri\Repositories\HydrogenMicroGrid\Results\Base_Case\basecase.xlsx', index=False,
                     sheet_name="basecase_calculations")
df_yearly.to_excel(r'C:\Users\gabri\Repositories\HydrogenMicroGrid\Results\Base_Case\basecase_yearly.xlsx', index=False,
                   sheet_name="yearly_calculations")

# Plotting things to test #############################################################################################
fig, ax = plt.subplots(1, 1, figsize=(10, 10))
storage = list(df_basecase['H2_storage'])
ax.plot(np.arange(len(storage)), storage)
plt.xlabel('Time step')
plt.ylabel('H2_storage')
plt.grid(True)
plt.show()
