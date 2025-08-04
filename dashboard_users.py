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
import sqlite3
import pandas as pd
from dash import Dash, dcc, html, clientside_callback
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
import plotly.express as px
import json
from os import path
from datetime import timedelta, date
from dash import callback_context

# Read the JSON file and load the database path
def load_db_path():
    # In a real scenario, consider making the script path more robust
    # For example, using `pathlib.Path(__file__).parent`
    script_dir = path.dirname(path.abspath(__file__))
    config_path = path.join(script_dir, 'config.json')
    with open(config_path) as config_file:
        config = json.load(config_file)
    return config['database_path_tokens']

# Load data from the database
def load_data():
    db_path = load_db_path()
    conn = sqlite3.connect(db_path)
    query_fcm = "SELECT UserID, timestamp, TokenSource FROM fcmTokens WHERE timestamp <= strftime('%s', 'now')"
    query_apns = "SELECT UserID, timestamp FROM apnsTokens WHERE timestamp <= strftime('%s', 'now')"
    df_fcm = pd.read_sql_query(query_fcm, conn)
    df_fcm['timestamp'] = pd.to_datetime(df_fcm['timestamp'], unit='s')
    df_apns = pd.read_sql_query(query_apns, conn)
    df_apns['timestamp'] = pd.to_datetime(df_apns['timestamp'], unit='s')
    conn.close()
    return df_fcm, df_apns

# Translation dictionaries
translations = {
    'en': {
        'android_users': 'Android Users', 'apns_users': 'iOS Users', 'refresh': 'Refresh Data',
        'fcm_tokens': 'FCM Tokens (Android)', 'apns_tokens': 'APNs Tokens (iOS)',
        'user_count_over_time': 'New Android Users Over Time',
        'new_users_by_period': 'New Android Users per Period',
        'user_growth': 'Android User Growth Over Time',
        'apns_user_count': 'New iOS Users Over Time',
        'apns_new_users_by_period': 'New iOS Users per Period',
        'apns_user_growth': 'User iOS Growth Over Time',
        'x_axis_label_time': 'Time', 'x_axis_label_date': 'Date',
        'custom_range_label': 'Or select a custom date range:',
        'time_ranges': [
            {'label': 'Last 24 hours', 'value': '24h'}, {'label': 'Last 7 days', 'value': '7d'},
            {'label': 'Yesterday', 'value': 'yesterday'}, {'label': 'Last 30 days', 'value': '30d'},
            {'label': 'All time', 'value': 'all'}
        ]
    },
    'es': {
        'android_users': 'Usuarios Android', 'apns_users': 'Usuarios iOS', 'refresh': 'Actualizar Datos',
        'fcm_tokens': 'Tokens FCM (Android)', 'apns_tokens': 'Tokens APNs (iOS)',
        'user_count_over_time': 'Usuarios Nuevos de Android en Función del Tiempo',
        'new_users_by_period': 'Nuevos Usuarios Android por Periodo',
        'user_growth': 'Crecimiento de Usuarios Android a lo Largo del Tiempo',
        'apns_user_count': 'Usuarios Nuevos en iOS en Función del Tiempo',
        'apns_new_users_by_period': 'Nuevos Usuarios iOS por Periodo',
        'apns_user_growth': 'Crecimiento de Usuarios iOS a lo Largo del Tiempo',
        'x_axis_label_time': 'Hora', 'x_axis_label_date': 'Fecha',
        'custom_range_label': 'O seleccione un rango de fechas personalizado:',
        'time_ranges': [
            {'label': 'Últimas 24 horas', 'value': '24h'}, {'label': 'Últimos 7 días', 'value': '7d'},
            {'label': 'Ayer', 'value': 'yesterday'}, {'label': 'Últimos 30 días', 'value': '30d'},
            {'label': 'Todo el tiempo', 'value': 'all'}
        ]
    }
}
color_discrete_map = {'android': '#636EFA', 'ios': '#EF553B'}

def register_callbacks(app):
    clientside_callback(
        """
        function(n_intervals) {
            return Intl.DateTimeFormat().resolvedOptions().timeZone;
        }
        """,
        Output('timezone-store', 'data'),
        Input('interval-load-trigger', 'n_intervals')
    )

    @app.callback(
        [
         Output('android-users', 'children'), Output('apns-users', 'children'),
         Output('user_counts_fig', 'figure'),
         Output('new_users_by_period_fig', 'figure'), Output('user_growth_fig', 'figure'),
         Output('apns_user_counts_fig', 'figure'), Output('apns_new_users_by_period_fig', 'figure'),
         Output('apns_user_growth_fig', 'figure'), Output('android-users-title', 'children'),
         Output('apns-users-title', 'children'), Output('refresh-button', 'children'),
         Output('fcm-tokens-title', 'children'), Output('apns-tokens-title', 'children'),
         Output('time-range-selector', 'options'), Output('custom-range-label', 'children')
        ],
        [
         Input('refresh-button', 'n_clicks'), Input('language-selector', 'value'),
         Input('time-range-selector', 'value'), Input('custom-date-picker', 'start_date'),
         Input('custom-date-picker', 'end_date'), Input('timezone-store', 'data')
        ]
    )
    def update_dashboard(n_clicks, lang, time_range, start_date, end_date, timezone):
        ctx = callback_context
        triggered_id = ""
        if ctx.triggered:
            triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]

        df_fcm, df_apns = load_data()
        
        timezone = timezone or 'UTC'
        try:
            df_fcm['timestamp'] = df_fcm['timestamp'].dt.tz_localize('UTC').dt.tz_convert(timezone)
            df_apns['timestamp'] = df_apns['timestamp'].dt.tz_localize('UTC').dt.tz_convert(timezone)
        except TypeError: # Handle cases where timestamp is already localized
            df_fcm['timestamp'] = df_fcm['timestamp'].dt.tz_convert(timezone)
            df_apns['timestamp'] = df_apns['timestamp'].dt.tz_convert(timezone)
        
        use_hourly_agg = False
        
        if triggered_id == 'custom-date-picker' and start_date and end_date:
            start_date_dt = pd.to_datetime(start_date).tz_localize(timezone)
            end_date_dt = pd.to_datetime(end_date).tz_localize(timezone)
            df_fcm = df_fcm[(df_fcm['timestamp'] >= start_date_dt) & (df_fcm['timestamp'] < end_date_dt + timedelta(days=1))]
            df_apns = df_apns[(df_apns['timestamp'] >= start_date_dt) & (df_apns['timestamp'] < end_date_dt + timedelta(days=1))]
            if (end_date_dt.to_pydatetime().date() - start_date_dt.to_pydatetime().date()).days <= 3:
                use_hourly_agg = True
        else:
            now = pd.Timestamp.now(tz=timezone)
            if time_range == '24h':
                use_hourly_agg = True
                df_fcm = df_fcm[df_fcm['timestamp'] >= now - timedelta(hours=24)]
                df_apns = df_apns[df_apns['timestamp'] >= now - timedelta(hours=24)]
            elif time_range == '7d':
                df_fcm = df_fcm[df_fcm['timestamp'] >= now - timedelta(days=7)]
                df_apns = df_apns[df_apns['timestamp'] >= now - timedelta(days=7)]
            elif time_range == 'yesterday':
                use_hourly_agg = True
                today = now.normalize()
                yesterday = today - timedelta(days=1)
                df_fcm = df_fcm[(df_fcm['timestamp'] >= yesterday) & (df_fcm['timestamp'] < today)]
                df_apns = df_apns[(df_apns['timestamp'] >= yesterday) & (df_apns['timestamp'] < today)]
            elif time_range == '30d':
                df_fcm = df_fcm[df_fcm['timestamp'] >= now - timedelta(days=30)]
                df_apns = df_apns[df_apns['timestamp'] >= now - timedelta(days=30)]

        df_fcm_android = df_fcm[df_fcm['TokenSource'] == 'android'].copy()

        android_users = df_fcm_android['UserID'].nunique()
        total_apns_users = df_apns['UserID'].nunique()

        agg_freq = 'H' if use_hourly_agg else 'D'
        x_axis_label = translations[lang]['x_axis_label_time'] if use_hourly_agg else translations[lang]['x_axis_label_date']
        
        df_fcm_android['time_agg'] = df_fcm_android['timestamp'].dt.floor(agg_freq)
        df_apns['time_agg'] = df_apns['timestamp'].dt.floor(agg_freq)
        
        # --- FCM (Android) Charts ---
        user_counts_fig = px.line(df_fcm_android.groupby('time_agg')['UserID'].nunique().reset_index(), x='time_agg', y='UserID', title=translations[lang]['user_count_over_time'], labels={'UserID': 'New Users', 'time_agg': x_axis_label})
        user_counts_fig.update_traces(line_color=color_discrete_map['android'])
        
        new_users_by_period_fig = px.bar(df_fcm_android.groupby('time_agg')['UserID'].nunique().reset_index(), x='time_agg', y='UserID', title=translations[lang]['new_users_by_period'], labels={'UserID': 'New Users', 'time_agg': x_axis_label})
        new_users_by_period_fig.update_traces(marker_color=color_discrete_map['android'])

        df_fcm_sorted = df_fcm_android.sort_values('timestamp')
        df_fcm_unique = df_fcm_sorted.drop_duplicates(subset=['UserID'])
        df_fcm_final = pd.DataFrame()
        if not df_fcm_unique.empty:
            df_fcm_unique['time_agg'] = df_fcm_unique['timestamp'].dt.floor(agg_freq)
            df_fcm_unique['cumulative_users'] = range(1, len(df_fcm_unique) + 1)
            df_fcm_final = df_fcm_unique.groupby('time_agg').agg({'cumulative_users': 'max'}).reset_index()
        user_growth_fig = px.line(df_fcm_final, x='time_agg', y='cumulative_users', title=translations[lang]['user_growth'], labels={'cumulative_users': 'Cumulative Users', 'time_agg': x_axis_label})
        user_growth_fig.update_traces(line_color=color_discrete_map['android'])
        
        # --- APNs (iOS) Charts ---
        apns_user_counts_fig = px.line(df_apns.groupby('time_agg')['UserID'].nunique().reset_index(), x='time_agg', y='UserID', title=translations[lang]['apns_user_count'], labels={'UserID': 'New Users', 'time_agg': x_axis_label})
        apns_user_counts_fig.update_traces(line_color=color_discrete_map['ios'])
        
        apns_new_users_by_period_fig = px.bar(df_apns.groupby('time_agg')['UserID'].nunique().reset_index(), x='time_agg', y='UserID', title=translations[lang]['apns_new_users_by_period'], labels={'UserID': 'New Users', 'time_agg': x_axis_label})
        apns_new_users_by_period_fig.update_traces(marker_color=color_discrete_map['ios'])
        
        df_apns_sorted = df_apns.sort_values('timestamp')
        df_apns_unique = df_apns_sorted.drop_duplicates(subset=['UserID'])
        df_apns_final = pd.DataFrame()
        if not df_apns_unique.empty:
            df_apns_unique['time_agg'] = df_apns_unique['timestamp'].dt.floor(agg_freq)
            df_apns_unique['cumulative_users'] = range(1, len(df_apns_unique) + 1)
            df_apns_final = df_apns_unique.groupby('time_agg').agg({'cumulative_users': 'max'}).reset_index()
        apns_user_growth_fig = px.line(df_apns_final, x='time_agg', y='cumulative_users', title=translations[lang]['apns_user_growth'], labels={'cumulative_users': 'Cumulative Users', 'time_agg': x_axis_label})
        apns_user_growth_fig.update_traces(line_color=color_discrete_map['ios'])

        figures = [user_counts_fig, new_users_by_period_fig, user_growth_fig, apns_user_counts_fig, apns_new_users_by_period_fig, apns_user_growth_fig]
        for fig in figures:
            fig.update_layout(
                plot_bgcolor='white', paper_bgcolor='white',
                title_font=dict(size=18, family='Arial', color='#1f77b4'),
                margin=dict(l=40, r=40, t=50, b=40),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgrey')
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgrey')
        
        time_range_options = translations[lang]['time_ranges']
        custom_range_label_text = translations[lang]['custom_range_label']
        
        return (
            f"{android_users:,}", f"{total_apns_users:,}",
            user_counts_fig, new_users_by_period_fig, user_growth_fig,
            apns_user_counts_fig, apns_new_users_by_period_fig, apns_user_growth_fig,
            translations[lang]['android_users'], translations[lang]['apns_users'],
            translations[lang]['refresh'], translations[lang]['fcm_tokens'],
            translations[lang]['apns_tokens'], time_range_options, custom_range_label_text
        )

# App Layout
layout = dbc.Container([
    dcc.Store(id='timezone-store'),
    dcc.Interval(id='interval-load-trigger', interval=500, max_intervals=1),
    dbc.Row([dbc.Col(html.H1("Users Tokens Analytics for FCM and APNs", className="text-center text-primary mb-4"), width=12)]),
    dbc.Row([dbc.Col(dcc.Dropdown(id='language-selector', options=[{'label': 'English', 'value': 'en'}, {'label': 'Español', 'value': 'es'}], value='en', clearable=False, style={'width': '200px'}), width={'size': 'auto'})]),
    dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([html.H5(id='android-users-title', className="card-title"), html.P(id='android-users', className="card-text")]), color="primary", inverse=True), md=6),
        dbc.Col(dbc.Card(dbc.CardBody([html.H5(id='apns-users-title', className="card-title"), html.P(id='apns-users', className="card-text")]), color="success", inverse=True), md=6),
    ], className="my-4 g-3"),
    dbc.Row([
        dbc.Col(dcc.RadioItems(id='time-range-selector', value='all', inline=True, labelClassName="mr-3"), width=12, lg=7, className="mb-3 mb-lg-0 d-flex align-items-center"),
        dbc.Col([html.P(id='custom-range-label', className="font-weight-bold mb-1"), dcc.DatePickerRange(id='custom-date-picker', min_date_allowed=date(2020, 1, 1), max_date_allowed=date.today(), start_date=None, end_date=None, display_format='YYYY-MM-DD')], width=12, lg=5)
    ], className="mb-4 align-items-center"),
    dbc.Row([dbc.Col(dbc.Button(id="refresh-button", color="primary", className="mb-4 w-100"), width=12)]),
    
    # --- Android (FCM) Section ---
    dbc.Row([dbc.Col(html.H3(id='fcm-tokens-title', className="text-center text-secondary mt-4 mb-3"), width=12)]),
    dbc.Row([dbc.Col(dcc.Graph(id='user_counts_fig'), width=12)], className="mb-4"),
    dbc.Row([
        dbc.Col(dcc.Graph(id='new_users_by_period_fig'), md=6),
        dbc.Col(dcc.Graph(id='user_growth_fig'), md=6)
    ], className="mb-4 g-3"),

    # --- iOS (APNs) Section ---
    dbc.Row([dbc.Col(html.H3(id='apns-tokens-title', className="text-center text-secondary mt-4 mb-3"), width=12)]),
    dbc.Row([dbc.Col(dcc.Graph(id='apns_user_counts_fig'), width=12)], className="mb-4"),
    dbc.Row([
        dbc.Col(dcc.Graph(id='apns_new_users_by_period_fig'), md=6),
        dbc.Col(dcc.Graph(id='apns_user_growth_fig'), md=6)
    ], className="mb-4 g-3"),
    
    dbc.Row([dbc.Col(html.Footer("© 2024 ATTAC Project", className="text-center mt-4 mb-4"), width=12)])
], fluid=True)

# Main execution block
if __name__ == '__main__':
    app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
    app.layout = layout
    register_callbacks(app)
    app.run_server(debug=True)
