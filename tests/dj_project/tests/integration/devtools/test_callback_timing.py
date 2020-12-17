from time import sleep
import requests

import pytest

import dash_html_components as html
from dash.dependencies import Output, Input

from dash.testing.plugin import *
from .. import BaseDashView


@pytest.mark.skip
def test_dvct001_callback_timing(dash_duo):
    class DashView(BaseDashView):
        def __init__(self, **kwargs):
            super(DashView, self).__init__(**kwargs)

            self.dash._dev_tools.ui = True
            self.dash._dev_tools.serve_dev_bundles = True

            self.dash.layout = html.Div()

            self.dash.callback(Output("x", "p"), Input("y", "q"))(self.x)

        def x(self, y):
            self.request.record_timing("pancakes", 1.23)
            sleep(0.5)
            return y

    dash_duo.start_server(DashView, debug=True, use_reloader=False, use_debugger=True)

    response = requests.post(
        dash_duo.server_url + "/_dash-update-component",
        json={
            "output": "x.p",
            "outputs": {"id": "x", "property": "p"},
            "inputs": [{"id": "y", "property": "q", "value": 9}],
            "changedPropIds": ["y.q"],
        },
    )

    # eg 'Server-Timing': '__dash_server;dur=505, pancakes;dur=1230'
    assert "Server-Timing" in response.headers
    st = response.headers["Server-Timing"]
    times = {k: int(float(v)) for k, v in [p.split(";dur=") for p in st.split(", ")]}
    assert "__dash_server" in times
    assert times["__dash_server"] >= 500  # 0.5 sec wait
    assert "pancakes" in times
    assert times["pancakes"] == 1230
