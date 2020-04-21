from flask import render_template,flash,url_for,request,redirect
from covid_map import app
import requests
import pandas as pd

from datetime import datetime
import plotly
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import json
#from apscheduler.schedulers.blocking import BlockingScheduler
#ched = BlockingScheduler()


df_codes = pd.read_csv('countries.csv')

@app.route('/')
def home():
	return render_template('home.html')

@app.route('/reset')
def timed_job():
	all_res = country_api([])
	get_res_df(all_res)
	return "reset complete"
@app.route('/insight',methods=['GET', 'POST'])
def insight():
	map_plot = generate_plot()
	return render_template('layouts.html', title = 'Insight', plot = map_plot)

def generate_plot():
	all_df = pd.read_csv('all_countries_pandamic.csv')
	data = [go.Scattergeo(
        lon = all_df['long'],
        lat = all_df['lat'],
        opacity = 0.7,
        text = all_df['text'],
        marker_color = "#FF0000")]

	graphJSON = json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder)

	return graphJSON

def get_res_df(res):
    data = dict()
    lst_country = []
    lst_total_cases = []
    lst_total_deaths = []
    lst_total_recovered = []
    lst_lat = []
    lst_lon = []
    text_lst = []

    for i in res:
        if(i['ok']):
            lst_country.append(i['country']['country_name'])
            lst_total_cases.append(i['country']['total_cases'])
            lst_total_deaths.append(i['country']['total_deaths'])
            lst_total_recovered.append(i['country']['total_recovered'])
            lst_lat.append(df_codes[df_codes["name"]==i['country']['country_name']]['latitude'].values[0])
            lst_lon.append(df_codes[df_codes["name"]==i['country']['country_name']]['longitude'].values[0])
        
    data['country_name'] = lst_country 
    data['total_cases'] = lst_total_cases
    data['total_deaths'] = lst_total_deaths
    data['total_recovered'] = lst_total_recovered
    data['lat'] = lst_lat
    data['long'] = lst_lon

    df_count = pd.DataFrame(data)
    for _,value in df_count.iterrows():
        text_lst.append(f"Country: {value['country_name']}\n Total Case:{value['total_cases']}\n Total Death:{value['total_deaths']}\n Total Recovered:{value['total_recovered']}")
    df_count['text'] = text_lst
        
    df_count.to_csv('all_countries_pandamic.csv')
    return []

def country_api(country_lst):
    covid_res = []
    if len(country_lst)<1:
        country_lst = df_codes['name'].values
    for country in country_lst:
        url = "https://coronavirus-info.p.rapidapi.com/country"
        if len(country)>4:
            country_name = country.title()
        else:
            country_name = country.upper()
        querystring = {"name": country_name}
        headers = {
                'x-rapidapi-host': "coronavirus-info.p.rapidapi.com",
                'x-rapidapi-key': "add you rapid-api key-here"

        response = requests.request("GET", url, headers=headers, params=querystring)
        res = json.loads(response.text)
        covid_res.append(res)

    return covid_res
