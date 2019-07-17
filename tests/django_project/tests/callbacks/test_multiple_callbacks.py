import time
from multiprocessing import Value

import dash_html_components as html

import dash
from dash.dependencies import Input, Output

from tests.IntegrationTests import IntegrationTests, TIMEOUT


class DashView(dash.BaseDashView):
    def __init__(self, **kwargs):
        super(DashView, self).__init__(**kwargs)

        self.dash.config.routes_pathname_prefix = '/dash/{}/'.format(self.dash_name)

    def _dash_component_suites(self, request, *args, **kwargs):
        self.dash._generate_scripts_html()
        self.dash._generate_css_dist_html()

        return super(DashView, self)._dash_component_suites(request, *args, **kwargs)


class Tests(IntegrationTests):
    def test_called_multiple_times_and_out_of_order(self):
        class DashCalledMultipleTimesAndOutOfOrder(DashView):
            dash_name = 'called_multiple_times_and_out_of_order'
            dash_components = {html.__name__}

            call_count = Value("i", 0)

            def __init__(self, **kwargs):
                super(DashCalledMultipleTimesAndOutOfOrder, self).__init__(**kwargs)

                self.dash.layout = html.Div(
                    [html.Button(id="input", n_clicks=0), html.Div(id="output")]
                )

                self.dash.callback(Output("output", "children"), [Input("input", "n_clicks")])(self.update_output)

            def update_output(self, n_clicks):
                self.call_count.value = self.call_count.value + 1
                if n_clicks == 1:
                    time.sleep(1)
                return n_clicks

        self.open('dash/{}/'.format(DashCalledMultipleTimesAndOutOfOrder.dash_name))

        self.multiple_click("#input", clicks=3)

        time.sleep(3)

        assert DashCalledMultipleTimesAndOutOfOrder.call_count.value == 4, "get called 4 times"
        assert (
            self.find_element("#output").text == "3"
        ), "clicked button 3 times"

        rqs = self.redux_state_rqs
        assert len(rqs) == 1 and not rqs[0]["rejected"]
