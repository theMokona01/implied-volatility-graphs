# Import required libraries
import os
import datetime as dt

import numpy as np
import pandas as pd
import flask
import dash
from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go
import pprint
import json
import requests
from py_vollib.black_scholes_merton.implied_volatility import implied_volatility

# Setup app
app = dash.Dash(__name__)
server = app.server

external_css = ["https://fonts.googleapis.com/css?family=Overpass:300,300i",
                "https://cdn.rawgit.com/plotly/dash-app-stylesheets/dab6f937fd5548cebf4c6dc7e93a10ac438f5efb/dash-technical-charting.css"]

for css in external_css:
    app.css.append_css({"external_url": css})

if 'DYNO' in os.environ:
    app.scripts.append_script({
        'external_url': 'https://cdn.rawgit.com/chriddyp/ca0d8f02a1659981a0ea7f013a378bbd/raw/e79f3f789517deec58f41251f7dbb6bee72c44ab/plotly_ga.js'
    })

graph_list = ["2D", "3D"]
call_or_put_list = ["Call", "Put"]

graphs = [dict(label=str(g), value=str(g)) for g in graph_list]
call_put = [dict(label=str(cp).capitalize(), value=str(cp).capitalize()) for cp in call_or_put_list]

# Make app layout
app.layout = html.Div(
    [
        html.Div([
            html.Img(
                src="https://i.ibb.co/tBRB14X/iv.jpg", alt="Implied Volatility Rate", height="100", width="auto",
                className='two columns',
                style={
                    'height': '100',
                    'width': '160',
                    'float': 'left',
                    'position': 'relative',
                },
            ),
            html.H1(
                '3D Volatility Surface Explorer',
                className='eight columns',
                style={'text-align': 'center'}
            ),
            html.Img(
                src="https://s3-us-west-1.amazonaws.com/plotly-tutorials/logo/new-branding/dash-logo-by-plotly-stripe.png",
                className='two columns',
                style={
                    'height': '60',
                    'width': '135',
                    'float': 'right',
                    'position': 'relative',
                },
            ),
        ],
            className='row'
        ),
        html.Hr(style={'margin-top': '0.1em', 'margin-bottom': '3em'}),
        html.H2('General'),
        html.Div([
            html.Div([
                html.Label('· Option settings:'),
                dcc.RadioItems(
                    id='option_selector',
                    options=call_put,
                    value='Call',
                    labelStyle={'display': 'inline-block'},
                ),
            ],
                className='two columns',
            ),

        ],
            className='row',
            style={'margin-bottom': '10'}
        ),
        html.Hr(style={'margin-top': '0.1em', 'margin-bottom': '0.1em'}),
       html.H2('Input Parameters'),

        html.Div([
            html.Label('· Underlying (s) :'),
            dcc.Input(
                id='s_input',
                placeholder='s',
                type='number',
                value='3000',
                style={'width': '75'}
            )
        ],
            style={'display': 'inline-block'}

        ),
        html.Div([
            html.Label('· Interest Rate (r) :'),
            dcc.Input(
                id='r_input',
                placeholder='r',
                type='number',
                value='0.02',
                style={'width': '25'}
            )
        ],
            style={'display': 'inline-block'}
        ),
        html.Div([
            html.Label('· Dividend Rate (q) :'),
            dcc.Input(
                id='q_input',
                placeholder='q',
                type='number',
                value='0.02',
                style={'width': '25'}
            )
        ],
            style={'display': 'inline-block'}
        ),
        html.Hr(style={'margin-top': '1em', 'margin-bottom': '1.5em'}),
        html.H2('Chart Display (3D Only)'),
        html.Div([

            html.Div([
                dcc.RadioItems(
                    id='log_selector',
                    options=[
                        {'label': 'Log surface', 'value': 'log'},
                        {'label': 'Linear surface', 'value': 'linear'},
                    ],
                    value='log',
                    labelStyle={'display': 'inline-block'}
                ),
                dcc.Checklist(
                    id='graph_toggles',
                    options=[
                        {'label': 'Flat shading', 'value': 'flat'},
                        {'label': 'Discrete contour', 'value': 'discrete'},
                        {'label': 'Error bars', 'value': 'box'},
                        {'label': 'Lock camera', 'value': 'lock'}
                    ],
                    value=['flat', 'box', 'lock'],
                    labelStyle={'display': 'inline-block'}
                )
            ],
                className='six columns'
            ),
        ],
            className='row'
        ),
        html.Div([
            dcc.Graph(id='iv_surface', animate=True, style={'max-height': '600', 'height': '60vh'}),
             dcc.Interval(
            id='interval-component',
            interval=10*1000, # updates once every 10 seconds
            n_intervals=0
        )
        ],
            className='row',
            style={'margin-bottom': '20'}
        ),
        html.Div([
            html.Div([
                dcc.Graph(id='iv_heatmap', style={'max-height': '350', 'height': '35vh'}),
            ],
                className='five columns'
            ),
            html.Div([
                dcc.Graph(id='iv_scatter', style={'max-height': '350', 'height': '35vh'}),
            ],
                className='seven columns'
            ),
            html.Div([
                dcc.Graph(id='2d_graph', style={'max-height': '450', 'height': '35vh'}),
            ],
            )
        ],
            className='row'
        ),
        # Temporary hack for live dataframe caching
        # 'hidden' set to 'loaded' triggers next callback
        html.P(
            hidden='',
            id='filtered_container',
            style={'display': 'none'}
        )
    ],
    style={
        'width': '85%',
        'max-width': '1200',
        'margin-left': 'auto',
        'margin-right': 'auto',
        'font-family': 'overpass',
        'background-color': '#F3F3F3',
        'padding': '40',
        'padding-top': '20',
        'padding-bottom': '20',
    },
)

@app.callback([Output('iv_surface', 'figure'),
               Output('2d_graph', 'figure'),
              Output('iv_scatter', 'figure'),
              Output('iv_heatmap', 'figure')],
              [Input('log_selector', 'value'),
               Input('graph_toggles', 'value'),
               Input('option_selector', 'value'),
               Input('s_input', 'value'),
               Input('r_input', 'value'),
               Input('q_input', 'value'),
               Input('interval-component', 'n_intervals')],
              [State('graph_toggles', 'value'),
               State('iv_surface', 'relayoutData')])
def multi_graph(log_selector, graph_toggles, option, s, r, q, n,
                      graph_toggles_state, iv_surface_layout):

    return graph_3d(log_selector, graph_toggles, option, s, r, q, graph_toggles_state, iv_surface_layout), graph_2d(s, r ,q), make_scatter_plot(option, s, r, q), make_heatmap_plot(option, s, r, q)

def graph_3d(log_selector, graph_toggles, option, s, r, q,
                      graph_toggles_state, iv_surface_layout):

    df = calc_iv(option, s, r, q, "3D")

    if 'flat' in graph_toggles:
        flat_shading = True
    else:
        flat_shading = False

    trace1 = {
        "type": "mesh3d",
        'x': update_strike(df),
        'y': df["IV"],
        'z': df["Time_Expiration"],
        'intensity': df["Time_Expiration"],
        'autocolorscale': False,
        "colorscale": [
            [0, "rgb(244,236,21)"], [0.3, "rgb(249,210,41)"], [0.4, "rgb(134,191,118)"], [
                0.5, "rgb(37,180,167)"], [0.65, "rgb(17,123,215)"], [1, "rgb(54,50,153)"],
        ],
        "lighting": {
            "ambient": 1,
            "diffuse": 0.9,
            "fresnel": 0.5,
            "roughness": 0.9,
            "specular": 2
        },
        "flatshading": flat_shading,
        "reversescale": True,
    }

    layout = {
        "title": "{} Volatility Surface | {}".format(option, str(dt.datetime.now())),
        'margin': {
            'l': 10,
            'r': 10,
            'b': 10,
            't': 60,
        },
        'paper_bgcolor': '#FAFAFA',
        "hovermode": "closest",
        "scene": {
            "aspectmode": "manual",
            "aspectratio": {
                "x": 2,
                "y": 2,
                "z": 1
            },
            'camera': {
                'up': {'x': 0, 'y': 0, 'z': 1},
                'center': {'x': 0, 'y': 0, 'z': 0},
                'eye': {'x': 1, 'y': 1, 'z': 0.5},
            },
            "xaxis": {
                "title": "Strike ($)",
                "showbackground": True,
                "backgroundcolor": "rgb(230, 230,230)",
                "gridcolor": "rgb(255, 255, 255)",
                "zerolinecolor": "rgb(255, 255, 255)"
            },
            "yaxis": {
                "title": "Expiry (days)",
                "showbackground": True,
                "backgroundcolor": "rgb(230, 230,230)",
                "gridcolor": "rgb(255, 255, 255)",
                "zerolinecolor": "rgb(255, 255, 255)"
            },
            "zaxis": {
                "rangemode": "tozero",
                "title": "IV (σ)",
                "type": log_selector,
                "showbackground": True,
                "backgroundcolor": "rgb(230, 230,230)",
                "gridcolor": "rgb(255, 255, 255)",
                "zerolinecolor": "rgb(255, 255, 255)"
            }
        },
    }

    if (iv_surface_layout is not None and 'lock' in graph_toggles_state):

        try:
            up = iv_surface_layout['scene']['up']
            center = iv_surface_layout['scene']['center']
            eye = iv_surface_layout['scene']['eye']
            layout['scene']['camera']['up'] = up
            layout['scene']['camera']['center'] = center
            layout['scene']['camera']['eye'] = eye
        except:
            pass

    data = [trace1]
    figure = dict(data=data, layout=layout)
    return figure

def graph_2d(s, r, q):

    df_call = calc_iv("call", s, r, q, "2D")
    call_trace = [(go.Scatter(x=update_strike(df_call), y=df_call["IV"], name="Call", mode='lines',
                            marker={'size': 8, "opacity": 0.6, "line": {'width': 0.5}}, ))]
    df_put = calc_iv("put", s, r, q, "2D")
    put_trace = [(go.Scatter(x=update_strike(df_put), y=df_put["IV"], name="Put", mode='lines',
                              marker={'size': 8, "opacity": 0.6, "line": {'width': 0.5}}, ))]

    trace = call_trace + put_trace

    return {"data": trace,
            "layout": go.Layout(colorway=['#fdae61', '#abd9e9', '#2c7bb6'],
                                yaxis={"title": "IV (σ)"}, xaxis={"title": "Strike ($)"})}

def make_heatmap_plot(option, s, r, q):

    df = calc_iv(option, s, r, q, "3D")
    trace1 = {
        "type": "contour",
        'x': update_strike(df),
        'y': df["IV"],
        'z': df["Time_Expiration"],
        'connectgaps': True,
        'line': {'smoothing': '1'},
        'contours': {'coloring': 'heatmap'},
        'autocolorscale': False,
        "colorscale": [
            [0, "rgb(244,236,21)"], [0.3, "rgb(249,210,41)"], [0.4, "rgb(134,191,118)"],
            [0.5, "rgb(37,180,167)"], [0.65, "rgb(17,123,215)"], [1, "rgb(54,50,153)"],
        ],
        # Add colorscale log
        "reversescale": True,
    }

    layout = {
        'margin': {
            'l': 60,
            'r': 10,
            'b': 60,
            't': 10,
        },
        'paper_bgcolor': '#FAFAFA',
        "hovermode": "closest",
        "xaxis": {
            'range': [],
            "title": "Strike ($)",
        },
        "yaxis": {
            'range': [],
            "title": "Expiry (days)",
        },
    }

    data = [trace1]
    figure = dict(data=data, layout=layout)
    return figure


def make_scatter_plot(option, s, r, q):

    df = calc_iv(option, s, r, q, "2D")

    trace = {
        "type": 'scatter',
        "shading" : 'contour',
        'mode': 'markers',
        'x': update_strike(df),
        'y': df["IV"],
        'boxpoints': 'outliers',
        'marker': {'color': '#B22222', 'opacity': 0.2}
    }



    layout = {
        'margin': {
            'l': 60,
            'r': 10,
            'b': 60,
            't': 10,
        },
        'paper_bgcolor': '#FAFAFA',
        "hovermode": "closest",
        "xaxis": {
            "title": "Strike ($)",
        },
        "yaxis": {
            "rangemode": "tozero",
            "title": "IV (σ)",
        },
    }

    data = [trace]
    figure = dict(data=data, layout=layout)
    return figure

def calc_iv(selected_option, selected_s, selected_r, selected_q, selected_graph):
    df = pd.DataFrame()
    prior_settle = []
    strike_price = []
    try:
        call_or_put = str(selected_option).lower()
        cme_group_url = "https://www.cmegroup.com/CmeWS/mvc/Quotes/Option/138/G/U9/ALL?optionProductId=138"
        try:
            request = requests.get(cme_group_url + "&strikeRange=ALL")
            request_json = json.loads(request.content.decode('utf-8'))
        except ConnectionError as e:
            print(e)
    except Exception as e:
        print(e)
    try:
        for strike in request_json["optionContractQuotes"]:
            str(strike).replace("\'", "\"")
            strike_price.append(float(strike["strikePrice"]))

        for price in request_json["optionContractQuotes"]:
            str(price).replace("\'", "\"")
            prior_settle.append(float(price[call_or_put]["priorSettle"]))
    except Exception as e:
        print(e)

    s = float(selected_s)
    r = float(selected_r)
    q = float(selected_q)
    flag = 'c'
    counter = 0
    iv = []
    try:
        # 2d option
        if selected_graph.upper() == "2D":
            t = 0.1
            for price in prior_settle:
                iv.append(implied_volatility(price, s, strike_price[counter], t, r, q, flag))
                counter = counter + 1

            df["Strike"] = strike_price #x-axis
            df["IV"] = iv #y-axis
            return df

        #3d option
        if selected_graph.upper() == "3D":
            t = np.arange(.1,1,.1)
            time_exp = []
            strike_3d = []
            for curr_t in t:
                iv.append(implied_volatility(prior_settle[counter], s, strike_price[counter], t[counter], r, q, flag))
                time_exp.append(t[counter])
                strike_3d.append(strike_price[counter])
                counter = counter + 1

            df["Strike"] = strike_3d #x-axis
            df["IV"] = iv #y-axis
            df["Time_Expiration"] = time_exp #z-axis
            return df

    except Exception as e:
        print(e)

def update_strike(df):
    updated_strike = []
    for curr_strike in df["Strike"].values:
        updated_strike.append(float(curr_strike) / 100)
    return updated_strike

if __name__ == '__main__':
    app.server.run(debug=True, threaded=True)
