import numpy as np # linear algebra
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm
from statsmodels.tsa.seasonal import STL
from fbprophet import Prophet
!pip install scikit-learn scipy
from sklearn.metrics import mean_absolute_error# data processing, CSV file I/O (e.g. pd.read_csv)