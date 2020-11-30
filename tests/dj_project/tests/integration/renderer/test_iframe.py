from multiprocessing import Value

import dash
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate

import dash_html_components as html

from dash.testing.plugin import *
from .. import BaseDashView


def test_rdif001_sandbox_allow_scripts(dash_duo, settings):
    settings.X_FRAME_OPTIONS = 'allow-from *'

    app = dash.Dash(__name__)
    call_count = Value("i")

    N_OUTPUTS = 50

    app.layout = html.Div([
        html.Button("click me", id="btn"),
    ] + [html.Div(id="output-{}".format(i)) for i in range(N_OUTPUTS)])

    @app.callback(
        [Output("output-{}".format(i), "children") for i in range(N_OUTPUTS)],
        [Input("btn", "n_clicks")]
    )
    def update_output(n_clicks):
        if n_clicks is None:
            raise PreventUpdate

        call_count.value += 1
        return ["{}={}".format(i, i + n_clicks) for i in range(N_OUTPUTS)]

    # @app.server.after_request
    # def apply_cors(response):
    #     response.headers["Access-Control-Allow-Origin"] = "*"
    #     response.headers["Access-Control-Allow-Headers"] = "Origin, X-Requested-With, Content-Type, Accept, Authorization"
    #     return response

    class DashView(BaseDashView):
        dash = app

    dash_duo.start_server(DashView)

    iframe = """
        <!DOCTYPE html>
    <html>
    <iframe src="{0}" sandbox="allow-same-origin allow-scripts">
    </iframe>
    </html>
    """

    html_content = iframe.format(dash_duo.server_url)

    dash_duo.driver.get("data:text/html;charset=utf-8," + html_content)

    dash_duo.driver.switch_to.frame(0)

    dash_duo.wait_for_element('#output-0')
    dash_duo.wait_for_element_by_id('btn').click()
    dash_duo.wait_for_element('#output-0').text == '0=1'

    assert len(dash_duo.get_logs()) != 0
