import pathlib

import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import plotly.graph_objs as go
from dash.dependencies import Input, Output
import os
import dash
from py_vollib.black import black
from py_vollib.black.implied_volatility import implied_volatility

app = dash.Dash(__name__)
server = app.server
app.config.suppress_callback_exceptions = True
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

#get path
PATH = pathlib.Path(__file__).parent
DATA_PATH = PATH.joinpath("data").resolve()
#get data
df =  pd.read_csv( DATA_PATH.joinpath("test_parameters.csv"), index_col=[6], parse_dates=["Date"])
df = df.dropna()

def calc_iv(df):
    ivr = []
    for date in list(df.index.values):
        curr_ivr = implied_volatility(black(df.loc[date, "flag"], df.loc[date, "F"], df.loc[date, "K"], df.loc[date, "t"], df.loc[date, "r"], df.loc[date, "sigma"]), df.loc[date, "F"], df.loc[date, "K"], df.loc[date, "r"], df.loc[date, "t"], df.loc[date, "flag"])
        ivr.append(curr_ivr)
    df['iv'] = ivr


if 'DYNO' in os.environ:
    app_name = os.environ['DASH_APP_NAME']
else:
    app_name = 'dash-lineplot'


layout = html.Div([html.Div([html.H1("Implied Volatility Rate")], style={'textAlign': "center"}),
                       html.Div([dcc.Dropdown(id="selected-value", multi=True, value=["2D_GraphC"],
                                              options=[{"label": "2D Graph", "value": "2D_GraphC"},
                                                       {"label": "3D Graph", "value": "3D_GraphC"},])],
                                className="row", style={"display": "block", "width": "60%", "margin-left": "auto",
                                                        "margin-right": "auto"}),
                       html.Div([dcc.Graph(id="my-graph")]),

                       ], className="container")

calc_iv(df)

@app.callback( Output('my-graph', 'figure'), [Input('selected-value', 'value')])

def update_figure(selected):
    text = {"2D_GraphC": "2D Graph", "3D_GraphC": "3D Graph"}
    trace = []
    for type in selected:
        trace.append(go.Scatter(x=df["K"], y=df["iv"], name=text[type], mode='lines',
                                marker={'size': 8, "opacity": 0.6, "line": {'width': 0.5}}, ))
    return {"data": trace,
            "layout": go.Layout(title="Implied Volatility Rate", colorway=['#fdae61', '#abd9e9', '#2c7bb6'],
                                yaxis={"title": "Implied Volatility"}, xaxis={"title": "Strike"})}


@app.callback(Output('page-content', 'children'),
              [Input('url', 'pathname')])
def display_page(pathname):
    if pathname is None or pathname.replace(app_name, '').strip('/') == '':
        return layout
    else:
        return layout

if __name__ == '__main__':
    app.run_server(debug=True)

