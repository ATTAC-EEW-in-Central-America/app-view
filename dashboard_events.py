#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (C) by ETHZ/SED

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

Author: Billy Burgoa Rosso (billyburgoa@gmail.com)
"""
import json
import sqlite3
import pandas as pd
import math
import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.express as px
import plotly.graph_objs as go
import numpy as np
from os import path

# Read the JSON file and load the database path
def load_db_path():
    script_dir = path.dirname(path.abspath(__file__))
    config_path = path.join(script_dir, 'dashboard_events.json')
    with open(config_path) as config_file:
        config = json.load(config_file)
    return config['database_path']

# Define the provided functions
def distanceEpiToPoint(epiLat, epiLon, lat, lon):
    if pd.isna(lat) or pd.isna(lon):
        return None
    rEpiLat = math.radians(epiLat)
    rEpiLon = math.radians(epiLon)
    rLat = math.radians(lat)
    rLon = math.radians(lon)
    
    distance = math.acos(math.sin(rEpiLat) * math.sin(rLat) + math.cos(rEpiLat) * math.cos(rLat) * math.cos(rEpiLon - rLon)) * 6371
    
    return distance

def distanceHypoToPoint(epiLat, epiLon, depth, lat, lon):
    if pd.isna(lat) or pd.isna(lon):
        return None
    rEpiLat = math.radians(epiLat)
    rEpiLon = math.radians(epiLon)
    rLat = math.radians(lat)
    rLon = math.radians(lon)
    
    distance = math.acos(math.sin(rEpiLat) * math.sin(rLat) + math.cos(rEpiLat) * math.cos(rLat) * math.cos(rEpiLon - rLon)) * 6371
    
    hypoDist = math.sqrt(distance * distance + depth * depth)
    
    return hypoDist

def ipe_allen2012_hyp(epiDistance, magnitude, depth):
    a = 2.085
    b = 1.428
    c = -1.402
    d = 0.078   
    s = 1.0
    m1 = -0.209  
    m2 = 2.042
        
    if depth < 0:
        return -1
    
    hypoDistance = math.sqrt(math.pow(epiDistance, 2) + math.pow(depth, 2))
        
    rm = m1 + m2 * math.exp(magnitude - 5)
        
    if hypoDistance <= 50:
        I = a + b * magnitude + c * math.log(math.sqrt(math.pow(hypoDistance, 2) + math.pow(rm, 2))) + s
    else:
        I = a + b * magnitude + c * math.log(math.sqrt(math.pow(hypoDistance, 2) + math.pow(rm, 2))) + d * math.log(hypoDistance / 50) + s
    
    intensity = round(I)
    
    if intensity > 12:
        return 12
    elif intensity < 0:
        return 0
    else:
        return I

def ipe_allen2012_hyp_sigma(epiDistance, depth):
    s1 = 0.82
    s2 = 0.37
    s3 = 22.9
    hypoDistance = math.sqrt(math.pow(epiDistance, 2) + math.pow(depth, 2))
        
    sigma = s1 + s2 / (1 + math.pow(hypoDistance / s3, 2))
        
    return sigma

def intToColorDescription(intVal):
    if intVal > 12 or intVal < 0:
        intVal = -1
    colorDict = {
        -1: "--",           # Invalid
        0: "I. Not Felt",   # #D3D3D3
        1: "II. Very Weak", # #BFCCFF
        2: "III. Weak",     # #9999FF
        3: "IV. Light",     # #80FFFF
        4: "V. Moderate",   # #7DF894
        5: "VI. Strong",    # #FFFF00
        6: "VII. Very Strong",# #FFC800
        7: "VIII. Severe",  # #FF9100
        8: "IX. Violent",   # #FF0000
        9: "X. Extreme",    # #C80000
        10: "XI. Extreme",  # #800000
        11: "XII. Extreme", # #000000
        12: "XII. Extreme"  # #000000
    }
    
    color = {
        -1: "#FFFFFF",
        0: "#D3D3D3",
        1: "#BFCCFF",
        2: "#9999FF",
        3: "#80FFFF",
        4: "#7DF894",
        5: "#FFFF00",
        6: "#FFC800",
        7: "#FF9100",
        8: "#FF0000",
        9: "#C80000",
        10: "#800000",
        11: "#000000",
        12: "#000000"
    }

    return f"{colorDict[intVal]};{color[intVal]}"

# Helper function to fetch data and process for resume cards
def get_resume_data(eventid):
    db_path = load_db_path()  # Load the database path from JSON file
    conn = sqlite3.connect(db_path)

    # Fetching data
    query_eventinfo = f"SELECT magnitude, origintime, depth, description FROM eventinfo WHERE eventid='{eventid}' ORDER BY updatetime DESC LIMIT 1"
    df_eventinfo = pd.read_sql(query_eventinfo, conn)

    query_intensity = f"SELECT intensity FROM intensityreports WHERE eventid='{eventid}'"
    df_intensity = pd.read_sql(query_intensity, conn)

    query_eventnotif = f"SELECT userid, osversion FROM eventnotif WHERE eventid='{eventid}'"
    df_eventnotif = pd.read_sql(query_eventnotif, conn)
    
    conn.close()

    # Event information
    magnitude = round(df_eventinfo['magnitude'].values[0], 1)
    origintime = df_eventinfo['origintime'].values[0]
    depth = int(df_eventinfo['depth'].values[0])
    description = df_eventinfo['description'].values[0]

    # Max intensity (95th percentile)
    percentil_95 = df_intensity['intensity'].quantile(0.95)
    max_intensity = df_intensity[df_intensity['intensity'] <= percentil_95]['intensity'].max()

    # Number of users (counting unique userid)
    unique_users = df_eventnotif.drop_duplicates(subset='userid')
    total_users = len(unique_users)
    android_users = len(unique_users[unique_users['osversion'].str.lower() == 'android'])
    ios_users = len(unique_users[unique_users['osversion'].str.lower() == 'ios'])
    intensity_report_users = len(df_intensity[df_intensity['intensity'] <= percentil_95]['intensity'])

    return magnitude, origintime, depth, description, max_intensity, total_users, android_users, ios_users, intensity_report_users

# Function to get data for dashboards
def get_data(eventid):
    db_path = load_db_path()  # Load the database path from JSON file
    conn = sqlite3.connect(db_path)
    
    # Get reported intensity data
    query_intensity = f"SELECT * FROM intensityreports WHERE eventid='{eventid}'"
    df_intensity = pd.read_sql(query_intensity, conn)
    
    # Get event notification data containing swavearrival
    query_eventnotif = f"SELECT * FROM eventnotif WHERE eventid='{eventid}'"
    df_eventnotif = pd.read_sql(query_eventnotif, conn)
    
    # Get epicenter data
    query_eventinfo = f"SELECT * FROM eventinfo WHERE eventid='{eventid}' ORDER BY updatetime DESC LIMIT 1"
    df_eventinfo = pd.read_sql(query_eventinfo, conn)
    
    conn.close()
    return df_intensity, df_eventnotif, df_eventinfo


# Layout of the dashboard
layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1(id="header-title", className="text-center mb-4"),
        ])
    ]),
    dbc.Row([  # Resume cards row
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(id="event-card-header"),  # Dynamic translation
                dbc.CardBody([
                    html.H5(id="event-description", className="card-title"),
                    html.P(id="event-details")
                ])
            ])
        ], width=4),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(id="max-intensity-card-header"),  # Dynamic translation
                dbc.CardBody([
                    html.H5(id="max-intensity", className="card-title"),
                    html.P(id="intensity-report")
                ], id="max-intensity-card")  # Set the id for the card body
            ])
        ], width=4),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(id="notified-users-card-header"),  # Dynamic translation
                dbc.CardBody([
                    html.H5(id="total-users", className="card-title"),
                    html.P(id="users-report")
                ], style={"background-color": "#F8F9FA", "text-align": "center"})
            ])
        ], width=4)
    ], className="mb-4"),
    dbc.Row([
        dbc.Col([
            dcc.Input(id='input-eventid', type='text', placeholder='Enter eventid', debounce=True),
        ], width=8),
        dbc.Col([
            dcc.Dropdown(
                id='language-dropdown',
                options=[
                    {'label': 'English', 'value': 'en'},
                    {'label': 'Español', 'value': 'es'}
                ],
                value='en',  # Default language
                clearable=False,
                className="mb-2",
            )
        ], width=4),
    ], justify="center"),
    dbc.Row([
        dbc.Col([
            dcc.Loading(id="loading-map-intensities", type="circle", children=[
                dcc.Graph(id='map-intensities')
            ])
        ], width=6),
        dbc.Col([
            dcc.Loading(id="loading-graph-intensity", type="circle", children=[
                dcc.Graph(id='graph-intensity')
            ])
        ], width=6),
    ]),
    dbc.Row([
        dbc.Col([
            dcc.Dropdown(id='dropdown-updateno-1', multi=False, placeholder="Select Updateno (Intensity/Swavearrival)"),
            dcc.Dropdown(id='dropdown-osversion-1', multi=False, placeholder="Select OS Version (Intensity/Swavearrival)"),
            dcc.Loading(id="loading-graph-delay", type="circle", children=[
                dcc.Graph(id='graph-delay')
            ])
        ], width=6),
        dbc.Col([
            dcc.Loading(id="loading-graph-alert", type="circle", children=[
                dcc.Graph(id='graph-alert')
            ])
        ], width=6),
    ]),
    dbc.Row([
        dbc.Col([
            dcc.Dropdown(id='dropdown-updateno-2', multi=False, style={'width': '100%', 'font-size': '12px'}),
            dcc.Loading(id="loading-map-swavearrival", type="circle", children=[
                dcc.Graph(id='map-swavearrival')
            ])
        ], width=6),
        dbc.Col([
            dcc.Loading(id="loading-graph-swavearrival", type="circle", children=[
                dcc.Graph(id='graph-swavearrival')
            ])
        ], width=6),
    ])
], fluid=True)

def register_callbacks(app):
    # Callback to update the dropdown of `updateno` and `osversion` for the first dashboard
    @app.callback(
        [Output('dropdown-updateno-1', 'options'),
         Output('dropdown-updateno-1', 'value')],
        [Input('input-eventid', 'value')]
    )
    def update_dropdown_1(eventid):
        if eventid:
            _, df_eventnotif, _ = get_data(eventid)
            if df_eventnotif.empty:
                return [], None
    
            # Count lines for updateno = 0
            total_updateno_0 = df_eventnotif[df_eventnotif['updateno'] == 0].shape[0]
            
            # Filter updatenos that meet the condition of having at least 1/3 of the lines of updateno = 0
            valid_updatenos = df_eventnotif.groupby('updateno').filter(lambda x: x.shape[0] >= total_updateno_0 / 3)['updateno'].unique()
    
            # Create options for the dropdown, including the "all" option
            updateno_options = [{'label': 'All', 'value': 'all'}] + [{'label': f'Updateno {updateno}', 'value': updateno} for updateno in sorted(valid_updatenos)]
            
            return updateno_options, 'all'
        
        return [], None
    
    @app.callback(
        [Output('dropdown-osversion-1', 'options'),
         Output('dropdown-osversion-1', 'value')],
        [Input('dropdown-updateno-1', 'value'),
         Input('input-eventid', 'value')]
    )
    def update_osversion_1(updateno, eventid):
        if eventid and updateno is not None:
            _, df_eventnotif, _ = get_data(eventid)
            if df_eventnotif.empty:
                return [], None
            
            osversion_options = [{'label': 'All', 'value': 'all'}, {'label': 'Android', 'value': 'android'}, {'label': 'iOS', 'value': 'ios'}]
            return osversion_options, 'all'
        
        return [], None
    
    # Callback to update the dropdown of `updateno` for the second dashboard
    @app.callback(
        [Output('dropdown-updateno-2', 'options'),
         Output('dropdown-updateno-2', 'value')],
        [Input('input-eventid', 'value')]
    )
    def update_dropdown_2(eventid):
        if eventid:
            _, df_eventnotif, _ = get_data(eventid)
            if df_eventnotif.empty:
                return [], None
    
            # Count lines for updateno = 0
            total_updateno_0 = df_eventnotif[df_eventnotif['updateno'] == 0].shape[0]
            
            # Filter updatenos that meet the condition of having at least 1/3 of the lines of updateno = 0
            valid_updatenos = df_eventnotif.groupby('updateno').filter(lambda x: x.shape[0] >= total_updateno_0 / 3)['updateno'].unique()
    
            # Create options for the dropdown
            updateno_options = [{'label': f'Updateno {updateno}', 'value': updateno} for updateno in sorted(valid_updatenos)]
            
            return updateno_options, 0
        
        return [], None
    
    # Callback to update the first dashboard for intensities, swavearrival, and the delay and alert histogram
    @app.callback(
        [Output('map-intensities', 'figure'),
         Output('graph-intensity', 'figure'),
         Output('graph-delay', 'figure'),
         Output('graph-alert', 'figure')],
        [Input('input-eventid', 'value'),
         Input('dropdown-updateno-1', 'value'),
         Input('dropdown-osversion-1', 'value'),
         Input('language-dropdown', 'value')]
    )
    def update_dashboard_1(eventid, updateno, osversion, language):
        if eventid:
            df_intensity, df_eventnotif, df_eventinfo = get_data(eventid)
            
            if df_eventinfo.empty:
                return {}, {}, {}, {}
            
            magnitude = df_eventinfo.iloc[0]['magnitude']
            depth = df_eventinfo.iloc[0]['depth']
            epiLat = df_eventinfo.iloc[0]['latitude']
            epiLon = df_eventinfo.iloc[0]['longitude']
            
            # --- Intensity Analysis ---
            
            # Filter intensities by the 95th percentile
            if not df_intensity.empty:
                percentil_95 = df_intensity['intensity'].quantile(0.95)
                df_intensity_filtered = df_intensity[df_intensity['intensity'] <= percentil_95]
                
                # Translate intensity labels based on selected language
                if language == 'es':
                    intensity_map = {
                        'I. Not Felt': 'I. No Sentido',
                        'II. Very Weak': 'II. Muy Débil',
                        'III. Weak': 'III. Débil',
                        'IV. Light': 'IV. Leve',
                        'V. Moderate': 'V. Moderada',
                        'VI. Strong': 'VI. Fuerte',
                        'VII. Very Strong': 'VII. Muy Fuerte',
                        'VIII. Severe': 'VIII. Severo',
                        'IX. Violent': 'IX. Violento',
                        'X. Extreme': 'X. Extremo',
                        'XI. Extreme': 'XI. Extremo',
                        'XII. Extreme': 'XII. Extremo',
                    }
                else:
                    intensity_map = {
                        'I. Not Felt': 'I. Not Felt',
                        'II. Very Weak': 'II. Very Weak',
                        'III. Weak': 'III. Weak',
                        'IV. Light': 'IV. Light',
                        'V. Moderate': 'V. Moderate',
                        'VI. Strong': 'VI. Strong',
                        'VII. Very Strong': 'VII. Very Strong',
                        'VIII. Severe': 'VIII. Severe',
                        'IX. Violent': 'IX. Violent',
                        'X. Extreme': 'X. Extreme',
                        'XI. Extreme': 'XI. Extreme',
                        'XII. Extreme': 'XII. Extreme',
                    }
    
                # Map the intensity values for the legend
                df_intensity_filtered['EMS-98'] = df_intensity_filtered['intensity'].apply(
                    lambda x: intensity_map[intToColorDescription(x).split(";")[0]]
                )
                df_intensity_filtered['color'] = df_intensity_filtered['intensity'].apply(
                    lambda x: intToColorDescription(x).split(";")[1]
                )
    
                # Intensity map
                fig_map_intensities = px.scatter_mapbox(
                    df_intensity_filtered, lat="lat", lon="lon", color="EMS-98",
                    color_discrete_map={intensity_map[intToColorDescription(k).split(";")[0]]: intToColorDescription(k).split(";")[1] for k in range(13)},
                    size_max=15, zoom=5, mapbox_style="carto-positron"
                )
                
                # Add a black circle for the epicenter
                epiMap = go.Scattermapbox(
                    lat=[epiLat],
                    lon=[epiLon],
                    mode='markers',
                    marker=go.scattermapbox.Marker(
                        size=20,
                        color='black',
                        symbol='circle'
                    ),
                    text="Mag: " + str(magnitude),
                    name="Epicenter"
                )
                
                fig_map_intensities.add_trace(epiMap)
                
                fig_map_intensities.update_layout(
                    mapbox=dict(
                        center=dict(lat=epiLat, lon=epiLon),
                        zoom=5
                    ),
                    title="Mapa de Intensidades" if language == 'es' else "Intensity Map"
                )
    
                # Intensity vs Hypocentral Distance Graph
                distances = []
                reported_intensities = []
                colors = []
    
                for index, row in df_intensity_filtered.iterrows():
                    if pd.notnull(row['lat']) and pd.notnull(row['lon']):
                        epi_distance = distanceEpiToPoint(epiLat, epiLon, row['lat'], row['lon'])
                        hypo_distance = distanceHypoToPoint(epiLat, epiLon, depth, row['lat'], row['lon'])
                        
                        distances.append(hypo_distance)
                        reported_intensities.append(row['intensity'])
                        colors.append(row['color'])
                
                # Generate theoretical distances for Allen
                allenDist = [x for x in range(0, 500, 10)]
                allen_intensities = [ipe_allen2012_hyp(d, magnitude, depth) for d in allenDist]
                sigma_allen = [ipe_allen2012_hyp_sigma(d, depth) for d in allenDist]
    
                fig_intensity = go.Figure()
    
                # Central line (Theoretical Intensity)
                fig_intensity.add_trace(go.Scatter(
                    x=allenDist,
                    y=allen_intensities,
                    mode='lines',
                    name="Allen's IPE 2012 (MMI)",
                    line=dict(color='black')
                ))
    
                # Band of +σ and -σ
                fig_intensity.add_trace(go.Scatter(
                    x=allenDist,
                    y=[i + s for i, s in zip(allen_intensities, sigma_allen)],
                    mode='lines',
                    name='+σ (SD) (MMI)',
                    line=dict(color='gray', dash='dash')
                ))
    
                fig_intensity.add_trace(go.Scatter(
                    x=allenDist,
                    y=[i - s for i, s in zip(allen_intensities, sigma_allen)],
                    mode='lines',
                    name='-σ (SD) (MMI)',
                    line=dict(color='gray', dash='dash')
                ))
    
                # Reported intensity points with colors
                fig_intensity.add_trace(go.Scatter(
                    x=distances,
                    y=reported_intensities,
                    mode='markers',
                    name='Reported Intensity',
                    marker=dict(size=8, color=colors)
                ))
    
                fig_intensity.update_layout(
                    xaxis=dict(title='Hypocentral Distance [km]', type='log'),
                    yaxis=dict(title='Intensity'),
                    title="Reported Intensities (EMS-98) vs Distance" if language == 'en' else "Intensidades Reportadas (EMS-98) vs Distancia",
                    template="plotly_white"
                )
            else:
                fig_map_intensities = {}
                fig_intensity = {}
            
            # --- Delay and Alert Graphs ---
            
            if df_eventnotif.empty or updateno is None:
                return fig_map_intensities, fig_intensity, {}, {}
    
            # Filter valid updatenos
            total_updateno_0 = df_eventnotif[df_eventnotif['updateno'] == 0].shape[0]
            valid_updatenos = df_eventnotif.groupby('updateno').filter(lambda x: x.shape[0] >= total_updateno_0 / 3)['updateno'].unique()
            
            # Filter by osversion
            if osversion and osversion != 'all':
                df_eventnotif = df_eventnotif[df_eventnotif['osversion'].str.lower() == osversion.lower()]
    
            if updateno != 'all':
                df_filtered = df_eventnotif[df_eventnotif['updateno'] == updateno]
            else:
                df_filtered = df_eventnotif[df_eventnotif['updateno'].isin(valid_updatenos)]
    
            # Histogram of delays by updateno
            percentil_95 = df_filtered['delay'].quantile(0.95)
            df_filtered = df_filtered[df_filtered['delay'] <= percentil_95]
    
            bin_width = 0.5  # Bin width in seconds
            bins = np.arange(df_filtered['delay'].min(), df_filtered['delay'].max() + bin_width, bin_width)
    
            fig_delay = px.histogram(df_filtered, x="delay", nbins=len(bins), title="Delay Distribution" if language == 'en' else "Distribución de los Retrasos",
                                     color="updateno", barmode="overlay", histnorm=None,
                                     labels={"delay": "Delay [s]" if language == 'en' else "Retraso [s]", "updateno": "Update" if language == 'en' else "Actualización"},
                                     color_discrete_sequence=px.colors.qualitative.Dark24)
            fig_delay.update_layout(xaxis_title="Delay [s]" if language == 'en' else "Retraso [s]", yaxis_title="Number of Users" if language == 'en' else "Número de Usuarios", template="plotly_white")
            fig_delay.update_xaxes(range=[-1, 120])  # Set X range from -1 to 120 seconds
    
            # Graph of categorized alerts
            df_eventnotif['alert_category'] = df_eventnotif['alert'].apply(lambda x: 'Red Alert' if x == 1 else ('Orange Alert' if x == 2 else ('Green Alert' if x == 3 else 'Quick Notification')))
            fig_alert = px.histogram(df_eventnotif[df_eventnotif['updateno'].isin(valid_updatenos)], x="updateno", color="alert_category", barmode="stack",
                                     category_orders={"alert_category": ["Red Alert", "Orange Alert", "Green Alert", "Quick Notification"]},
                                     color_discrete_map={"Red Alert": "#FF0000", "Orange Alert": "#FFA500", "Green Alert": "#008000", "Quick Notification": "#0000FF"},
                                     title="Notification Types by Update" if language == 'en' else "Tipos de Notificaciones por Actualización")
            fig_alert.update_layout(xaxis_title="Update Number" if language == 'en' else "Número de Actualización", yaxis_title="Number of Users" if language == 'en' else "Número de Usuarios", template="plotly_white", bargap=0.2)
            fig_alert.update_xaxes(type='linear', tickmode='linear', dtick=1)  # Ensure X values are integers
    
            return fig_map_intensities, fig_intensity, fig_delay, fig_alert
        
        return {}, {}, {}, {}
    
    # Callback to update the second dashboard for swavearrival
    @app.callback(
        [Output('map-swavearrival', 'figure'),
         Output('graph-swavearrival', 'figure')],
        [Input('input-eventid', 'value'),
         Input('dropdown-updateno-2', 'value'),
         Input('language-dropdown', 'value')]
    )
    def update_dashboard_2(eventid, updateno, language):
        if eventid:
            _, df_eventnotif, df_eventinfo = get_data(eventid)
            
            if df_eventinfo.empty or df_eventnotif.empty or updateno is None:
                return {}, {}
    
            magnitude = df_eventinfo.iloc[0]['magnitude']
            depth = df_eventinfo.iloc[0]['depth']
            epiLat = df_eventinfo.iloc[0]['latitude']
            epiLon = df_eventinfo.iloc[0]['longitude']
            
            # Filter by the selected updateno
            df_eventnotif = df_eventnotif[df_eventnotif['updateno'] == updateno]
            
            # Map of swavearrival
            df_eventnotif = df_eventnotif[(df_eventnotif['swavearrival'] >= -50) & (df_eventnotif['swavearrival'] <= 50)]
            
            df_eventnotif['lat'] = df_eventnotif.apply(lambda row: row['userlat'] if row['alertsite'] == 1 else row['userlatpoi'], axis=1)
            df_eventnotif['lon'] = df_eventnotif.apply(lambda row: row['userlon'] if row['alertsite'] == 1 else row['userlonpoi'], axis=1)
            df_eventnotif = df_eventnotif.dropna(subset=['lat', 'lon'])
    
            fig_map_swavearrival = go.Figure(go.Scattermapbox(
                lat=df_eventnotif['lat'],
                lon=df_eventnotif['lon'],
                mode='markers',
                marker=go.scattermapbox.Marker(
                    size=6,
                    color=df_eventnotif['swavearrival'],
                    colorscale='BrBG',
                    colorbar=dict(
                        title='swavearrival (s)',
                        x=0.5,
                        y=-0.1,
                        orientation='h',
                        thickness=15
                    ),
                    symbol='circle'
                ),
                text=df_eventnotif['swavearrival'],
                name=f'Updateno {updateno}'
            ))
    
            fig_map_swavearrival.add_trace(go.Scattermapbox(
                lat=[epiLat],
                lon=[epiLon],
                mode='markers',
                marker=go.scattermapbox.Marker(
                    size=20,
                    color='black',
                    symbol='circle'
                ),
                text="Mag: " + str(magnitude),
                name="Epicenter"
            ))
    
            fig_map_swavearrival.update_layout(
                mapbox=dict(
                    center=dict(lat=epiLat, lon=epiLon),
                    zoom=5,
                    style="carto-positron"
                ),
                margin=dict(l=0, r=0, t=0, b=0),
                title="Mapa de Swavearrival" if language == 'es' else "Swavearrival Map"
            )
    
            # Epicentral Distance vs Swavearrival Graph
            df_eventnotif = df_eventnotif[(df_eventnotif['swavearrival'] >= -30) & (df_eventnotif['swavearrival'] <= 120)]
            
            df_eventnotif['lat'] = df_eventnotif.apply(lambda row: row['userlat'] if row['alertsite'] == 1 else row['userlatpoi'], axis=1)
            df_eventnotif['lon'] = df_eventnotif.apply(lambda row: row['userlon'] if row['alertsite'] == 1 else row['userlonpoi'], axis=1)
            df_eventnotif = df_eventnotif.dropna(subset=['lat', 'lon'])
    
            df_eventnotif['epi_distance'] = df_eventnotif.apply(lambda row: distanceEpiToPoint(epiLat, epiLon, row['lat'], row['lon']), axis=1)
            
            total = len(df_eventnotif)
            before_swave = len(df_eventnotif[df_eventnotif['swavearrival'] >= 0])
            after_swave = len(df_eventnotif[df_eventnotif['swavearrival'] < 0])
    
            try:
                percentage_before = (before_swave / total) * 100
            except:
                # potential division by zero
                percentage_before = 0
            try:
                percentage_after = (after_swave / total) * 100
            except:
                # potential division by zero
                percentage_after = 0
    
            fig_swavearrival = go.Figure()
    
            fig_swavearrival.add_trace(go.Scatter(
                x=df_eventnotif['epi_distance'],
                y=df_eventnotif['swavearrival'],
                mode='markers',
                marker=dict(
                    size=6,
                    color='white',
                    line=dict(width=1, color=['red' if val < 0 else 'green' for val in df_eventnotif['swavearrival']])
                ),
                name=f'Updateno {updateno}'
            ))
    
            fig_swavearrival.add_shape(
                go.layout.Shape(
                    type="line",
                    x0=0, y0=0, x1=max(df_eventnotif['epi_distance']), y1=0,
                    line=dict(color="black", width=2)
                )
            )
    
            fig_swavearrival.add_annotation(
                xref="paper", yref="paper",
                x=0.5, y=1.1,
                showarrow=False,
                text=f"{percentage_before:.0f}% arrived before S-wave" if language == 'en' else f"{percentage_before:.0f}% llegó antes de la onda S",
                font=dict(color="green")
            )
            fig_swavearrival.add_annotation(
                xref="paper", yref="paper",
                x=0.5, y=1.05,
                showarrow=False,
                text=f"{percentage_after:.0f}% arrived with or after S-wave" if language == 'en' else f"{percentage_after:.0f}% llegó con o después de la onda S",
                font=dict(color="red")
            )
    
            fig_swavearrival.update_layout(
                xaxis=dict(title='Epicentral Distance (km)' if language == 'en' else 'Distancia Epicentral (km)', range=[0, 120]),
                yaxis=dict(title='S-wave Arrival Time (s)' if language == 'en' else 'Tiempo de llegada de la onda S (s)', range=[-30, 60]),
                title="Epicentral Distance vs S-wave Arrival Time" if language == 'en' else "Distancia Epicentral vs Tiempo de llegada de la onda S",
                template="plotly_white"
            )
    
            return fig_map_swavearrival, fig_swavearrival
        
        return {}, {}
    
    # Callback to update the header title based on selected language
    @app.callback(
        Output('header-title', 'children'),
        Input('language-dropdown', 'value')
    )
    def update_header(language):
        if language == 'es':
            return "Visualización de Sismos"
        return "Earthquake Visualization"
    
    # Callback to update placeholder texts based on selected language
    @app.callback(
        [Output('input-eventid', 'placeholder'),
         Output('dropdown-updateno-1', 'placeholder'),
         Output('dropdown-osversion-1', 'placeholder')],
        Input('language-dropdown', 'value')
    )
    def update_placeholders(language):
        if language == 'es':
            return ['Ingrese el eventid', "Seleccione Updateno (Intensidad/Swavearrival)", "Seleccione OS Version (Intensidad/Swavearrival)"]
        return ['Enter eventid', "Select Updateno (Intensity/Swavearrival)", "Select OS Version (Intensity/Swavearrival)"]
    
    # Callback to populate the cards based on eventid and language
    @app.callback(
        [Output('event-description', 'children'),
         Output('event-details', 'children'),
         Output('max-intensity', 'children'),
         Output('intensity-report', 'children'),
         Output('total-users', 'children'),
         Output('users-report', 'children'),
         Output('max-intensity-card', 'style'),
         Output('event-card-header', 'children'),
         Output('max-intensity-card-header', 'children'),
         Output('notified-users-card-header', 'children')],
        [Input('input-eventid', 'value'),
         Input('language-dropdown', 'value')]
    )
    def update_resume_cards(eventid, language):
        if eventid:
            magnitude, origintime, depth, description, max_intensity, total_users, android_users, ios_users, intensity_users = get_resume_data(eventid)
            
            # Translations
            if language == 'es':
                magnitud_label = "Magnitud"
                evento_label = "Evento"
                prof_label = "Prof."
                fecha_hora_label = "Fecha y Hora del sismo"
                max_intensidad_label = "Máxima Intensidad Reportada"
                usuarios_notificados_label = "Usuarios Notificados"
                usuarios_label = "Usuarios"
                reportes_usuarios_label = "reportes de Usuarios"
                max_intensity_text = f"{intToColorDescription(max_intensity).split(';')[0].replace('Light', 'Leve').replace('Moderate', 'Moderada').replace('Strong', 'Fuerte')}"
            else:
                magnitud_label = "Magnitude"
                evento_label = "Event"
                prof_label = "Depth"
                fecha_hora_label = "Date and Time"
                max_intensidad_label = "Maximum Reported Intensity"
                usuarios_notificados_label = "Notified Users"
                usuarios_label = "Users"
                reportes_usuarios_label = "user reports"
                max_intensity_text = f"{intToColorDescription(max_intensity).split(';')[0]}"
            
            # Card content
            event_description = f"{magnitud_label}: {magnitude}, {prof_label}: {depth} KM."
            event_details = f"{description}\n{fecha_hora_label}: {origintime} (UTC)"
            intensity_report = f"{intensity_users} {reportes_usuarios_label}"
            total_users_text = f"{total_users} {usuarios_label}"
            users_report = f"{android_users} Android, {ios_users} iOS"
            
            # Get background color based on intensity
            background_color = intToColorDescription(max_intensity).split(';')[1]
            card_style = {"background-color": background_color, "text-align": "center"}
            
            return (event_description, event_details, max_intensity_text, intensity_report, 
                    total_users_text, users_report, card_style, 
                    evento_label, max_intensidad_label, usuarios_notificados_label)
        
        return [""] * 6 + [{"background-color": "#FFFFFF", "text-align": "center"}] + [""] * 3
    
# Run the application
if __name__ == '__main__':
    from dash import Dash
    app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP],suppress_callback_exceptions=True)
    app.layout = layout
    register_callbacks(app)
    app.run_server(debug=True)

