import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
from urllib.parse import urlparse, parse_qs
from flask_caching import Cache

# Import the layouts and functions of the dashboards
from dashboard_users import layout as layout1, register_callbacks as register_callbacks1
from dashboard_silent import layout as layout2, register_callbacks as register_callbacks2
from dashboard_events import layout as layout3, register_callbacks as register_callbacks3

# --- Helper Functions ---
def load_cfg_path():
    script_dir = path.dirname(path.abspath(__file__))
    config_path = path.join(script_dir, 'config.json')
    with open(config_path) as config_file:
        config = json.load(config_file)
    return config


cfg = load_cfg_path()
cache_size = cfg["cache_size_days"]
cache_path = cfg["cache_folder"]

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server = app.server 

CACHE_CONFIG = {
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': cache_path,
    'CACHE_THRESHOLD': cache_size 
}

cache = Cache()
cache.init_app(server, config=CACHE_CONFIG)

app.layout = dbc.Container([
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='stored-eventid', storage_type='session'),
    dcc.Tabs(id="tabs-example", value='tab-1', children=[
        dcc.Tab(label='Users', value='tab-1'),
        dcc.Tab(label='Silent Notif.', value='tab-2'),
        dcc.Tab(label='Events', value='tab-3'),
    ]),
    html.Div(id='tabs-content')
])

@app.callback(
    [Output('tabs-example', 'value'), Output('stored-eventid', 'data')],
    Input('url', 'search')
)
def select_tab_based_on_url(search):
    if search:
        query_params = parse_qs(urlparse(search).query)
        eventid = query_params.get('eventid', [None])[0]
        if eventid:
            return 'tab-3', eventid 
    return 'tab-1', None  # Default to 'Users' tab

@app.callback(
    Output('tabs-content', 'children'),
    [Input('tabs-example', 'value'), Input('stored-eventid', 'data')]
)
def render_content(tab, stored_eventid):
    if tab == 'tab-1':
        return layout1
    elif tab == 'tab-2':
        return layout2
    elif tab == 'tab-3':
        if stored_eventid:
            return html.Div([layout3, html.Div(f"Event ID: {stored_eventid}")])
        return layout3

# Register the callbacks for each dashboard
register_callbacks1(app)
register_callbacks2(app)
register_callbacks3(app, cache) 

if __name__ == '__main__':
    app.run_server(debug=False, port=8055,
                   host='0.0.0.0',
                   dev_tools_ui=False,
                   dev_tools_props_check=False,
                   dev_tools_serve_dev_bundles=False,
                   dev_tools_hot_reload=False,
                   dev_tools_hot_reload_interval=False,
                   dev_tools_hot_reload_watch_interval=False,
                   dev_tools_hot_reload_max_retry=False,
                   dev_tools_silence_routes_logging=False,
                   dev_tools_prune_errors=False)
