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
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import pandas as pd
import numpy as np
from scipy import stats
import json
from os import path

# Read the JSON file and load the database path
def load_db_path():
    script_dir = path.dirname(path.abspath(__file__))
    config_path = path.join(script_dir, 'dashboard_silent.json')
    with open(config_path) as config_file:
        config = json.load(config_file)
    return config['database_path']

# Set your Mapbox access token
mapbox_access_token = 'your_mapbox_token_here'  # Replace with your actual token
px.set_mapbox_access_token(mapbox_access_token)

# Function to fetch unique senttime, notifid, and osversions from the database
def fetch_unique_values():
    db_path = load_db_path()  # Load the database path from JSON file
    with sqlite3.connect(db_path) as conn:
        senttimes = pd.read_sql_query("SELECT DISTINCT senttime, notifid FROM silentnotif", conn)
        osversions = pd.read_sql_query("SELECT DISTINCT osversion FROM silentnotif", conn)
    senttimes['senttime'] = pd.to_datetime(senttimes['senttime'], unit='ms')
    return senttimes, osversions

senttimes, osversions = fetch_unique_values()

# Find the latest senttime
latest_senttime = senttimes['senttime'].max()

# Add an "All" option to the OS versions
osversion_options = [{'label': 'All', 'value': 'All'}] + [
    {'label': os, 'value': os} for os in osversions['osversion']
]

# Create a dropdown menu with human-readable date-time options and notifid
senttime_options = [
    {'label': f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {notifid}", 'value': time.timestamp() * 1000}
    for time, notifid in zip(senttimes['senttime'], senttimes['notifid'])
]

# Translation dictionary
translations = {
    'en': {
        'title': "Notification Analysis Dashboard",
        'map_title': "Notification Map & Distribution",
        'map_filters': "Map Filters",
        'dist_filters': "Distribution Filters",
        'delay_vs_time_title': "Delay vs Time",
        'user_count_filters': "User Count Filters",
        'users_vs_time_title': "Number of Users vs Time",
        'osversion_placeholder': "Select OS Version",
        'senttime_placeholder': "Select Sent Time",
        'debug_no_data': "No data found for OS version '{os}' and sent time '{time}'.",
        'debug_rows_retrieved': "Selected OS: {os}, Sent Time: {time}, Rows retrieved after filtering: {rows}",
        'delay_distribution_title': "Delay Distribution",
        'delay_seconds': "Delay (seconds)",
        'count': "Count",
        'time': "Time",
        'number_of_users': "Number of Users",
        'log10_delay': "Log10(Delay)",
        'select_language': "Select Language"
    },
    'es': {
        'title': "Tablero de Análisis de Notificaciones",
        'map_title': "Mapa de Notificaciones y Distribución",
        'map_filters': "Filtros de Mapa",
        'dist_filters': "Filtros de Distribución",
        'delay_vs_time_title': "Retraso vs Tiempo",
        'user_count_filters': "Filtros de Conteo de Usuarios",
        'users_vs_time_title': "Número de Usuarios vs Tiempo",
        'osversion_placeholder': "Seleccionar Versión de OS",
        'senttime_placeholder': "Seleccionar Hora de Envío",
        'debug_no_data': "No se encontraron datos para la versión de OS '{os}' y la hora de envío '{time}'.",
        'debug_rows_retrieved': "OS seleccionado: {os}, Hora de Envío: {time}, Filas recuperadas después de filtrar: {rows}",
        'delay_distribution_title': "Distribución de Retrasos",
        'delay_seconds': "Retraso (segundos)",
        'count': "Cuenta",
        'time': "Tiempo",
        'number_of_users': "Número de Usuarios",
        'log10_delay': "Log10(Retraso)",
        'select_language': "Seleccionar Idioma"
    }
}

# Layout
#app.layout = dbc.Container([
layout = dbc.Container([
    html.H1(id="dashboard-title", className="text-center mt-4 mb-4"),
    
    # Language selection dropdown
    dbc.Row([
        dbc.Col([
            dcc.Dropdown(
                id='language-dropdown',
                options=[
                    {'label': 'English', 'value': 'en'},
                    {'label': 'Español', 'value': 'es'}
                ],
                value='en',  # Default to English
                clearable=False,
                className="mb-4"
            )
        ], width=3)
    ], justify="end"),
    
    dbc.Row([
        dbc.Col([
            html.H5(id="map-title", className="text-center mb-4"),
            dbc.Card([
                dbc.CardHeader(id="map-filters-header"),
                dbc.CardBody([
                    dcc.Dropdown(
                        id='osversion-dropdown-map',
                        options=osversion_options,
                        value='All',  # Default to "All"
                        placeholder="",
                        className="mb-3"
                    ),
                    dcc.Dropdown(
                        id='senttime-dropdown-map',
                        options=senttime_options,
                        value=latest_senttime.timestamp() * 1000,  # Default to the latest senttime
                        placeholder="",
                        className="mb-3"
                    ),
                    dcc.Loading(
                        id="loading-map",
                        type="default",
                        children=[
                            dcc.Graph(id='map-graph'),
                        ]
                    ),
                    html.Div(id='debug-output-map')
                ])
            ])
        ], width=6),
        dbc.Col([
            html.H5(id="dist-title", className="text-center mb-4"),
            dbc.Card([
                dbc.CardHeader(id="dist-filters-header"),
                dbc.CardBody([
                    dcc.Dropdown(
                        id='osversion-dropdown-dist',
                        options=osversion_options,
                        value='All',  # Default to "All"
                        placeholder="",
                        className="mb-3"
                    ),
                    dcc.Dropdown(
                        id='senttime-dropdown-dist',
                        options=senttime_options,
                        value=latest_senttime.timestamp() * 1000,  # Default to the latest senttime
                        placeholder="",
                        className="mb-3"
                    ),
                    dcc.Loading(
                        id="loading-dist",
                        type="default",
                        children=[
                            dcc.Graph(id='dist-graph'),
                        ]
                    ),
                    html.Div(id='debug-output-dist')
                ])
            ])
        ], width=6)
    ]),
    
    dbc.Row([
        dbc.Col([
            html.H5(id="delay-vs-time-title", className="text-center mb-4"),
            dbc.Card([
                dbc.CardHeader(id="delay-vs-time-header"),
                dbc.CardBody([
                    dcc.DatePickerRange(
                        id='date-picker-range',
                        start_date=(latest_senttime - pd.DateOffset(months=3)).to_pydatetime(),
                        end_date=latest_senttime.to_pydatetime(),
                        display_format='YYYY-MM-DD',
                        className="mb-3"
                    ),
                    dbc.Button(id="show-all-data-button", color="primary", className="mb-3"),
                    dcc.Loading(
                        id="loading-delay-time",
                        type="default",
                        children=[
                            dcc.Graph(id='delay-time-graph'),
                        ]
                    ),
                    html.Div(id='debug-output-delay')
                ])
            ])
        ], width=6),
        dbc.Col([
            html.H5(id="users-vs-time-title", className="text-center mb-4"),
            dbc.Card([
                dbc.CardHeader(id="user-count-filters-header"),
                dbc.CardBody([
                    dcc.Dropdown(
                        id='osversion-dropdown-users',
                        options=osversion_options,
                        value='All',  # Default to "All"
                        placeholder="",
                        className="mb-3"
                    ),
                    dcc.Loading(
                        id="loading-users-time",
                        type="default",
                        children=[
                            dcc.Graph(id='users-time-graph'),
                        ]
                    ),
                    html.Div(id='debug-output-users')
                ])
            ])
        ], width=6)
    ])
], fluid=True)

def register_callbacks(app):
# Callback to update all text based on selected language
    @app.callback(
        [Output('dashboard-title', 'children'),
         Output('map-title', 'children'),
         Output('map-filters-header', 'children'),
         Output('dist-title', 'children'),
         Output('dist-filters-header', 'children'),
         Output('delay-vs-time-title', 'children'),
         Output('user-count-filters-header', 'children'),
         Output('users-vs-time-title', 'children'),
         Output('osversion-dropdown-map', 'placeholder'),
         Output('senttime-dropdown-map', 'placeholder'),
         Output('osversion-dropdown-dist', 'placeholder'),
         Output('senttime-dropdown-dist', 'placeholder'),
         Output('osversion-dropdown-users', 'placeholder'),
         Output('show-all-data-button', 'children')],
        [Input('language-dropdown', 'value')]
    )
    def update_language_text(language):
        trans = translations[language]
        return [
            trans['title'],
            trans['map_title'],
            trans['map_filters'],
            trans['map_title'],
            trans['dist_filters'],
            trans['delay_vs_time_title'],
            trans['user_count_filters'],
            trans['users_vs_time_title'],
            trans['osversion_placeholder'],
            trans['senttime_placeholder'],
            trans['osversion_placeholder'],
            trans['senttime_placeholder'],
            trans['osversion_placeholder'],
            trans['delay_vs_time_title']
        ]
    
    # Callback to update the map based on inputs and provide debug info
    @app.callback(
        [Output('map-graph', 'figure'),
         Output('debug-output-map', 'children')],
        [Input('osversion-dropdown-map', 'value'),
         Input('senttime-dropdown-map', 'value'),
         Input('language-dropdown', 'value')]
    )
    def update_map(selected_os_map, selected_senttime_map, language):
        trans = translations[language]
        if selected_os_map is None or selected_senttime_map is None:
            return {}, trans['debug_no_data'].format(os=selected_os_map, time=selected_senttime_map)
    
        timestamp_map = int(selected_senttime_map)
        db_path = load_db_path()  # Load the database path from JSON file
        with sqlite3.connect(db_path) as conn:
            if selected_os_map == 'All':
                query = f"""
                SELECT userid, userLat, userLon, delay 
                FROM silentnotif 
                WHERE senttime={timestamp_map}
                """
            else:
                query = f"""
                SELECT userid, userLat, userLon, delay 
                FROM silentnotif 
                WHERE osversion='{selected_os_map}' AND senttime={timestamp_map}
                """
            df_map = pd.read_sql_query(query, conn)
    
        if not df_map.empty:
            delay_90th_percentile_map = df_map['delay'].quantile(0.95)
            df_map = df_map[df_map['delay'] <= delay_90th_percentile_map]
    
        debug_message_map = trans['debug_rows_retrieved'].format(os=selected_os_map, time=timestamp_map, rows=len(df_map))
    
        if df_map.empty:
            return {}, trans['debug_no_data'].format(os=selected_os_map, time=timestamp_map)
    
        # Remove rows with NaN values in userLat or userLon
        df_map = df_map.dropna(subset=['userLat', 'userLon'])
    
        # Calculate the center based on the median of the points
        lat_center = df_map['userLat'].median()
        lon_center = df_map['userLon'].median()
    
        fig_map = px.scatter_mapbox(df_map, lat="userLat", lon="userLon", 
                                    color=np.log10(df_map['delay']),
                                    color_continuous_scale='GnBu',
                                    mapbox_style="carto-darkmatter",
                                    center={"lat": lat_center, "lon": lon_center},
                                    zoom=10,
                                    hover_name="userid",
                                    hover_data={"delay": True, "userLat": False, "userLon": False}
                                    )
    
        fig_map.update_coloraxes(colorbar=dict(title=trans['log10_delay']))
    
        return fig_map, debug_message_map
    
    # Callback to update the distribution plot based on inputs and provide debug info
    @app.callback(
        [Output('dist-graph', 'figure'),
         Output('debug-output-dist', 'children')],
        [Input('osversion-dropdown-dist', 'value'),
         Input('senttime-dropdown-dist', 'value'),
         Input('language-dropdown', 'value')]
    )
    def update_distribution(selected_os_dist, selected_senttime_dist, language):
        trans = translations[language]
        if selected_os_dist is None or selected_senttime_dist is None:
            return {}, trans['debug_no_data'].format(os=selected_os_dist, time=selected_senttime_dist)
    
        timestamp_dist = int(selected_senttime_dist)
        db_path = load_db_path()  # Load the database path from JSON file
        with sqlite3.connect(db_path) as conn:
            if selected_os_dist == 'All':
                query = f"""
                SELECT userid, delay 
                FROM silentnotif 
                WHERE senttime={timestamp_dist}
                """
            else:
                query = f"""
                SELECT userid, delay 
                FROM silentnotif 
                WHERE osversion='{selected_os_dist}' AND senttime={timestamp_dist}
                """
            df_dist = pd.read_sql_query(query, conn)
    
        if not df_dist.empty:
            delay_90th_percentile_dist = df_dist['delay'].quantile(0.95)
            df_dist = df_dist[df_dist['delay'] <= delay_90th_percentile_dist]
    
        if len(df_dist) < 10:
            return {}, trans['debug_no_data'].format(os=selected_os_dist, time=timestamp_dist)
    
        debug_message_dist = trans['debug_rows_retrieved'].format(os=selected_os_dist, time=timestamp_dist, rows=len(df_dist))
    
        fig_dist = go.Figure(data=[go.Histogram(x=df_dist['delay'], nbinsx=int((df_dist['delay'].max() - df_dist['delay'].min()) / 0.5))])
        
        fig_dist.update_layout(
            title=trans['delay_distribution_title'],
            xaxis_title=trans['delay_seconds'],
            yaxis_title=trans['count'],
            xaxis=dict(range=[-1, 120]),  # Set the x-axis range from -1 to 120 seconds
            bargap=0.2,
            bargroupgap=0.1
        )
    
        return fig_dist, debug_message_dist
    
    # Callback to update the delay vs time plot based on selected date range or all data
    @app.callback(
        [Output('delay-time-graph', 'figure'),
         Output('debug-output-delay', 'children')],
        [Input('date-picker-range', 'start_date'),
         Input('date-picker-range', 'end_date'),
         Input('show-all-data-button', 'n_clicks'),
         Input('language-dropdown', 'value')]
    )
    def update_delay_time(start_date, end_date, n_clicks, language):
        trans = translations[language]
        all_data = False
        if n_clicks and n_clicks > 0:
            all_data = True
        db_path = load_db_path()
        with sqlite3.connect(db_path) as conn:
            if all_data:
                query = f"""
                SELECT senttime, delay 
                FROM silentnotif
                """
            else:
                start_timestamp = int(pd.to_datetime(start_date).timestamp() * 1000)
                end_timestamp = int(pd.to_datetime(end_date).timestamp() * 1000)
                query = f"""
                SELECT senttime, delay 
                FROM silentnotif
                WHERE senttime BETWEEN {start_timestamp} AND {end_timestamp}
                """
            df_delay_time = pd.read_sql_query(query, conn)
    
        fig_delay_time = go.Figure()
    
        for senttime in df_delay_time['senttime'].unique():
            df_subset = df_delay_time[df_delay_time['senttime'] == senttime]
    
            if len(df_subset) < 50:
                continue
    
            delay_90th_percentile = df_subset['delay'].quantile(0.95)
            df_subset = df_subset[df_subset['delay'] <= delay_90th_percentile]
    
            if df_subset.empty:
                continue
    
            try:
                mode_delay = stats.mode(df_subset['delay'])[0][0]
            except IndexError:
                mode_delay = df_subset['delay'].mean()
    
            std_delay = df_subset['delay'].std()
    
            time_value = pd.to_datetime(senttime, unit='ms')
    
            fig_delay_time.add_trace(go.Scatter(
                x=[time_value],
                y=[mode_delay],
                mode='markers',
                marker=dict(size=10, color='blue'),
                showlegend=False
            ))
    
            fig_delay_time.add_trace(go.Scatter(
                x=[time_value, time_value],
                y=[mode_delay - std_delay, mode_delay + std_delay],
                mode='lines',
                line=dict(color='black', width=1, dash='dot'),  # Make the standard deviation line thinner and dotted
                showlegend=False
            ))
    
        fig_delay_time.update_layout(
            title=trans['delay_vs_time_title'],
            xaxis_title=trans['time'],
            yaxis_title=trans['delay_seconds'],
            yaxis_type="log",
            xaxis=dict(
                tickformat='%Y-%m-%d %H:%M:%S',
                title=trans['time']
            ),
            showlegend=False
        )
    
        return fig_delay_time, trans['delay_vs_time_title']
    
    # Callback to update the number of users vs time plot based on osversion
    @app.callback(
        [Output('users-time-graph', 'figure'),
         Output('debug-output-users', 'children')],
        [Input('osversion-dropdown-users', 'value'),
         Input('language-dropdown', 'value')]
    )
    def update_users_time(selected_os_users, language):
        trans = translations[language]
        db_path = load_db_path()  # Load the database path from JSON file
        with sqlite3.connect(db_path) as conn:
            if selected_os_users == 'All':
                query = f"""
                SELECT senttime, userid 
                FROM silentnotif
                """
            else:
                query = f"""
                SELECT senttime, userid 
                FROM silentnotif 
                WHERE osversion='{selected_os_users}'
                """
            df_users_time = pd.read_sql_query(query, conn)
    
        df_users_time['senttime'] = pd.to_datetime(df_users_time['senttime'], unit='ms')
        df_users_count = df_users_time.groupby(df_users_time['senttime'].dt.date)['userid'].nunique().reset_index()
    
        fig_users_time = go.Figure()
    
        fig_users_time.add_trace(go.Scatter(
            x=df_users_count['senttime'],
            y=df_users_count['userid'],
            mode='lines+markers',
            line=dict(color='blue', width=2),
            marker=dict(size=6),
            showlegend=False
        ))
    
        fig_users_time.update_layout(
            title=trans['users_vs_time_title'],
            xaxis_title=trans['time'],
            yaxis_title=trans['number_of_users'],
            xaxis=dict(
                tickformat='%Y-%m-%d',
                title=trans['time']
            ),
            showlegend=False
        )
    
        return fig_users_time, trans['users_vs_time_title']
    
if __name__ == '__main__':
    from dash import Dash
    app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP],suppress_callback_exceptions=True)
    app.layout = layout
    register_callbacks(app)
    app.run_server(debug=True)
