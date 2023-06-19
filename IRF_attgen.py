# -*- coding: utf-8 -*-
"""
Created on Mon Jun 19 11:26:23 2023
simple code to save optimal att positions for irf measurements

@author: pranav.lanka
"""

from pandas import *

# Empty lists to store data
lamd = []
optpos = []

# Generate data inside a for loop
for i in range(1, 6):
    lamd.append(600 + i*5)
    optpos.append(i * 10)

# Create a DataFrame from the data
optpos_att = {'Lamda': lamd, 'OptPos': optpos}
df = DataFrame(optpos_att)

# Save DataFrame to an Excel file
df.to_excel('output.xlsx', index=False)
