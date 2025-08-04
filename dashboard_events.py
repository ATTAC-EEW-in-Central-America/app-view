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
from dash import dcc, html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import plotly.express as px
import plotly.graph_objs as go
import numpy as np
from os import path
import time
import logging

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Helper Functions ---
def load_db_path():
    script_dir = path.dirname(path.abspath(__file__))
    config_path = path.join(script_dir, 'config.json')
    with open(config_path) as config_file:
        config = json.load(config_file)
    return config['database_path_events_silent']

# Vectorized versions for performance on large datasets
def vectorized_distanceEpiToPoint(epiLat, epiLon, lat_series, lon_series):
    lat_series = pd.to_numeric(lat_series, errors='coerce')
    lon_series = pd.to_numeric(lon_series, errors='coerce')
    valid_mask = lat_series.notna() & lon_series.notna()
    result = pd.Series(np.nan, index=lat_series.index)
    if not valid_mask.any(): return result
    
    rEpiLat, rEpiLon = np.radians(epiLat), np.radians(epiLon)
    rLat, rLon = np.radians(lat_series[valid_mask]), np.radians(lon_series[valid_mask])
    
    # Using np.sin and np.cos for vectorization
    distance = np.arccos(np.sin(rEpiLat) * np.sin(rLat) + np.cos(rEpiLat) * np.cos(rLat) * np.cos(rEpiLon - rLon)) * 6371
    result.loc[valid_mask] = distance
    return result

def distanceEpiToPoint(epiLat, epiLon, lat, lon):
    if pd.isna(lat) or pd.isna(lon): return None
    rEpiLat, rEpiLon, rLat, rLon = map(math.radians, [epiLat, epiLon, lat, lon])
    distance = math.acos(math.sin(rEpiLat) * math.sin(rLat) + math.cos(rEpiLat) * math.cos(rLat) * math.cos(rEpiLon - rLon)) * 6371
    return distance

def distanceHypoToPoint(epiLat, epiLon, depth, lat, lon):
    if pd.isna(lat) or pd.isna(lon): return None
    epi_distance = distanceEpiToPoint(epiLat, epiLon, lat, lon)
    if epi_distance is None: return None
    return math.sqrt(epi_distance**2 + depth**2)

# IPE Equation
def ipe_allen2012_hyp(epiDistance, magnitude, depth):
    a = 2.085
    b = 1.428
    c = -1.402
    d = 0.078
    s = 1.0
    m1 = -0.209
    m2 = 2.042
    
    if depth < 0: return -1
    
    hypoDistance = math.sqrt(math.pow(epiDistance, 2) + math.pow(depth, 2))
    rm = m1 + m2 * math.exp(magnitude - 5)
    
    log_arg = math.sqrt(math.pow(hypoDistance, 2) + math.pow(rm, 2))
    if log_arg <= 0: return 0
        
    if hypoDistance <= 50:
        I = a + b * magnitude + c * math.log(log_arg) + s
    else:
        I = a + b * magnitude + c * math.log(log_arg) + d * math.log(hypoDistance / 50) + s
    
    intensity = round(I)
    
    if intensity > 12: return 12
    elif intensity < 0: return 0
    else: return I

def ipe_allen2012_hyp_sigma(epiDistance, depth):
    s1, s2, s3 = 0.82, 0.37, 22.9
    hypoDistance = math.sqrt(math.pow(epiDistance, 2) + math.pow(depth, 2))
    return s1 + s2 / (1 + math.pow(hypoDistance / s3, 2))

def intToColorDescription(intVal):
    if pd.isna(intVal): intVal = -1
    intVal = int(round(intVal)) if intVal != -1 else -1
    if not (0 <= intVal <= 12): intVal = -1
    colorDict = {-1:"--",0:"I. Not Felt",1:"II. Very Weak",2:"III. Weak",3:"IV. Light",4:"V. Moderate",5:"VI. Strong",6:"VII. Very Strong",7:"VIII. Severe",8:"IX. Violent",9:"X. Extreme",10:"XI. Extreme",11:"XII. Extreme",12:"XII. Extreme"}
    color = {-1:"#FFFFFF",0:"#D3D3D3",1:"#BFCCFF",2:"#9999FF",3:"#80FFFF",4:"#7DF894",5:"#FFFF00",6:"#FFC800",7:"#FF9100",8:"#FF0000",9:"#C80000",10:"#800000",11:"#000000",12:"#000000"}
    return f"{colorDict[intVal]};{color[intVal]}"

def get_data(eventid):
    db_path = load_db_path()
    with sqlite3.connect(db_path) as conn:
        df_intensity = pd.read_sql(f"SELECT * FROM intensityreports WHERE eventid='{eventid}'", conn)
        df_eventnotif = pd.read_sql(f"SELECT * FROM eventnotif WHERE eventid='{eventid}'", conn)
        df_eventinfo = pd.read_sql(f"SELECT * FROM eventinfo WHERE eventid='{eventid}' ORDER BY updatetime DESC LIMIT 1", conn)
    return df_intensity, df_eventnotif, df_eventinfo

def get_resume_data(eventid):
    db_path = load_db_path()
    with sqlite3.connect(db_path) as conn:
        df_eventinfo = pd.read_sql(f"SELECT magnitude, origintime, depth, description FROM eventinfo WHERE eventid='{eventid}' ORDER BY updatetime DESC LIMIT 1", conn)
        df_intensity = pd.read_sql(f"SELECT intensity FROM intensityreports WHERE eventid='{eventid}'", conn)
        df_eventnotif = pd.read_sql(f"SELECT userid, osversion FROM eventnotif WHERE eventid='{eventid}'", conn)
    if df_eventinfo.empty: return [None] * 9
    magnitude = round(df_eventinfo['magnitude'].values[0], 1)
    origintime = df_eventinfo['origintime'].values[0]
    depth = int(df_eventinfo['depth'].values[0])
    description = df_eventinfo['description'].values[0]
    max_intensity, intensity_report_users = None, 0
    if not df_intensity.empty:
        p95 = df_intensity['intensity'].quantile(0.95)
        filtered = df_intensity[df_intensity['intensity'] <= p95]
        if not filtered.empty:
            max_intensity = filtered['intensity'].max()
            intensity_report_users = len(filtered)
    unique_users = df_eventnotif.drop_duplicates(subset='userid')
    return magnitude, origintime, depth, description, max_intensity, len(unique_users), len(unique_users[unique_users['osversion'].str.lower() == 'android']), len(unique_users[unique_users['osversion'].str.lower() == 'ios']), intensity_report_users


# --- Layout for the Events Tab ---
layout = dbc.Container([
    dbc.Row([dbc.Col(html.H1(id="events-header-title", className="text-center mb-4"))]),
    dbc.Row([
        dbc.Col(dbc.Card([dbc.CardHeader(id="events-event-card-header"), dbc.CardBody([html.H5(id="events-event-description", className="card-title"), html.P(id="events-event-details")])]), width=4),
        dbc.Col(dbc.Card([dbc.CardHeader(id="events-max-intensity-card-header"), dbc.CardBody([html.H5(id="events-max-intensity", className="card-title"), html.P(id="events-intensity-report")], id="events-max-intensity-card")]), width=4),
        dbc.Col(dbc.Card([dbc.CardHeader(id="events-notified-users-card-header"), dbc.CardBody([html.H5(id="events-total-users", className="card-title"), html.P(id="events-users-report")], style={"background-color": "#F8F9FA", "text-align": "center"})]), width=4)
    ], className="mb-4"),
    dbc.Row([
        dbc.Col([dcc.Input(id='events-input-eventid', type='text', placeholder='Enter eventid', debounce=True), dcc.Dropdown(id='events-dropdown-eventid', placeholder='Select an eventid')], width=8),
        dbc.Col(dcc.Dropdown(id='events-language-dropdown', options=[{'label': 'English', 'value': 'en'}, {'label': 'Español', 'value': 'es'}], value='en', clearable=False, className="mb-2"), width=4),
    ], justify="center"),
    dbc.Row([dbc.Col(dcc.Loading(dcc.Graph(id='events-map-intensities')), width=6), dbc.Col(dcc.Loading(dcc.Graph(id='events-graph-intensity')), width=6)]),
    dbc.Row([dbc.Col([dcc.Dropdown(id='events-dropdown-updateno-1', multi=False, placeholder="Select Updateno"), dcc.Dropdown(id='events-dropdown-osversion-1', multi=False, placeholder="Select OS Version"), dcc.Loading(dcc.Graph(id='events-graph-delay'))], width=6), dbc.Col(dcc.Loading(dcc.Graph(id='events-graph-alert')), width=6)]),
    dbc.Row([dbc.Col([dcc.Dropdown(id='events-dropdown-updateno-2', multi=False, style={'width': '100%', 'font-size': '12px'}), dcc.Loading(dcc.Graph(id='events-map-swavearrival'))], width=6), dbc.Col(dcc.Loading(dcc.Graph(id='events-graph-swavearrival')), width=6)])
], fluid=True)

def register_callbacks(app, cache):

    @cache.memoize()
    def get_cached_data(eventid):
        logging.info(f"CACHE MISS: Querying database for eventid: {eventid}")
        start_time = time.time()
        df_i, df_en, df_ei = get_data(eventid)
        end_time = time.time()
        logging.info(f"Database query finished. Duration: {end_time - start_time:.2f} seconds.")
        return df_i, df_en, df_ei

    @app.callback(Output('events-input-eventid', 'value'), Input('stored-eventid', 'data'), prevent_initial_call=True)
    def set_initial_eventid(eventid):
        return eventid if eventid else PreventUpdate

    @app.callback(Output('events-input-eventid', 'value', allow_duplicate=True), Input('events-dropdown-eventid', 'value'), prevent_initial_call=True)
    def sync_dropdown_to_input(selected_eventid):
        return selected_eventid if selected_eventid else PreventUpdate
        
    @app.callback(Output('events-dropdown-eventid', 'options'), Input('tabs-example', 'value'))
    def populate_dropdown(tab_value):
        if tab_value != 'tab-3': raise PreventUpdate
        with sqlite3.connect(load_db_path()) as conn:
            df = pd.read_sql("SELECT eventid, magnitude, origintime, description FROM eventinfo ORDER BY origintime DESC LIMIT 100", conn)
#        return [{'label': f"{row['eventid']} - {row['mag']}, {row['origintime']}", 'value': row['eventid']} for _, row in df.iterrows()]
        return [{'label': f"{row['eventid']} - Mag: {round(row['magnitude'], 1)}, OriginTime: {row['origintime']}", 'value': row['eventid']} for _, row in df.iterrows()]

    @app.callback(
        [Output('events-dropdown-updateno-1', 'options'), Output('events-dropdown-updateno-1', 'value')],
        Input('events-input-eventid', 'value'))
    def update_dropdown_1(eventid):
        if not eventid: return [], None
        _, df_eventnotif, _ = get_cached_data(eventid)
        if df_eventnotif.empty: return [], None
        total_updateno_0 = df_eventnotif[df_eventnotif['updateno'] == 0].shape[0]
        valid_updatenos = df_eventnotif.groupby('updateno').filter(lambda x: x.shape[0] >= total_updateno_0 / 3)['updateno'].unique() if total_updateno_0 > 0 else sorted(df_eventnotif['updateno'].unique())
        updateno_options = [{'label': 'All', 'value': 'all'}] + [{'label': f'Updateno {updateno}', 'value': updateno} for updateno in sorted(valid_updatenos)]
        return updateno_options, 'all'

    @app.callback(
        [Output('events-dropdown-osversion-1', 'options'), Output('events-dropdown-osversion-1', 'value')],
        [Input('events-input-eventid', 'value')])
    def update_osversion_1(eventid):
        if not eventid: return [], None
        return [{'label': 'All', 'value': 'all'}, {'label': 'Android', 'value': 'android'}, {'label': 'iOS', 'value': 'ios'}], 'all'

    @app.callback(
        [Output('events-dropdown-updateno-2', 'options'), Output('events-dropdown-updateno-2', 'value')],
        Input('events-input-eventid', 'value'))
    def update_dropdown_2(eventid):
        if not eventid: return [], None
        _, df_eventnotif, _ = get_cached_data(eventid)
        if df_eventnotif.empty: return [], None
        total_updateno_0 = df_eventnotif[df_eventnotif['updateno'] == 0].shape[0]
        valid_updatenos = df_eventnotif.groupby('updateno').filter(lambda x: x.shape[0] >= total_updateno_0 / 3)['updateno'].unique() if total_updateno_0 > 0 else sorted(df_eventnotif['updateno'].unique())
        updateno_options = [{'label': f'Updateno {updateno}', 'value': updateno} for updateno in sorted(valid_updatenos)]
        return updateno_options, 0 if 0 in valid_updatenos else (valid_updatenos[0] if len(valid_updatenos)>0 else None)

    @app.callback(
        [Output('events-map-intensities', 'figure'), Output('events-graph-intensity', 'figure'),
         Output('events-graph-delay', 'figure'), Output('events-graph-alert', 'figure')],
        [Input('events-input-eventid', 'value'), Input('events-dropdown-updateno-1', 'value'),
         Input('events-dropdown-osversion-1', 'value'), Input('events-language-dropdown', 'value')])
    def update_dashboard_1(eventid, updateno, osversion, language):
        if not eventid or updateno is None: raise PreventUpdate
        
        logging.info(f"Callback 'update_dashboard_1' started for eventid: {eventid}")
        start_time = time.time()
        
        df_intensity, df_eventnotif, df_eventinfo = get_cached_data(eventid)
        
        if df_eventinfo.empty: raise PreventUpdate
        magnitude, depth, epiLat, epiLon = df_eventinfo.iloc[0][['magnitude', 'depth', 'latitude', 'longitude']]

        # --- Intensity Plots ---
        fig_map_intensities, fig_intensity = go.Figure(), go.Figure()
        if not df_intensity.empty:
            processing_start = time.time()
            percentil_95 = df_intensity['intensity'].quantile(0.95)
            df_intensity_filtered = df_intensity[df_intensity['intensity'] <= percentil_95].copy()
            if language == 'es':
                intensity_map = {'I. Not Felt': 'I. No Sentido','II. Very Weak': 'II. Muy Débil','III. Weak': 'III. Débil','IV. Light': 'IV. Leve','V. Moderate': 'V. Moderada','VI. Strong': 'VI. Fuerte','VII. Very Strong': 'VII. Muy Fuerte','VIII. Severe': 'VIII. Severo','IX. Violent': 'IX. Violento','X. Extreme': 'X. Extremo','XI. Extreme': 'XI. Extremo','XII. Extreme': 'XII. Extremo'}
            else:
                intensity_map = {'I. Not Felt': 'I. Not Felt','II. Very Weak': 'II. Very Weak','III. Weak': 'III. Weak','IV. Light': 'IV. Light','V. Moderate': 'V. Moderate','VI. Strong': 'VI. Strong','VII. Very Strong': 'VII. Very Strong','VIII. Severe': 'VIII. Severe','IX. Violent': 'IX. Violent','X. Extreme': 'X. Extreme','XI. Extreme': 'XI. Extreme','XII. Extreme': 'XII. Extreme'}
            
            df_intensity_filtered['EMS-98'] = df_intensity_filtered['intensity'].apply(lambda x: intensity_map.get(intToColorDescription(x).split(";")[0]))
            df_intensity_filtered['color'] = df_intensity_filtered['intensity'].apply(lambda x: intToColorDescription(x).split(";")[1])
            df_intensity_filtered.dropna(subset=['EMS-98', 'color'], inplace=True)
            
            # This section for the IPE plot uses your original slow loop to preserve the exact logic
            distances, reported_intensities, colors = [], [], []
            for _, row in df_intensity_filtered.iterrows():
                if pd.notnull(row['lat']) and pd.notnull(row['lon']):
                    hypo_distance = distanceHypoToPoint(epiLat, epiLon, depth, row['lat'], row['lon'])
                    if hypo_distance is not None:
                        distances.append(hypo_distance)
                        reported_intensities.append(row['intensity'])
                        colors.append(row['color'])
            processing_end = time.time()
            logging.info(f"-> update_dashboard_1: Intensity graph processing took {processing_end - processing_start:.2f}s")
            
            figure_gen_start = time.time()
            fig_map_intensities = px.scatter_mapbox(df_intensity_filtered, lat="lat", lon="lon", color="EMS-98", color_discrete_map={intensity_map.get(intToColorDescription(k).split(";")[0]): intToColorDescription(k).split(";")[1] for k in range(13)}, size_max=15, zoom=5, mapbox_style="carto-positron")
            fig_map_intensities.add_trace(go.Scattermapbox(lat=[epiLat], lon=[epiLon], mode='markers', marker=go.scattermapbox.Marker(size=20, color='black', symbol='circle'), name="Epicenter"))
            fig_map_intensities.update_layout(mapbox=dict(center=dict(lat=epiLat, lon=epiLon), zoom=5))

            allenDist = [x for x in range(0, 500, 10)]
            allen_intensities = [ipe_allen2012_hyp(d, magnitude, depth) for d in allenDist]
            sigma_allen = [ipe_allen2012_hyp_sigma(d, depth) for d in allenDist]

            fig_intensity.add_trace(go.Scatter(x=allenDist, y=allen_intensities, mode='lines', name="Allen's IPE 2012 (MMI)", line=dict(color='black')))
            fig_intensity.add_trace(go.Scatter(x=allenDist, y=[i + s for i, s in zip(allen_intensities, sigma_allen)], mode='lines', name='+σ (SD) (MMI)', line=dict(color='gray', dash='dash')))
            fig_intensity.add_trace(go.Scatter(x=allenDist, y=[i - s for i, s in zip(allen_intensities, sigma_allen)], mode='lines', name='-σ (SD) (MMI)', line=dict(color='gray', dash='dash')))
            fig_intensity.add_trace(go.Scatter(x=distances, y=reported_intensities, mode='markers', name='Reported Intensity', marker=dict(size=8, color=colors)))
            fig_intensity.update_layout(xaxis=dict(title='Hypocentral Distance [km]', type='log'), yaxis=dict(title='Intensity'), title="Reported Intensities (EMS-98) vs Distance", template="plotly_white")
            figure_gen_end = time.time()
            logging.info(f"-> update_dashboard_1: Intensity plots generation took {figure_gen_end - figure_gen_start:.2f}s")

        # --- Delay and Alert Graphs ---
        fig_delay, fig_alert = go.Figure(), go.Figure()
        if not df_eventnotif.empty:
            def categorize_alert(row, lang):
                red_alert, orange_alert, green_alert, early_warning, quick_notif = ("Alerta Roja", "Alerta Naranja", "Alerta Verde", "Alerta Roja Tardia", "Notificación Rápida") if lang == 'es' else ("Red Alert", "Orange Alert", "Green Alert", "Late Red Alert", "Quick Notification")
                if row['estmdintensity'] >= 5 and row['swavearrival'] < -5: return early_warning
                elif row['estmdintensity'] >= 3 and row['estmdintensity'] <= 4: return orange_alert
                elif row['alert'] == 1: return red_alert
                elif row['alert'] == 3: return green_alert
                else: return quick_notif
            df_eventnotif['alert_category'] = df_eventnotif.apply(lambda row: categorize_alert(row, language), axis=1)
            
            # Filtering for delay and alert plots
            total_updateno_0 = df_eventnotif.loc[df_eventnotif['updateno'] == 0].shape[0]
            valid_updatenos = df_eventnotif.groupby('updateno').filter(lambda x: x.shape[0] >= total_updateno_0 / 3)['updateno'].unique() if total_updateno_0 > 0 else sorted(df_eventnotif['updateno'].unique())
            df_for_alerts = df_eventnotif[df_eventnotif['updateno'].isin(valid_updatenos)]

            df_filtered_delay = df_eventnotif
            if osversion and osversion != 'all': df_filtered_delay = df_filtered_delay[df_filtered_delay['osversion'].str.lower() == osversion]
            df_filtered_delay = df_filtered_delay[df_filtered_delay['updateno'] == updateno] if updateno != 'all' else df_filtered_delay[df_filtered_delay['updateno'].isin(valid_updatenos)]

            if not df_filtered_delay.empty:
                percentil_95 = df_filtered_delay['delay'].quantile(0.95)
                df_to_sample = df_filtered_delay[df_filtered_delay['delay'] <= percentil_95]
                
                # The number of samples for the distribution is here. 
                # This is important to know because when there are more than 100k plots, 
                # the distribution plot is drawn in minutes. To avoid this issue, it is used
                # the most representative value which can be above of 10k. 
                num_samples = 20000
                
                plot_sample_delay = df_to_sample.sample(n=min(len(df_to_sample), num_samples))
                
                bin_width = 0.5
                bins = np.arange(plot_sample_delay['delay'].min(), plot_sample_delay['delay'].max() + bin_width, bin_width)
                fig_delay = px.histogram(plot_sample_delay, x="delay", nbins=len(bins), title="Delay Distribution", color="updateno", barmode="overlay", labels={"delay": "Delay [s]", "updateno": "Update"}, color_discrete_sequence=px.colors.qualitative.Dark24)
                fig_delay.update_layout(xaxis_title="Delay [s]", yaxis_title="Number of Users", template="plotly_white", xaxis_range=[-1, 120])
            
            category_orders = ["Alerta Roja", "Alerta Temprana", "Alerta Naranja", "Alerta Verde", "Notificación Rápida"] if language == 'es' else ["Red Alert", "Late Red Alert", "Orange Alert", "Green Alert", "Quick Notification"]
            color_map = {"Alerta Roja": "#FF0000", "Alerta Roja Tardia": "#fa6c41", "Alerta Naranja": "#FFA500", "Alerta Verde": "#008000", "Notificación Rápida": "#0000FF"} if language == 'es' else {"Red Alert": "#FF0000", "Late Red Alert": "#fa6c41", "Orange Alert": "#FFA500", "Green Alert": "#008000", "Quick Notification": "#0000FF"}
            fig_alert = px.histogram(df_for_alerts, x="updateno", color="alert_category", barmode="stack", category_orders={"alert_category": category_orders}, color_discrete_map=color_map, title="Notification Types by Update")
            fig_alert.update_layout(xaxis_title="Update Number", yaxis_title="Number of Users", template="plotly_white", bargap=0.2, xaxis=dict(type='linear', tickmode='linear', dtick=1))
        
        end_time = time.time()
        logging.info(f"Callback 'update_dashboard_1' finished. Total duration: {end_time - start_time:.2f} seconds.")
        return fig_map_intensities, fig_intensity, fig_delay, fig_alert

    @app.callback(
        [Output('events-map-swavearrival', 'figure'), Output('events-graph-swavearrival', 'figure')],
        [Input('events-input-eventid', 'value'), Input('events-dropdown-updateno-2', 'value'), 
         Input('events-language-dropdown', 'value')])
    def update_dashboard_2(eventid, updateno, language):
        if not eventid or updateno is None: raise PreventUpdate

        logging.info(f"Callback 'update_dashboard_2' started for eventid: {eventid}, updateno: {updateno}")
        start_time = time.time()
        
        _, df_eventnotif, df_eventinfo = get_cached_data(eventid)

        if df_eventinfo.empty or df_eventnotif.empty: raise PreventUpdate
        magnitude, epiLat, epiLon = df_eventinfo.iloc[0][['magnitude', 'latitude', 'longitude']]
        df_eventnotif = df_eventnotif[df_eventnotif['updateno'] == updateno].copy()
        
        processing_start = time.time()
        df_eventnotif['lat'] = np.where(df_eventnotif['alertsite'] == 1, df_eventnotif['userlat'], df_eventnotif['userlatpoi'])
        df_eventnotif['lon'] = np.where(df_eventnotif['alertsite'] == 1, df_eventnotif['userlon'], df_eventnotif['userlonpoi'])
        df_eventnotif.dropna(subset=['lat', 'lon'], inplace=True)
        df_eventnotif['epi_distance'] = vectorized_distanceEpiToPoint(epiLat, epiLon, df_eventnotif['lat'], df_eventnotif['lon'])
        processing_end = time.time()
        logging.info(f"-> update_dashboard_2: S-Wave data processing took {processing_end - processing_start:.2f}s")

        figure_gen_start = time.time()
        df_map = df_eventnotif[(df_eventnotif['swavearrival'] >= -50) & (df_eventnotif['swavearrival'] <= 50)]
        plot_sample_map = df_map.sample(n=min(len(df_map), 10000))
        
        fig_map_swavearrival = go.Figure(go.Scattermapbox(
           lat=plot_sample_map['lat'],
           lon=plot_sample_map['lon'],
           mode='markers',
           marker=go.scattermapbox.Marker(
               size=6,
               color=plot_sample_map['swavearrival'],
               colorscale='BrBG',
               colorbar=dict(title='swavearrival (s)'),
               symbol='circle'
           ),
           text=plot_sample_map['swavearrival'],
           name='S-wave Arrivals' # Add a name to the trace
        ))
        fig_map_swavearrival.add_trace(go.Scattermapbox(
           lat=[epiLat],
           lon=[epiLon],
           mode='markers',
           marker=go.scattermapbox.Marker(size=20, color='black', symbol='circle'),
           name="Epicenter"
        ))
       
        fig_map_swavearrival.update_layout(
           mapbox=dict(center=dict(lat=epiLat, lon=epiLon), zoom=5, style="carto-positron"),
           title="Swavearrival Map",
           legend=dict(
               yanchor="top",
               y=1,
               xanchor="left",
               x=0.01
           )
        )
        
        df_graph = df_eventnotif[(df_eventnotif['swavearrival'] >= -30) & (df_eventnotif['swavearrival'] <= 120)]
        plot_sample_graph = df_graph.sample(n=min(len(df_graph), 10000))

        fig_swavearrival = go.Figure(go.Scatter(x=plot_sample_graph['epi_distance'], y=plot_sample_graph['swavearrival'], mode='markers', marker=dict(size=6, color='white', line=dict(width=1, color=['red' if val < 0 else 'green' for val in plot_sample_graph['swavearrival']]))))
        if not plot_sample_graph.empty and plot_sample_graph['epi_distance'].notna().any():
            fig_swavearrival.add_shape(type="line", x0=0, y0=0, x1=max(plot_sample_graph['epi_distance'].dropna()), y1=0, line=dict(color="black", width=2))
        
        total = len(df_graph)
        if total > 0:
            before_swave = len(df_graph[df_graph['swavearrival'] >= 0])
            after_swave = total - before_swave
            p_before = (before_swave / total) * 100
            p_after = (after_swave / total) * 100
            fig_swavearrival.add_annotation(xref="paper", yref="paper", x=0.5, y=1.1, showarrow=False, text=f"{p_before:.0f}% arrived before S-wave", font=dict(color="green"))
            fig_swavearrival.add_annotation(xref="paper", yref="paper", x=0.5, y=1.05, showarrow=False, text=f"{p_after:.0f}% arrived with or after S-wave", font=dict(color="red"))

        fig_swavearrival.update_layout(xaxis=dict(title='Epicentral Distance (km)'), yaxis=dict(title='S-wave Arrival Time (s)'), title="Epicentral Distance vs S-wave Arrival Time", template="plotly_white")
        figure_gen_end = time.time()
        logging.info(f"-> update_dashboard_2: Figure generation took {figure_gen_end - figure_gen_start:.2f}s")
        
        end_time = time.time()
        logging.info(f"Callback 'update_dashboard_2' finished. Total duration: {end_time - start_time:.2f} seconds.")
        return fig_map_swavearrival, fig_swavearrival

    # --- UI text and card callbacks ---
    @app.callback(Output('events-header-title', 'children'), Input('events-language-dropdown', 'value'))
    def update_header(language):
        return "Visualización de Sismos" if language == 'es' else "Earthquake Visualization"

    @app.callback(
        [Output('events-input-eventid', 'placeholder'), Output('events-dropdown-updateno-1', 'placeholder'), Output('events-dropdown-osversion-1', 'placeholder')],
        Input('events-language-dropdown', 'value'))
    def update_placeholders(language):
        if language == 'es': return ['Ingrese el eventid', "Seleccione Updateno", "Seleccione Versión OS"]
        return ['Enter eventid', "Select Updateno", "Select OS Version"]

    @app.callback(
        [Output('events-event-description', 'children'), Output('events-event-details', 'children'),
         Output('events-max-intensity', 'children'), Output('events-intensity-report', 'children'),
         Output('events-total-users', 'children'), Output('events-users-report', 'children'),
         Output('events-max-intensity-card', 'style'), Output('events-event-card-header', 'children'),
         Output('events-max-intensity-card-header', 'children'), Output('events-notified-users-card-header', 'children')],
        [Input('events-input-eventid', 'value'), Input('events-language-dropdown', 'value')])
    def update_resume_cards(eventid, language):
        if not eventid: return [""] * 6 + [{"background-color": "#FFFFFF", "text-align": "center"}] + [""] * 3
        data = get_resume_data(eventid)
        if not data or data[0] is None: return ["No data"] * 6 + [{"background-color": "#FFFFFF", "text-align": "center"}] + [""] * 3
        magnitude, origintime, depth, description, max_intensity, total_users, android_users, ios_users, intensity_users = data
        if language == 'es':
            event_desc, event_details = f"Magnitud: {magnitude}, Prof: {depth} KM.", f"{description}\nFecha: {origintime} (UTC)"
            max_i_text = intToColorDescription(max_intensity).split(';')[0].replace('Light', 'Leve').replace('Moderate', 'Moderada').replace('Strong', 'Fuerte')
            i_report, total_text, users_report = f"{intensity_users} reportes", f"{total_users} Usuarios", f"{android_users} Android, {ios_users} iOS"
            headers = ["Evento", "Intensidad Máxima", "Usuarios Notificados"]
        else:
            event_desc, event_details = f"Magnitude: {magnitude}, Depth: {depth} KM.", f"{description}\nDate: {origintime} (UTC)"
            max_i_text = intToColorDescription(max_intensity).split(';')[0]
            i_report, total_text, users_report = f"{intensity_users} reports", f"{total_users} Users", f"{android_users} Android, {ios_users} iOS"
            headers = ["Event", "Max Intensity", "Notified Users"]
        card_style = {"background-color": intToColorDescription(max_intensity).split(';')[1], "text-align": "center"}
        return event_desc, event_details, max_i_text, i_report, total_text, users_report, card_style, headers[0], headers[1], headers[2]

    @app.callback(
        Output('events-input-eventid', 'value', allow_duplicate=True),
        Input('stored-eventid', 'data'),
        prevent_initial_call=True)
    def update_eventid_from_main_store(eventid_from_store):
        return eventid_from_store if eventid_from_store else dash.no_update

# Standalone testing block
if __name__ == '__main__':
    app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
    
    # Mock the cache object for standalone testing
    class MockCache:
        def memoize(self, timeout=None):
            def decorator(func):
                return func
            return decorator
    cache = MockCache()

    app.layout = html.Div([
        dcc.Store(id='stored-eventid', data='us7000kufc'),
        dcc.Tabs(id='tabs-example', value='tab-3', children=[dcc.Tab(label='Events', value='tab-3')]),
        html.Div(id='tabs-content', children=[layout])
    ])
    register_callbacks(app, cache)
    app.run_server(debug=True)
