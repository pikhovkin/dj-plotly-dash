# -*- coding: UTF-8 -*-
from django.conf import settings
import dash_html_components as html
import dash_core_components as dcc

from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate
from selenium.common.exceptions import TimeoutException

from tests import DashView
from tests.IntegrationTests import IntegrationTests, TIMEOUT


class DashPythonErrors(DashView):
    dash_components = {html.__name__}

    def __init__(self, **kwargs):
        super(DashPythonErrors, self).__init__(**kwargs)

        self.dash._dev_tools.ui = True
        # self.dash._dev_tools.props_check = True
        self.dash._dev_tools.serve_dev_bundles = True
        # self.dash._dev_tools.silence_routes_logging = True
        # self.dash._dev_tools.prune_errors = True

        self.dash.layout = html.Div(
            [
                html.Button(id="python", children="Python exception", n_clicks=0),
                html.Div(id="output"),
            ]
        )
        self.dash.callback(Output("output", "children"), [Input("python", "n_clicks")])(self.update_output)

    def update_output(self, n_clicks):
        if n_clicks == 1:
            return self.bad_sub()
        elif n_clicks == 2:
            raise Exception("Special 2 clicks exception")

    def bad_sub(self):
        return 1 / 0


class Tests(IntegrationTests):
    @property
    def devtools_error_count_locator(self):
        return ".test-devtools-error-count"

    def test_dveh_python_errors(self):
        settings.DEBUG = True

        class DashDvehPythonErrors(DashPythonErrors):
            dash_name = 'dveh_python_errors'

        self.open('dash/{}/'.format(DashDvehPythonErrors.dash_name))

        self.find_element("#python").click()
        self.wait_for_text_to_equal(self.devtools_error_count_locator, "1")

        self.find_element(".test-devtools-error-toggle").click()

        self.find_element(".test-devtools-error-toggle").click()
        self.find_element("#python").click()

        self.wait_for_text_to_equal(self.devtools_error_count_locator, "2")

        self.find_element(".test-devtools-error-toggle").click()

        # the top (first) error is the most recent one - ie from the second click
        error0 = self.get_error_html(0)
        # print error0
        # user part of the traceback shown by default
        assert 'in update_output' in error0
        assert 'Special 2 clicks exception' in error0
        assert 'in bad_sub' not in error0
        # dash and flask part of the traceback not included
        # assert '%% callback invoked %%' not in error0
        # assert 'self.wsgi_app' not in error0
        #
        error1 = self.get_error_html(1)
        print error1
        assert 'in update_output' in error1
        assert 'in bad_sub' in error1
        assert 'ZeroDivisionError' in error1
        # assert '%% callback invoked %%' not in error1
        # assert 'self.wsgi_app' not in error1

        settings.DEBUG = False

    def test_dveh_long_python_errors(self):
        settings.DEBUG = True

        class DashDvehLongPythonErrors(DashPythonErrors):
            dash_name = 'dveh_long_python_errors'

        self.open('dash/{}/'.format(DashDvehLongPythonErrors.dash_name))

        self.find_element("#python").click()
        self.find_element("#python").click()
        self.wait_for_text_to_equal(self.devtools_error_count_locator, "2")

        self.find_element(".test-devtools-error-toggle").click()

        error0 = self.get_error_html(0)
        assert 'in update_output' in error0
        assert 'Special 2 clicks exception' in error0
        assert 'in bad_sub' not in error0
        # dash and flask part of the traceback ARE included
        # since we set dev_tools_prune_errors=False
        assert '%% callback invoked %%' in error0
        # assert 'self.wsgi_app' in error0

        error1 = self.get_error_html(1)
        assert 'in update_output' in error1
        assert 'in bad_sub' in error1
        assert 'ZeroDivisionError' in error1
        assert '%% callback invoked %%' in error1
        # assert 'self.wsgi_app' in error1

        settings.DEBUG = False

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

    def test_dveh_validation_errors_in_place(self):
        class DashDvehValidationErrorsInPlace(DashView):
            dash_name = 'dveh_validation_errors_in_place'
            dash_components = {html.__name__, dcc.__name__}

            def __init__(self, **kwargs):
                super(DashDvehValidationErrorsInPlace, self).__init__(**kwargs)

                self.dash._dev_tools.ui = True
                self.dash._dev_tools.serve_dev_bundles = True

                self.dash.layout = html.Div(
                    [
                        html.Button(id="button", children="update-graph", n_clicks=0),
                        dcc.Graph(id="output", figure={"data": [{"y": [3, 1, 2]}]}),
                    ]
                )
                self.dash.callback(Output("output", "animate"), [Input("button", "n_clicks")])(self.update_output)

            def update_output(self, n_clicks):
                if n_clicks == 1:
                    return n_clicks


        self.open('dash/{}/'.format(DashDvehValidationErrorsInPlace.dash_name))

        self.find_element("#button").click()
        with self.assertRaises(TimeoutException):
            self.wait_for_text_to_equal(self.devtools_error_count_locator, "1")

        # self.find_element(".test-devtools-error-toggle").click()

    def test_dveh_validation_errors_creation(self):
        class DashDvehValidationErrorsCreation(DashView):
            dash_name = 'dveh_validation_errors_creation'
            dash_components = {html.__name__, dcc.__name__}

            def __init__(self, **kwargs):
                super(DashDvehValidationErrorsCreation, self).__init__(**kwargs)

                self.dash._dev_tools.ui = True
                self.dash._dev_tools.serve_dev_bundles = True

                self.dash.layout = html.Div(
                    [
                        html.Button(id="button", children="update-graph", n_clicks=0),
                        html.Div(id="output"),
                    ]
                )
                self.dash.callback(Output("output", "children"), [Input("button", "n_clicks")])(self.update_output)

            def update_output(self, n_clicks):
                if n_clicks == 1:
                    return dcc.Graph(
                        id="output", animate=0, figure={"data": [{"y": [3, 1, 2]}]}
                    )

        self.open('dash/{}/'.format(DashDvehValidationErrorsCreation.dash_name))

        self.wait_for_element_by_id("button").click()
        with self.assertRaises(TimeoutException):
            self.wait_for_text_to_equal(self.devtools_error_count_locator, "1")

        # self.find_element(".test-devtools-error-toggle").click()

    def test_dveh_multiple_outputs(self):
        class DashDvehMultipleOutputs(DashView):
            dash_name = 'dveh_multiple_outputs'
            dash_components = {html.__name__}

            def __init__(self, **kwargs):
                super(DashDvehMultipleOutputs, self).__init__(**kwargs)

                self.dash._dev_tools.ui = True
                self.dash._dev_tools.serve_dev_bundles = True

                self.dash.layout = html.Div(
                    [
                        html.Button(
                            id="multi-output",
                            children="trigger multi output update",
                            n_clicks=0,
                        ),
                        html.Div(id="multi-1"),
                        html.Div(id="multi-2"),
                    ]
                )
                self.dash.callback(
                    [Output("multi-1", "children"), Output("multi-2", "children")],
                    [Input("multi-output", "n_clicks")],
                )(self.update_output)

            def update_output(self, n_clicks):
                if n_clicks == 0:
                    return [
                        "Output 1 - {} Clicks".format(n_clicks),
                        "Output 2 - {} Clicks".format(n_clicks),
                    ]
                else:
                    n_clicks / 0

        self.open('dash/{}/'.format(DashDvehMultipleOutputs.dash_name))

        self.find_element("#multi-output").click()
        self.wait_for_text_to_equal(self.devtools_error_count_locator, "1")

        self.find_element(".test-devtools-error-toggle").click()
