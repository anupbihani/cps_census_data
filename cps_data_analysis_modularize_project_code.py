# -*- coding: utf-8 -*-
"""
Created on Sun Mar 27 12:00:47 2022

@author: anupb
"""
import requests
import json
import pandas as pd
import numpy as np
import plotly.express as px
from dash import Dash, html, dcc, dash_table
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate

# Collect the US CPS data based on native country of mother: 'PEMNTVTY' for the given month and year
def collectCPSData(year, month):
    try:
        url = f'https://api.census.gov/data/{year}/cps/basic/{month}?get=GTCBSA,PWSSWGT,PEMNTVTY'
        rawData = requests.get(url).text
        jsonData = json.loads(rawData)
    except:
        jsonData = []
    return jsonData

# Get country codes and name
def fetchDemographicCountryNames(year, month):
    url = f'https://api.census.gov/data/{year}/cps/basic/{month}/variables/PEMNTVTY.json'
    demoCountries = requests.get(url).text
    demoCountries = json.loads(demoCountries)['values']['item']
    demoCountriesList = []
    for key in demoCountries:
         demoCountriesList.append([key, demoCountries[key]])
    demoCountriesDf = pd.DataFrame(demoCountriesList, columns=['PEMNTVTY','COUNTRY'])
    demoCountriesDf = demoCountriesDf.astype({'PEMNTVTY': 'int32'})
    return demoCountriesDf

# Get metro city code and name
def fetchMetroCityNames(year, month):
    url = f'https://api.census.gov/data/{year}/cps/basic/{month}/variables/GTCBSA.json'
    metroCityData = requests.get(url).text
    metroCityData = json.loads(metroCityData)['values']['item']
    metroCityNames = []
    for key in metroCityData:
         metroCityNames.append([key, metroCityData[key]])
    metroCityDf = pd.DataFrame(metroCityNames, columns=['GTCBSA','CITY'])
    metroCityDf = metroCityDf.astype({'GTCBSA': 'int32'})
    return metroCityDf

# Get demographics highest level of school completed
def fetchHighestDegreeEducation():
    url = 'https://api.census.gov/data/2021/cps/basic/dec/variables/PEEDUCA'
    education = requests.get(url).text
    educationData = json.loads(education)['values']['item']
    educationDataNames = []
    for key in educationData:
         educationDataNames.append([key, educationData[key]])
    educationDf = pd.DataFrame(educationDataNames, columns=['PEEDUCA','EDUCATION_DEGREE'])
    educationDf = educationDf.astype({'PEEDUCA': 'int32'})
    return educationDf

#Read latitude longitude for Metropolitan cities from cbsa national text file.
def readMetroLatLong():
    geo_data = pd.read_csv('C:\\Users\\anupb\\Anup\\UNO_MS\\Tools For Data Analysis\\2021_Gaz_cbsa_national.txt', delimiter= "\t")
    geo_data = geo_data.rename(columns={'INTPTLONG                                                                                                             ':'INTPTLONG'})
    geo_data = geo_data[["GEOID", "INTPTLAT", "INTPTLONG"]]
    return geo_data

# Collect data with the CPS (Census Population Survey) API for any year range
# Also, get the metro city and demographics coutry names along with metro city lat long details
def collectCPSDataForMarEachYear(toYear, fromYear, month):
    cpsDataFrame = pd.DataFrame(columns = ['GTCBSA','PWSSWGT','PEMNTVTY'])
    finalDemoCountryDf = pd.DataFrame(columns = ['PEMNTVTY', 'COUNTRY'])
    finalMetroCityDf = pd.DataFrame(columns=['GTCBSA','CITY'])
    for year in range(toYear,fromYear):
        dataFrame = pd.DataFrame(collectCPSData(str(year), month)[1:], columns = ['GTCBSA','PWSSWGT','PEMNTVTY'])
        dataFrame['YEAR'] = str(year)
        cpsDataFrame = cpsDataFrame.append(dataFrame)
        #Fetch Demographic country for each year
        finalDemoCountryDf = finalDemoCountryDf.append(fetchDemographicCountryNames(year, month))
        #Fetch Metropolitan cities for each year
        finalMetroCityDf = finalMetroCityDf.append(fetchMetroCityNames(year, month))
    
    cpsDataFrame['PWSSWGT'] = cpsDataFrame['PWSSWGT'].astype(float)
    cpsDataFrame['PWSSWGT'] = cpsDataFrame['PWSSWGT'].apply(np.ceil)
    cpsDataFrame = cpsDataFrame.groupby(by=["GTCBSA","PEMNTVTY","YEAR"])['PWSSWGT'].sum().reset_index()
    cpsDataFrame = cpsDataFrame.astype({'PEMNTVTY': 'int32'})
    cpsDataFrame = cpsDataFrame.astype({'GTCBSA': 'int32'})
    cpsDataFrame = cpsDataFrame.astype({'YEAR': 'int32'})
    #cpsDataFrame = cpsDataFrame.astype({'PEEDUCA': 'int32'})
    cpsDataFrame = cpsDataFrame.drop(cpsDataFrame[cpsDataFrame.GTCBSA == 0].index)
    cpsDataFrame = cpsDataFrame.drop(cpsDataFrame[cpsDataFrame.PWSSWGT == 0].index)
    
    # Remove records with native country of mother as 'USA' (57)
    cpsDataFrame = cpsDataFrame.drop(cpsDataFrame[cpsDataFrame.PEMNTVTY == 57].index)
    
    finalDemoCountryDf = finalDemoCountryDf.drop_duplicates()
    finalMetroCityDf = finalMetroCityDf.drop_duplicates()
    #finalEducationDf = fetchHighestDegreeEducation()
    
    cpsDataFrame = pd.merge(cpsDataFrame, finalDemoCountryDf, on='PEMNTVTY', how='inner')
    cpsDataFrame = pd.merge(cpsDataFrame, finalMetroCityDf, on='GTCBSA', how='inner')
    #cpsDataFrame = pd.merge(cpsDataFrame, finalEducationDf, on='PEEDUCA', how='left')
    
    cpsDataFrame = cpsDataFrame.drop_duplicates()
    return cpsDataFrame

# This method will get the census data specified for the year range and month for those years.
def getCPSDemographicDataForUS(toYear, fromYear, month):
    try:
        cpsDemoUSDf = pd.read_csv('cps_demographic_data.csv')
    except:
        cpsDemoUSDf = collectCPSDataForMarEachYear(toYear, fromYear, month)
   
        # Add the lat/ long data into CPS dataframe
        geo_data = readMetroLatLong()
        cpsDemoUSDf = pd.merge(cpsDemoUSDf, geo_data, how='left', left_on = 'GTCBSA', right_on = 'GEOID') 
        
        # Drop NaN values from the dataframe; makes it easy to render the remaining data on the maps
        cpsDemoUSDf = cpsDemoUSDf.dropna()
        
        # Sort the data by Year and Country columns so that we will have all the data sorted from 2004 to 2019; ascending by countries.
        cpsDemoUSDf = cpsDemoUSDf.sort_values(by=['YEAR','PWSSWGT'], ascending=[True, False])
        cpsDemoUSDf.columns = ['METRO_CITY_CODE', 'NATIVE_MOTHER_COUNTRY_CODE', 'YEAR', 'IMMIGRANT_COUNT', 'COUNTRY', 'METRO_CITY', 'GEOID', 'METRO_CITY_LAT', 'METRO_CITY_LONG']
        cpsDemoUSDf.to_csv('cps_demographic_data.csv', index=False)
        
    print("cpsDemoUSDf: \n", cpsDemoUSDf)
    return cpsDemoUSDf

# Find out the top demographic countries by immigration count number per year
def getTopDemographicCountryByCount():
    topDemoCountryDf = getCPSDemographicDataForUS(2004, 2020, 'dec')
    topDemoCountryDf = topDemoCountryDf.groupby(by=["YEAR","COUNTRY"])['IMMIGRANT_COUNT'].sum().reset_index()
    print('topDemoCountryDf: \n',topDemoCountryDf)
    return topDemoCountryDf


cpsDemographicDataDf = getCPSDemographicDataForUS(2004, 2020, 'dec')
countryNameList = cpsDemographicDataDf['COUNTRY'].drop_duplicates()
yearList = cpsDemographicDataDf['YEAR'].drop_duplicates()

topDemoCountryDf = getTopDemographicCountryByCount()
tempTopDemoCountryDf = topDemoCountryDf[topDemoCountryDf['YEAR'] == 2015]
tempTopDemoCountryDf = tempTopDemoCountryDf.sort_values(by=['IMMIGRANT_COUNT'], ascending=[False])
tempTopDemoCountryDf = tempTopDemoCountryDf.head(10)

app = Dash(__name__)
fig1 = px.scatter_geo(cpsDemographicDataDf, lat='METRO_CITY_LAT', lon='METRO_CITY_LONG', color='COUNTRY', hover_name="METRO_CITY",
               animation_frame = 'YEAR', size="IMMIGRANT_COUNT", size_max=30,
               scope="usa", featureidkey='properties.GEOID', title="Canada Immigrants on USA map")

colors = {
    'background': '#111111',
    'text': '#7FDBFF'
}
fig1.update_layout(
    plot_bgcolor=colors['background'],
    paper_bgcolor=colors['background'],
    font_color=colors['text'],
    height=500, width=740,
    transition= {'duration':30000 }
)

fig2 = px.bar(tempTopDemoCountryDf, x="COUNTRY", y="IMMIGRANT_COUNT", color="COUNTRY", 
              labels={'IMMIGRANT_COUNT':'Immigrant Count'}, title="Top 10 Immigrant Countries for the year 2015")

app.layout = html.Div(className='row', children=[
    html.H1(children='USA Demographic changes from 2004 to 2019', style={'textAlign': 'center','color': colors['text']}), 
    dcc.Store(id='memory-output'),
    html.Div([
        dcc.Dropdown(id='countryDropdown', options = countryNameList, multi=True, style={'display': 'inline-block','width': 740}),
        html.Label("Select Year", style={'margin-left':'20px', 'color': colors['text']}),
        dcc.Dropdown(id='yearDropdown', options = yearList, value=2019, style={'margin-right':'10px','margin-left':'10px','display': 'inline-block','width': 200}),
        html.Label("# of top countries", style={'color': colors['text'],'margin-left':'10px', 'margin-right':'10px', 'margin-bottom':'15px'}),
        dcc.Input(id='num', type='number', debounce=True, max=20, value=10, step=1, style={'margin-left':'10px','margin-bottom':'15px','display': 'inline-block','width': 150})
    ]),
    
    html.Div([
                dcc.Graph(id="cps-geo-plot", figure=fig1,  style={'display': 'inline-block', 'margin-right':'10px'}),
                dcc.Graph(id="cps-bar-plot", figure=fig2,  style={'display': 'inline-block', 'margin-left':'10px'})
          ]),
    
    dash_table.DataTable(
            id='memory-table',
            columns=[{'name': i, 'id': i} for i in cpsDemographicDataDf.columns]
        ),
    
])

@app.callback(Output('memory-output', 'data'),
              Input('countryDropdown', 'value'), 
              Input('yearDropdown', 'value'))
def filter_countries(countries_selected, year_selected):
    if not countries_selected:
        # Return all the rows on initial load/no country selected.
        return cpsDemographicDataDf.to_dict('records')

    if year_selected is None:
        filtered = cpsDemographicDataDf.query('COUNTRY in @countries_selected')
    else:
        year_selected = int(year_selected)
        filtered = cpsDemographicDataDf.query('COUNTRY in @countries_selected & YEAR == @year_selected')

    return filtered.to_dict('records')


@app.callback(Output('memory-table', 'data'),
              Input('memory-output', 'data'))
def on_data_set_table(data):
    if data is None:
        raise PreventUpdate

    return data

@app.callback(Output('cps-geo-plot', 'figure'),
              Input('countryDropdown', 'value'),
              Input('yearDropdown', 'value'))
def updateMap(countries_selected, year_selected):
    tempCpsDemodf = cpsDemographicDataDf
    if not countries_selected:
        joined_string = "All country"
    if year_selected is None:
        tempCpsDemodf = cpsDemographicDataDf.query('COUNTRY in @countries_selected')
    else:         
        tempCpsDemodf = cpsDemographicDataDf.query('COUNTRY in @countries_selected & YEAR == @year_selected')
        joined_string = ",".join(countries_selected)
        
    fig1 = px.scatter_geo(tempCpsDemodf, lat='METRO_CITY_LAT', lon='METRO_CITY_LONG', color="COUNTRY", hover_name="METRO_CITY",
               animation_frame = 'YEAR', size="IMMIGRANT_COUNT", scope="usa", size_max=30, title=f"{joined_string} immigrants on USA map")
     
    fig1.update_layout(
        plot_bgcolor=colors['background'],
        paper_bgcolor=colors['background'],
        font_color=colors['text'],
        height=500, width=740,
        transition= {'duration':30000 }
    )
    return fig1

@app.callback(Output('cps-bar-plot', 'figure'),
              Input('yearDropdown', 'value'),
              Input('num', 'value'),
             )
def updateBarPlot(yearDropDownVal, numberCount):
    tempTopDemoCountryDf = topDemoCountryDf
    if yearDropDownVal is None:
        yearDropDownVal = '2004 to 2019'
        tempTopDemoCountryDf = tempTopDemoCountryDf.COUNTRY.unique()
        tempTopDemoCountryDf = tempTopDemoCountryDf.sort_values(by=['IMMIGRANT_COUNT'], ascending=[False])
        tempTopDemoCountryDf = tempTopDemoCountryDf.head(numberCount)
    else:
        tempTopDemoCountryDf = topDemoCountryDf[topDemoCountryDf['YEAR'] == yearDropDownVal]
        tempTopDemoCountryDf = tempTopDemoCountryDf.sort_values(by=['IMMIGRANT_COUNT'], ascending=[False])
        tempTopDemoCountryDf = tempTopDemoCountryDf.head(numberCount)
    
    fig2 = px.bar(tempTopDemoCountryDf, x="COUNTRY", y="IMMIGRANT_COUNT", color="COUNTRY",
                  labels={'IMMIGRANT_COUNT':'Immigrant Count'}, title=f"Top {numberCount} Immigrant Countries for the year {yearDropDownVal}")
        
    fig2.update_layout(
        plot_bgcolor=colors['background'],
        paper_bgcolor=colors['background'],
        font_color=colors['text'],
        height=500, width=740
    )
    return fig2

app.css.append_css({
    'external_url': 'https://codepen.io/chriddyp/pen/bWLwgP.css'
})

if __name__ == '__main__':
    app.run_server(debug=False)