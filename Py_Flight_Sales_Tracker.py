
# coding: utf-8

# In[1]:


# Make notebook full width
from IPython.core.display import display, HTML
display(HTML("<style>.container { width:100% !important; }</style>"))


# File Name: Py_Flight_Sales_Tracker  
# Author: Anjukan Kathirgamanathan  
# Date: 11/09/2018  
# This is a python script to scrape the web for the cheapest flight on a route and save flight details to a database tracking sales and the price of the flight over time

# ## Load Libraries

# In[2]:


import schedule

import requests

from lxml import html

from bs4 import BeautifulSoup

from collections import OrderedDict

import argparse

import time

import glob
import os
import json

import csv

import pandas as pd
import numpy as np

import matplotlib.pyplot as plt

import plotly as py
import plotly.graph_objs as go
from plotly.offline import download_plotlyjs, init_notebook_mode, plot, iplot

py.tools.set_credentials_file(username='akat022', api_key='Pdc1fGtg6IOWTOF1uLvE')

py.offline.init_notebook_mode()
init_notebook_mode(connected=True)

import cufflinks as cf

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# In[3]:


# Function that takes in the source location, destination (both 3 letter IATA codes), and the date (in 'YYYY-MM-DD' format) and will scrape flights from Google Flights. Returns a sorted list of flights by price.
def google(source,destination,date):
    # URL to scrape from taking in user input
    url = "https://www.google.com/flights#flt={0}.{1}.{2};c:EUR;e:1;sd:1;t:f;tt:o".format(source,destination,date)
    dcap = dict(DesiredCapabilities.PHANTOMJS)
    dcap["phantomjs.page.settings.userAgent"] = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.98 Safari/537.36 OPR/44.0.2510.857")
    # Use headless chrome as the webdriver
    driver = webdriver.Chrome(desired_capabilities=dcap, service_args=['--ignore-ssl-errors=true','--ssl-protocol=any'])
    driver.get(url)
    print(url)
    # Wait for page to load
    wait = WebDriverWait(driver, 10)
    wait
    # Save a screenshot of the page being scraped
    driver.save_screenshot(r'image.png')
    s = BeautifulSoup(driver.page_source, "lxml")
    pretty_s = s.prettify()
    #print(pretty_s)
    driver.close()
    # Find the html of interest with the following tag
    best_price_tags = s.findAll('div', 'gws-flights-results__itinerary-card-summary gws-flights-results__result-item-summary gws-flights__flex-box')
    best_prices = []
    for tag in best_price_tags:
        best_prices.append(tag.text)
        #print(best_prices)

    s2 = "From "
    s3 = "Trip duration: "
    s4 = "Departure time: "
    s5 = "Arrival time: "
    s6 = "flight by and"

    flight_info  = OrderedDict() 
    lists=[]
    
    # Create a list including the following details for each flight
    for x in best_prices:
        price = x[x.index(s2) + len(s2) + 1:].split('.')[0].replace(',','')
        duration = x[x.index(s3) + len(s3):].split('.')[0]
        dep_time = x[x.index(s4) + len(s4):].split('.')[0]
        arr_time = x[x.index(s5) + len(s5):].split('.')[0]
        airline = x[x.index(s6) + len(s6):].split('.')[0]

        flight_info={'ticket price':price,
                'departure':source,
                'arrival':destination,
                'flight duration':duration,
                'airline':airline,
                 'departure date': date,
                'departure time':dep_time,
                'arrival time':arr_time,
                'lookup date': pd.to_datetime('today').strftime("%d/%m/%Y") 
                }
        lists.append(flight_info)
    
    sortedlist = sorted(lists, key=lambda k: float(k['ticket price']),reverse=False)

    labels = ['ticket price','departure','arrival','flight duration','airline','departure date','departure time','arrival time','lookup date']
    
    # Create a dataframe from the list
    df = pd.DataFrame.from_records(sortedlist, columns=labels)
    
    # Write the scraped data to the csv database
    # Extract data from existing records to ensure that they are not overwritten
    df_existing = pd.read_csv("flight_data.csv", sep=',')

    df_new = pd.concat([df_existing, df], ignore_index=True)

    #print(df_new)

    # As a safety check, remove any rows with NaN
    df_new.dropna(axis=0)

    # Save data to csv
    df_new.to_csv('flight_data.csv', sep=',', header=True, index=False)
    
    return df


# In[4]:


schedule.every().day.at("12:00").do(google,'DUB','SGN','2018-12-16')
schedule.every().day.at("12:02").do(google,'DUB','SGN','2018-12-15')
schedule.every().day.at("12:04").do(google,'CMB','DUB','2019-01-18')
schedule.every().day.at("12:06").do(google,'CMB','DUB','2019-01-19')
schedule.every().day.at("12:08").do(google,'CMB','DUB','2019-01-20')

while True:
    schedule.run_pending()
    time.sleep(60) # wait one minute


# ## Plot Evolution

# In[ ]:


# Plot the prices as they evolve over time

# Load the data
df_plot = pd.read_csv("flight_data.csv", sep=',')

# Co-erce date columns to be in a consistent format
df_plot['departure date'] = pd.to_datetime(df_plot['departure date']).dt.strftime('%d/%m/%Y')
df_plot['departure time'] = pd.to_datetime(df_plot['departure time']).dt.strftime('%H:%M')
df_plot['lookup date'] = pd.to_datetime(df_plot['lookup date']).dt.strftime('%d/%m/%Y')

# Need a new column to identify each flight (in the absence of flight numbers)
df_plot['flight identifier'] = df_plot['airline'] + '*' + df_plot['departure date'] + '*' + df_plot['departure time']

df_plot['flight routing'] = df_plot['departure'] + '-' + df_plot['arrival']

# Drop the columns that are now redundant
df_plot.drop(['departure', 'arrival', 'airline', 'arrival time', 'departure time', 'flight duration', 'departure date'], axis=1, inplace=True)

# Change ticket pricec column to float
df_plot['ticket price'] = pd.to_numeric(df_plot['ticket price']).astype(np.int64)

# Remove any excessive priced options
df_plot = df_plot[df_plot['ticket price'] < 1000]

# Set index
df_plot.set_index('lookup date')

# Look at DUB-SGN only for now
df_plot = df_plot.loc[df_plot['flight routing'] == 'CMB-DUB']

#print(df_plot)

df_plot2 = df_plot.pivot_table(index = 'lookup date', columns='flight identifier', values='ticket price')

#print(df_plot2)

df_plot2.plot(kind = 'line', figsize=(12,12))
# Put a legend to the right of the current axis
ax = plt.subplot(111)
ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
plt.title('Evolution of Flights Prices between CMB and DUB')
plt.ylabel('Price (EUROS)')
plt.show()


# In[22]:


# Produce a plotly plot
cf.set_config_file(offline=False, world_readable=True, theme='ggplot')

fig = df_plot2.iplot(kind='scatter', asFigure=True)
py.plotly.plot(fig)

