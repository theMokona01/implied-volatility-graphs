import pathlib
import random

import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import numpy as np
import plotly.graph_objs as go
import py_vollib
from dash.dependencies import Input, Output
import os
import dash
import pprint
import simplejson as sjson
import json
import requests
from py_vollib.black_scholes_merton.implied_volatility import implied_volatility

app = dash.Dash(__name__)
server = app.server
app.config.suppress_callback_exceptions = True
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

# get path
PATH = pathlib.Path(__file__).parent
#DATA_PATH = PATH.joinpath("data").resolve()
# data = DATA_PATH.joinpath("params.csv")

# df = pd.read_csv(data, index_col="Index")


# filepath = os.path.join(os.path.dirname(__file__), "test_data.json")
#json_data = sjson.load(open(DATA_PATH.joinpath("test_data.json"), 'rb'))
json_data = sjson.load(open("test_data.json"), 'rb')
columns = json_data['columns']
index = json_data['index']
data = json_data['data']

df = pd.DataFrame(data, index=index, columns=columns)


# df.to_csv("data_params.csv")

def calc_iv():
    prior_settle = []
    strike_price = []
    strike_range = ["ALL", "ATM", "Active"]
    cme_group_url = "https://www.cmegroup.com/CmeWS/mvc/Quotes/Option/138/G/U9/ALL?optionProductId=138"

    try:
        request = requests.get(cme_group_url + "&strikeRange=" + strike_range[0])
        request_json = json.loads(request.content.decode('utf-8'))
    except ConnectionError as e:
        print(e)

    try:
        for strike in request_json["optionContractQuotes"]:
            str(strike).replace("\'", "\"")
            strike_price.append(strike["strikePrice"])

        for price in request_json["optionContractQuotes"]:
            str(price).replace("\'", "\"")
            prior_settle.append(price["call"]["priorSettle"])
    except Exception as e:
        print(e)

    s = 3000
    t = 0.1
    r = 0.02
    q = 0.02
    flag = 'c'
    counter = 0
    iv = []

    for price in prior_settle:

        iv.append(implied_volatility(float(price), s, float(strike_price[counter]), t, r, q, flag))
        counter = counter + 1

    df = pd.DataFrame()
    df['Strike'] = strike_price
    df['IV'] = iv

    df.to_csv("graphs.csv")
    return iv


# ivr = []


# K = int(df.loc[1, 'K'])
# for index in list(df.index.values):
#     curr_ivr = float(implied_volatility(black('c', df.loc[index, "S"], df.loc[index, "K"], df.loc[index, "t"], df.loc[index, "R"], df.loc[index, "v"]), df.loc[index, "S"], df.loc[index, "K"], df.loc[index, "R"], df.loc[index, "t"], 'c'))
#     ivr.append(round(curr_ivr, 2))
#
#     # only for testing purposes
#     ############################
#     df.set_value(index, 'K', K )
#     K = K + 1
#     #############################
#
#
# df['iv'] = ivr

if 'DYNO' in os.environ:
    app_name = os.environ['DASH_APP_NAME']
else:
    app_name = 'dash-lineplot'

layout = html.Div(className="graphs",
                  children=[html.Div([html.H1("Implied Volatility Rate Graphs")], style={'textAlign': "center"}),
                            html.Div([dcc.Dropdown(id="selected-value", multi=True, value=["2D_option"],
                                                   options=[{"label": "2D Graph", "value": "2D_option"},
                                                            {"label": "3D Graph", "value": "3D_option"}, ])],
                                     className="row", style={"display": "block", "width": "60%", "margin-left": "auto",
                                                             "margin-right": "auto"}),
                            html.Div([dcc.Graph(id="my-graph")]),

                            ]
                  )  # , className="container")

# calc_iv(df)

df.to_csv('test_data')


# values = []
# for x in list(df.index.values):
#     values.append([df.loc[x, 'K'], df.loc[x, 'iv']])

# df_test = pd.DataFrame(data = values, columns = ['X', 'Y'])

@app.callback(Output('my-graph', 'figure'), [Input('selected-value', 'value')])
# def bar_trace(df):
#     return go.Ohlc(
#         x=df.index,
#         open=df["open"],
#         high=df["high"],
#         low=df["low"],
#         close=df["close"],
#         increasing=dict(line=dict(color="#888888")),
#         decreasing=dict(line=dict(color="#888888")),
#         showlegend=False,
#         name="bar",
#     )
#
#
# def colored_bar_trace(df):
#     return go.Ohlc(
#         x=df.index,
#         open=df["open"],
#         high=df["high"],
#         low=df["low"],
#         close=df["close"],
#         showlegend=False,
#         name="colored bar",
#     )

def update_figure(selected):
    text = {"2D_option": "2D Graph", "3D_option": "3D Graph"}
    trace = []
    strike = []
    K = np.arange(2000, 4000, 100)
    for k in K:
        strike.append(k)

    for type in selected:
        # trace.append(go.Scatter(x=df["K"], y=df["iv"], name=text[type], mode='lines',
        #                        marker={'size': 8, "opacity": 0.6, "line": {'width': 0.5}}, ))
        x = np.arange(2000, 4000, 100)

        trace.append(go.Scatter(x=strike, y=calc_iv(), name=text[type], mode='lines',
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
