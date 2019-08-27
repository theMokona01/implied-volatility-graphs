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

import pprint
import json
import requests
#from data_fetcher import get_time_delta, get_raw_data, get_filtered_data
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
strike_range_list = ["ALL", "ATM", "ACTIVE"]
call_or_put_list = ["calls", "puts"]

graphs = [dict(label=str(g), value=str(g)) for g in graph_list]
strike_range = [dict(label=str(sr).capitalize(), value=str(sr).capitalize()) for sr in strike_range_list]
call_put = [dict(label=str(cp).capitalize(), value=str(cp).capitalize()) for cp in call_or_put_list]

df_iv = pd.DataFrame()

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
                html.Label('· Graph type:'),
                dcc.RadioItems(
                    id='graph_dropdown',
                    options=graphs,
                    value='3D',
                    labelStyle={'display': 'inline-block'},
                ),

            ],
                className='two columns',
            ),
            html.Div([
                html.Label('· Strike range:'),
                dcc.RadioItems(
                    id='strike_dropdown',
                    options=strike_range,
                    value='All',
                    labelStyle={'display': 'inline-block'},
                ),

            ],
                className='two columns',
            ),
            html.Div([
                html.Label('· Option settings:'),
                dcc.RadioItems(
                    id='option_selector',
                    options=call_put,
                    value='Calls',
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
            dcc.Graph(id='iv_surface', style={'max-height': '600', 'height': '60vh'}),
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

# Make main surface plot
@app.callback(Output('iv_surface', 'figure'),
              [Input('log_selector', 'value'),
               Input('graph_toggles', 'value'),
               Input('strike_dropdown', 'value'),
               Input('option_selector', 'value'),
               Input('s_input', 'value'),
               Input('r_input', 'value'),
               Input('q_input', 'value'),
               Input('graph_dropdown', 'value') ],
              [State('graph_toggles', 'value'),
               State('iv_surface', 'relayoutData')])
def make_surface_plot(log_selector, graph_toggles, strike, option, s, r, q, graph_type,
                      graph_toggles_state, iv_surface_layout):

    if graph_type.upper() == "3D":
        calc_iv(strike, option, s, r, q, graph_type)

        if 'flat' in graph_toggles:
            flat_shading = True
        else:
            flat_shading = False

        trace1 = {
            "type": "mesh3d",
            'x': df_iv["Strike"],
            'y': df_iv["IV"],
            'z': df_iv["Time_Expiration"],
            'intensity': df_iv["Time_Expiration"],
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
            "title": "{} Volatility Surface | {}".format(strike, str(dt.datetime.now())),
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


# # Make side heatmap plot
# @app.callback(Output('iv_heatmap', 'figure'),
#               [Input('filtered_container', 'hidden'),
#                Input('strike_dropdown', 'value'),
#                Input('graph_toggles', 'value')],
#               [State('graph_toggles', 'value'),
#                State('iv_heatmap', 'relayoutData')])
# def make_surface_plot(hidden, strike, graph_toggles,
#                       graph_toggles_state, iv_heatmap_layout):
#
#
#     if hidden == 'loaded':
#
#         if 'discrete' in graph_toggles:
#             shading = 'contour'
#         else:
#             shading = 'heatmap'
#
#         trace1 = {
#             "type": "contour",
#             'x': df_iv["Strike"],
#             'y': df_iv["IV"],
#             'z': df_iv["Time_Expiration"],
#             'connectgaps': True,
#             'line': {'smoothing': '1'},
#             'contours': {'coloring': shading},
#             'autocolorscale': False,
#             "colorscale": [
#                 [0, "rgb(244,236,21)"], [0.3, "rgb(249,210,41)"], [0.4, "rgb(134,191,118)"],
#                 [0.5, "rgb(37,180,167)"], [0.65, "rgb(17,123,215)"], [1, "rgb(54,50,153)"],
#             ],
#             # Add colorscale log
#             "reversescale": True,
#         }
#
#         layout = {
#             'margin': {
#                 'l': 60,
#                 'r': 10,
#                 'b': 60,
#                 't': 10,
#             },
#             'paper_bgcolor': '#FAFAFA',
#             "hovermode": "closest",
#             "xaxis": {
#                 'range': [],
#                 "title": "Strike ($)",
#             },
#             "yaxis": {
#                 'range': [],
#                 "title": "Expiry (days)",
#             },
#         }
#
#         if (iv_heatmap_layout is not None and 'lock' in graph_toggles_state):
#
#             try:
#                 x_range_left = iv_heatmap_layout['xaxis.range[0]']
#                 x_range_right = iv_heatmap_layout['xaxis.range[1]']
#                 layout['xaxis']['range'] = [x_range_left, x_range_right]
#             except:
#                 pass
#
#             try:
#                 y_range_left = iv_heatmap_layout['yaxis.range[0]']
#                 y_range_right = iv_heatmap_layout['yaxis.range[1]']
#                 layout['yaxis']['range'] = [x_range_left, x_range_right]
#             except:
#                 pass
#
#         data = [trace1]
#         figure = dict(data=data, layout=layout)
#         return figure
#
#
# Make side scatter plot

@app.callback(Output('iv_scatter', 'figure'),
              [Input('strike_dropdown', 'value'),
               Input('option_selector', 'value'),
               Input('s_input', 'value'),
               Input('r_input', 'value'),
               Input('q_input', 'value'),
               Input('graph_dropdown', 'value'),
               Input('graph_toggles', 'value')],
              [State('graph_toggles', 'value'),
               State('iv_scatter', 'relayoutData')])
def make_scatter_plot(strike, option, s, r, q, graph_type, graph_toggles,
                      graph_toggles_state, iv_scatter_layout):

    if graph_type.upper() == "2D":
        calc_iv(strike, option, s, r, q, graph_type)

        if 'discrete' in graph_toggles:
            shading = 'contour'
        else:
            shading = 'heatmap'

        if 'box' in graph_toggles:
            typ = 'box'
        else:
            typ = 'scatter'

        trace1 = {
            "type": 'scatter',
            'mode': 'markers',
            'x': df_iv["Strike"],
            'y': df_iv["IV"],
            'boxpoints': 'outliers',
            'marker': {'color': '#32399F', 'opacity': 0.2}
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
                "title": "Strike",
            },
            "yaxis": {
                "rangemode": "tozero",
                "title": "Implied Volatility",
            },
        }

        if (iv_scatter_layout is not None and 'lock' in graph_toggles_state):

            try:
                x_range_left = iv_scatter_layout['xaxis.range[0]']
                x_range_right = iv_scatter_layout['xaxis.range[1]']
                layout['xaxis']['range'] = [x_range_left, x_range_right]
            except:
                pass

            try:
                y_range_left = iv_scatter_layout['yaxis.range[0]']
                y_range_right = iv_scatter_layout['yaxis.range[1]']
                layout['yaxis']['range'] = [x_range_left, x_range_right]
            except:
                pass

        data = [trace1]
        figure = dict(data=data, layout=layout)
        return figure

def calc_iv(selected_strike, selected_option, selected_s, selected_r, selected_q, selected_graph):
    df_iv.drop(df_iv.index, inplace=True)
    prior_settle = []
    strike_price = []
    try:
        strike = str(selected_strike).upper()
        if strike == "ACTIVE":
            strike = strike.capitalize()

        call_or_put = str(selected_option).lower()
        if call_or_put == "calls":
            call_or_put = "call"
        else:
            call_or_put = "put"

        cme_group_url = "https://www.cmegroup.com/CmeWS/mvc/Quotes/Option/138/G/U9/ALL?optionProductId=138"

        try:
            request = requests.get(cme_group_url + "&strikeRange=" + strike)
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
    if call_or_put == "put":
        flag = 'p'
    counter = 0
    iv = []
    try:
        # 2d option
        if selected_graph.upper() == "2D":
            t = 0.1
            for price in prior_settle:
                iv.append(implied_volatility(price, s, strike_price[counter], t, r, q, flag))
                counter = counter + 1

            df_iv["Strike"] = strike_price #x-axis
            df_iv["IV"] = iv #y-axis
            df_iv.to_csv("2D.csv")

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

            df_iv["Strike"] = strike_3d #x-axis
            df_iv["IV"] = iv #y-axis
            df_iv["Time_Expiration"] = time_exp #z-axis
            df_iv.to_csv("3D.csv")

    except Exception as e:
        print(e)

if __name__ == '__main__':
    app.server.run(debug=True, threaded=True)
