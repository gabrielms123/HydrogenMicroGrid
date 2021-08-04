import numpy as np
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt

DATA_PATH = Path.cwd()

# Solar ###############################################################################################################
df_full_irradiation = pd.read_csv(DATA_PATH / 'solar_avg.csv')
df_GHI = df_full_irradiation[['Day', 'Month', 'Hour end', 'GHI [Wh/m2]']]

solar_1D = np.array(df_GHI['GHI [Wh/m2]'])
number_quarters = 96
number_days = int(solar_1D.shape[0]/number_quarters)
solar_2D = solar_1D.reshape(number_days, number_quarters)

# plt.subplots(1, 1, squeeze=True)

# Electrical ##########################################################################################################

df_electrical_load = pd.read_csv(DATA_PATH / 'load_data.csv')
electrical_1D = np.array(df_electrical_load['Load [Wh]'])
electrical_2D = electrical_1D.reshape((number_days, number_quarters))

# Hydrogen ############################################################################################################

df_hydrogen_load = pd.read_csv(DATA_PATH / 'hydrogen_load_data.csv')
hydrogen_1D = np.array(df_hydrogen_load['H2_load [kg]'])
hydrogen_2D = hydrogen_1D.reshape((number_days, number_quarters))

fig_s = plt.imshow(solar_2D.T, cmap='hot')
# fig_e = plt.imshow(electrical_2D.T, cmap='hot')
# fig_h = plt.imshow(hydrogen_2D.T, cmap='hot')

plt.xlabel('Day of year')
plt.ylabel('Time of day')
plt.colorbar(orientation="horizontal", label="Global Horizontal Irradiation [Wh/m^2]")
plt.show()