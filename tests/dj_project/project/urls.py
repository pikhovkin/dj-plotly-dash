from django.conf.urls import url, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    url(r'^dash/', include('dash.urls')),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)



# # UNCOMMENT FOR CHECKING
#
# from django.contrib.staticfiles.finders import get_finder
# f = get_finder('django.contrib.staticfiles.finders.FileSystemFinder')
# f.locations.append(('', settings.STATIC_ROOT),)
#
# import time
# from multiprocessing import Value, Lock
# import dash
# from dash.dependencies import Input, Output, State, ClientsideFunction, MATCH, ALL, ALLSMALLER
# import json
#
# import dash_core_components as dcc
# import dash_html_components as html
# import dash_table as dt
#
# from tests.integration import BaseDashView

########################################################
# app = dash.Dash(__name__)
# app.layout = html.Div()
#
#
# @app.callback([], [])
# def x():
#     print(42)
#     return 42
#
#
# class DashView(BaseDashView):
#     dash = app
#     dash._dev_tools.ui = True
#     dash._dev_tools.serve_dev_bundles = True
#     dash_suppress_callback_exceptions = False


##############################################

# app = dash.Dash(__name__, assets_folder="clientside_assets")
#
# app.layout = html.Div(
#     [
#         dcc.Input(id="input"),
#         html.Div(id="output-clientside"),
#         html.Div(id="output-serverside"),
#     ]
# )
#
# @app.callback(Output("output-serverside", "children"), [Input("input", "value")])
# def update_output(value):
#     return 'Server says "{}"'.format(value)
#
# app.clientside_callback(
#     ClientsideFunction(namespace="clientside", function_name="display"),
#     Output("output-clientside", "children"),
#     [Input("input", "value")],
# )
#
# class DashView(BaseDashView):
#     dash = app

###########################################################
#
# app = dash.Dash(__name__, assets_folder="clientside_assets")
#
# app.layout = html.Div(
#     [
#         html.Button("btn0", id="btn0"),
#         html.Button("btn1:0", id={"btn1": 0}),
#         html.Button("btn1:1", id={"btn1": 1}),
#         html.Button("btn1:2", id={"btn1": 2}),
#         html.Div(id="output-clientside", style={"font-family": "monospace"}),
#     ]
# )
#
# app.clientside_callback(
#     ClientsideFunction(namespace="clientside", function_name="triggered_to_str"),
#     Output("output-clientside", "children"),
#     [Input("btn0", "n_clicks"), Input({"btn1": ALL}, "n_clicks")],
# )
#
# class DashView(BaseDashView):
#     dash = app
#     dash._dev_tools.ui = True
#     dash._dev_tools.serve_dev_bundles = True

############################################################

# app = dash.Dash(__name__, assets_folder="clientside_assets")
#
# app.layout = html.Div(
#     [
#         dcc.Input(id="first", value=1),
#         dcc.Input(id="second", value=1),
#         dcc.Input(id="third", value=1),
#     ]
# )
#
# app.clientside_callback(
#     ClientsideFunction(
#         namespace="clientside", function_name="add1_no_update_at_11"
#     ),
#     [Output("second", "value"), Output("third", "value")],
#     [Input("first", "value")],
#     [State("second", "value"), State("third", "value")],
# )
#
# class DashView(BaseDashView):
#     dash = app
