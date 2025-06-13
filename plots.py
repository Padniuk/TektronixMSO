import pandas as pd
from matplotlib import pyplot as plt

file_path = "data/0/0.csv"
data = pd.read_csv(file_path, skiprows=1)

plt.plot(data.iloc[:, 1], data.iloc[:, 2])
plt.plot(data.iloc[:, 1], data.iloc[:, 3])
plt.xlabel('Time, [us]')
plt.ylabel('Signal, [mV]')
plt.show()
