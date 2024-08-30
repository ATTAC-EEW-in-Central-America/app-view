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
from dash import Dash, dcc, html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
import plotly.express as px
import json

# Create the dashboard layout using Dash and Bootstrap
#app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Read the JSON file and load the database path
def load_db_path():
    with open('dashboard_users.json') as config_file:
        config = json.load(config_file)
    return config['database_path']

# Load data from the database
def load_data():
    db_path = load_db_path()  # Load the database path from JSON file
    conn = sqlite3.connect(db_path)

    # Load data from the fcmTokens table into a pandas DataFrame
    df_fcm = pd.read_sql_query("SELECT UserID, timestamp, TokenSource FROM fcmTokens", conn)
    df_fcm['timestamp'] = pd.to_datetime(df_fcm['timestamp'], unit='s')

    # Load data from the apnsTokens table into a pandas DataFrame
    df_apns = pd.read_sql_query("SELECT UserID, timestamp FROM apnsTokens", conn)
    df_apns['timestamp'] = pd.to_datetime(df_apns['timestamp'], unit='s')

    # Close the database connection
    conn.close()

    # Daily aggregation
    df_fcm['day'] = df_fcm['timestamp'].dt.to_period('D').astype(str)
    df_apns['day'] = df_apns['timestamp'].dt.to_period('D').astype(str)

    # Calculate summary statistics
    android_users = df_fcm[df_fcm['TokenSource'] == 'android']['UserID'].nunique()
    ios_users_fcm = df_fcm[df_fcm['TokenSource'] == 'ios']['UserID'].nunique()
    total_apns_users = df_apns['UserID'].nunique()

    return df_fcm, df_apns, android_users, ios_users_fcm, total_apns_users

# Translation dictionaries
translations = {
    'en': {
        'android_users': 'Android Users (FCM)',
        'ios_users': 'iOS Users (FCM)',
        'apns_users': 'Total APNs Users',
        'refresh': 'Refresh Data',
        'fcm_tokens': 'FCM Tokens',
        'apns_tokens': 'APNs Tokens',
        'user_count_over_time': 'User Count Over Time by Token Source (FCM)',
        'user_distribution': 'User Distribution by Token Source (FCM)',
        'daily_active_users': 'Daily New Users (FCM)',
        'user_growth': 'User Growth Over Time by Token Source (FCM)',
        'apns_user_count': 'User Count Over Time (APNs)',
        'apns_daily_active_users': 'Daily New Users (APNs)',
        'apns_user_growth': 'User Growth Over Time (APNs)'
    },
    'es': {
        'android_users': 'Usuarios Android (FCM)',
        'ios_users': 'Usuarios iOS (FCM)',
        'apns_users': 'Usuarios Totales de APNs',
        'refresh': 'Actualizar Datos',
        'fcm_tokens': 'Tokens FCM',
        'apns_tokens': 'Tokens APNs',
        'user_count_over_time': 'Conteo de Usuarios a lo Largo del Tiempo por Fuente de Token (FCM)',
        'user_distribution': 'Distribución de Usuarios por Fuente de Token (FCM)',
        'daily_active_users': 'Nuevos Usuarios por Día (FCM)',
        'user_growth': 'Crecimiento de Usuarios a lo Largo del Tiempo por Fuente de Token (FCM)',
        'apns_user_count': 'Conteo de Usuarios a lo Largo del Tiempo (APNs)',
        'apns_daily_active_users': 'Nuevos Usuarios por Día (APNs)',
        'apns_user_growth': 'Crecimiento de Usuarios a lo Largo del Tiempo (APNs)'
    }
}

# Consistent color scheme
color_discrete_map = {
    'android': '#636EFA',  # Blue
    'ios': '#EF553B',      # Red
}

def register_callbacks(app):
    @app.callback(
        [Output('android-users', 'children'),
         Output('ios-users', 'children'),
         Output('apns-users', 'children'),
         Output('user_counts_fig', 'figure'),
         Output('token_distribution_fig', 'figure'),
         Output('daily_active_users_fig', 'figure'),
         Output('user_growth_fig', 'figure'),
         Output('apns_user_counts_fig', 'figure'),
         Output('apns_daily_active_users_fig', 'figure'),
         Output('apns_user_growth_fig', 'figure'),
         Output('android-users-title', 'children'),
         Output('ios-users-title', 'children'),
         Output('apns-users-title', 'children'),
         Output('refresh-button', 'children'),
         Output('fcm-tokens-title', 'children'),
         Output('apns-tokens-title', 'children')],
        [Input('refresh-button', 'n_clicks'),
         Input('language-selector', 'value')]
    )
    def update_dashboard(n_clicks, lang):
        # Load the data
        df_fcm, df_apns, android_users, ios_users_fcm, total_apns_users = load_data()
    
        # Sort and correctly calculate cumulative unique users
        df_fcm_sorted = df_fcm.sort_values('timestamp')
        df_fcm_unique = df_fcm_sorted.drop_duplicates(subset=['UserID', 'TokenSource'])
    
        df_fcm_unique['cumulative_users'] = df_fcm_unique.groupby('TokenSource').cumcount() + 1
        df_fcm_final = df_fcm_unique.groupby(['TokenSource', df_fcm_unique['timestamp'].dt.date]).agg({'cumulative_users': 'max'}).reset_index()
    
        # Create the user growth chart
        user_growth_fig = px.line(
            df_fcm_final,
            x='timestamp', y='cumulative_users', color='TokenSource',
            title=translations[lang]['user_growth'],
            labels={'cumulative_users': 'Cumulative Users', 'timestamp': 'Date'},
            color_discrete_map=color_discrete_map
        )
    
        # Other charts...
        user_counts_fig = px.line(
            df_fcm.groupby([df_fcm['timestamp'].dt.date, 'TokenSource'])['UserID'].nunique().reset_index(),
            x='timestamp', y='UserID', color='TokenSource',
            title=translations[lang]['user_count_over_time'],
            labels={'UserID': 'Number of Users', 'timestamp': 'Date'},
            color_discrete_map=color_discrete_map
        )
    
        token_distribution_fig = px.bar(
            df_fcm.groupby('TokenSource')['UserID'].nunique().reset_index(),
            x='TokenSource', y='UserID', color='TokenSource',
            title=translations[lang]['user_distribution'],
            labels={'UserID': 'Number of Users'},
            color_discrete_map=color_discrete_map
        )
    
        daily_active_users_fig = px.bar(
            df_fcm.groupby(['day', 'TokenSource'])['UserID'].nunique().reset_index(),
            x='day', y='UserID', color='TokenSource',
            title=translations[lang]['daily_active_users'],
            labels={'UserID': 'Number of Users', 'day': 'Day'},
            color_discrete_map=color_discrete_map
        )
    
        # Create charts for apnsTokens
        apns_user_counts_fig = px.line(
            df_apns.groupby(df_apns['timestamp'].dt.date)['UserID'].nunique().reset_index(),
            x='timestamp', y='UserID',
            title=translations[lang]['apns_user_count'],
            labels={'UserID': 'Number of Users', 'timestamp': 'Date'}
        )
    
        apns_daily_active_users_fig = px.bar(
            df_apns.groupby('day')['UserID'].nunique().reset_index(),
            x='day', y='UserID',
            title=translations[lang]['apns_daily_active_users'],
            labels={'UserID': 'Number of Users', 'day': 'Day'}
        )
    
        apns_user_growth_fig = px.line(
            df_apns.groupby(df_apns['timestamp'].dt.date)['UserID'].nunique().cumsum().reset_index(),
            x='timestamp', y='UserID',
            title=translations[lang]['apns_user_growth'],
            labels={'UserID': 'Cumulative Users', 'timestamp': 'Date'}
        )
    
        # Style the figures
        figures = [user_counts_fig, token_distribution_fig, daily_active_users_fig, user_growth_fig,
                   apns_user_counts_fig, apns_daily_active_users_fig, apns_user_growth_fig]
    
        for fig in figures:
            fig.update_layout(
                plot_bgcolor='white',
                paper_bgcolor='white',
                title_font=dict(size=18, family='Arial', color='#1f77b4'),
                margin=dict(l=20, r=20, t=40, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgrey')
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgrey')
    
        return (f"{android_users:,}", f"{ios_users_fcm:,}", f"{total_apns_users:,}",
                user_counts_fig, token_distribution_fig, daily_active_users_fig, user_growth_fig,
                apns_user_counts_fig, apns_daily_active_users_fig, apns_user_growth_fig,
                translations[lang]['android_users'], translations[lang]['ios_users'], translations[lang]['apns_users'],
                translations[lang]['refresh'], translations[lang]['fcm_tokens'], translations[lang]['apns_tokens'])

#app.layout = dbc.Container([
layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H1("Users Tokens Analytics for FCM and APNs", className="text-center text-primary mb-4"), width=12)
    ]),
    dbc.Row([
        dbc.Col(dcc.Dropdown(
            id='language-selector',
            options=[
                {'label': 'English', 'value': 'en'},
                {'label': 'Español', 'value': 'es'}
            ],
            value='en',
            clearable=False,
            style={'width': '200px'}
        ), width=12, className="text-right mb-2")
    ]),
    dbc.Row([
        dbc.Col(dbc.Card(
            dbc.CardBody([
                html.H5(id='android-users-title', className="card-title"),
                html.P(id='android-users', className="card-text"),
            ]),
            color="primary", inverse=True
        ), width=4),
        dbc.Col(dbc.Card(
            dbc.CardBody([
                html.H5(id='ios-users-title', className="card-title"),
                html.P(id='ios-users', className="card-text"),
            ]),
            color="info", inverse=True
        ), width=4),
        dbc.Col(dbc.Card(
            dbc.CardBody([
                html.H5(id='apns-users-title', className="card-title"),
                html.P(id='apns-users', className="card-text"),
            ]),
            color="success", inverse=True
        ), width=4),
    ], className="mb-4"),
    dbc.Row([
        dbc.Col(dbc.Button(id="refresh-button", color="primary", className="mb-4"), width=12)
    ]),
    dbc.Row([
        dbc.Col(html.H5(id='fcm-tokens-title', className="text-center text-secondary mt-4"), width=12)
    ]),
    dbc.Row([
        dbc.Col(dcc.Graph(id='user_counts_fig'), width=12)
    ]),
    dbc.Row([
        dbc.Col(dcc.Graph(id='token_distribution_fig'), width=6),
        dbc.Col(dcc.Graph(id='daily_active_users_fig'), width=6),
    ]),
    dbc.Row([
        dbc.Col(dcc.Graph(id='user_growth_fig'), width=12)
    ]),
    dbc.Row([
        dbc.Col(html.H5(id='apns-tokens-title', className="text-center text-secondary mt-4"), width=12)
    ]),
    dbc.Row([
        dbc.Col(dcc.Graph(id='apns_user_counts_fig'), width=12)
    ]),
    dbc.Row([
        dbc.Col(dcc.Graph(id='apns_daily_active_users_fig'), width=6),
        dbc.Col(dcc.Graph(id='apns_user_growth_fig'), width=6),
    ]),
    dbc.Row([
        dbc.Col(html.Footer("© 2024 ATTAC Project", className="text-center mt-4 mb-4"), width=12)
    ])
], fluid=True)

# Solo ejecutar la aplicación si este archivo es el principal
if __name__ == '__main__':
    from dash import Dash
    app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP],suppress_callback_exceptions=True)
    app.layout = layout
    register_callbacks(app)
    app.run_server(debug=True)

