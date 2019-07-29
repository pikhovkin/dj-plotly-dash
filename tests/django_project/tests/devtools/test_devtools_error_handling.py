# -*- coding: UTF-8 -*-
import dash_html_components as html
import dash_core_components as dcc

import dash
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate

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
    @property
    def devtools_error_count_locator(self):
        return ".test-devtools-error-count"

    def test_dveh_python_errors(self):
        class DashDvehPythonErrors(DashView):
            dash_name = 'dveh_python_errors'
            dash_components = {html.__name__}

            def __init__(self, **kwargs):
                super(DashDvehPythonErrors, self).__init__(**kwargs)

                self.dash._dev_tools.ui = True
                self.dash._dev_tools.serve_dev_bundles = True

                self.dash.layout = html.Div(
                    [
                        html.Button(id="python", children="Python exception", n_clicks=0),
                        html.Div(id="output"),
                    ]
                )
                self.dash.callback(Output("output", "children"), [Input("python", "n_clicks")])(self.update_output)

            def update_output(self, n_clicks):
                if n_clicks == 1:
                    1 / 0
                elif n_clicks == 2:
                    raise Exception("Special 2 clicks exception")

        self.open('dash/{}/'.format(DashDvehPythonErrors.dash_name))

        self.find_element("#python").click()
        self.wait_for_text_to_equal(self.devtools_error_count_locator, "1")

        self.find_element(".test-devtools-error-toggle").click()

        self.find_element(".test-devtools-error-toggle").click()
        self.find_element("#python").click()

        self.wait_for_text_to_equal(self.devtools_error_count_locator, "2")

        self.find_element(".test-devtools-error-toggle").click()

    def test_dveh_prevent_update_not_in_error_msg(self):
        class DashDvehPreventUpdateNotInErrorMsg(DashView):
            dash_name = 'dveh_prevent_update_not_in_error_msg'
            dash_components = {html.__name__}

            def __init__(self, **kwargs):
                super(DashDvehPreventUpdateNotInErrorMsg, self).__init__(**kwargs)

                self.dash._dev_tools.ui = True
                self.dash._dev_tools.serve_dev_bundles = True

                self.dash.layout = html.Div(
                    [
                        html.Button(id="python", children="Prevent update", n_clicks=0),
                        html.Div(id="output"),
                    ]
                )
                self.dash.callback(Output("output", "children"), [Input("python", "n_clicks")])(self.update_output)

            def update_output(self, n_clicks):
                if n_clicks == 1:
                    raise PreventUpdate
                if n_clicks == 2:
                    raise Exception("An actual python exception")

                return "button clicks: {}".format(n_clicks)

        self.open('dash/{}/'.format(DashDvehPreventUpdateNotInErrorMsg.dash_name))

        for _ in range(3):
            self.find_element("#python").click()

        assert (
            self.find_element("#output").text == "button clicks: 3"
        ), "the click counts correctly in output"

        # two exceptions fired, but only a single exception appeared in the UI:
        # the prevent default was not displayed
        self.wait_for_text_to_equal(self.devtools_error_count_locator, "1")

