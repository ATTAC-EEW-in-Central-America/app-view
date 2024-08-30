import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output

# Importa los layouts y funciones de callbacks de los dashboards
from dashboard_users import layout as layout1, register_callbacks as register_callbacks1
from dashboard_silent import layout as layout2, register_callbacks as register_callbacks2
from dashboard_events import layout as layout3, register_callbacks as register_callbacks3

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)

app.layout = dbc.Container([
    dcc.Tabs(id="tabs-example", value='tab-1', children=[
        dcc.Tab(label='Users', value='tab-1'),
        dcc.Tab(label='Silent Notif.', value='tab-2'),
        dcc.Tab(label='Events', value='tab-3'),
    ]),
    html.Div(id='tabs-content')
])

@app.callback(Output('tabs-content', 'children'),
              Input('tabs-example', 'value'))
def render_content(tab):
    if tab == 'tab-1':
        return layout1
    elif tab == 'tab-2':
        return layout2
    elif tab == 'tab-3':
        return layout3

# Registra los callbacks de cada dashboard
register_callbacks1(app)
register_callbacks2(app)
register_callbacks3(app)

if __name__ == '__main__':
    app.run_server(debug=True, port = 8055)
