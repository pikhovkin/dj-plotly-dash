# -*- coding: UTF-8 -*-
from multiprocessing import Value

import dash_html_components as html
import dash_core_components as dcc

from dash.dependencies import Input, Output, ClientsideFunction, State

from ..IntegrationTests import IntegrationTests
from .. import DashView as BaseDashView


class DashView(BaseDashView):
    dash_name = 'view'
    dash_components = {dcc.__name__, html.__name__}
    dash_assets_folder = 'clientside_assets'


class Tests(IntegrationTests):
    def test_simple_clientside_serverside_callback(self):
        class Dash(DashView):
            def __init__(self, **kwargs):
                super(Dash, self).__init__(**kwargs)

                self.dash.layout = html.Div(
                    [
                        dcc.Input(id="input"),
                        html.Div(id="output-clientside"),
                        html.Div(id="output-serverside"),
                    ]
                )

                self.dash.callback(
                    Output("output-serverside", "children"), [Input("input", "value")]
                )(self.update_output)
                self.dash.clientside_callback(
                    ClientsideFunction(namespace="clientside", function_name="display"),
                    Output("output-clientside", "children"),
                    [Input("input", "value")],
                )

            def update_output(self, value):
                return 'Server says "{}"'.format(value)

        self.open('dash/{}/'.format(Dash.dash_name))

        self.wait_for_text_to_equal("#output-serverside", 'Server says "None"')
        self.wait_for_text_to_equal(
            "#output-clientside", 'Client says "undefined"'
        )

        self.find_element("#input").send_keys("hello world")
        self.wait_for_text_to_equal(
            "#output-serverside", 'Server says "hello world"'
        )
        self.wait_for_text_to_equal(
            "#output-clientside", 'Client says "hello world"'
        )

    def test_chained_serverside_clientside_callbacks(self):
        class Dash(DashView):
            call_counts = {"divide": Value("i", 0), "display": Value("i", 0)}

            def __init__(self, **kwargs):
                super(Dash, self).__init__(**kwargs)

                self.dash.layout = html.Div(
                    [
                        html.Label("x"),
                        dcc.Input(id="x", value=3),
                        html.Label("y"),
                        dcc.Input(id="y", value=6),
                        # clientside
                        html.Label("x + y (clientside)"),
                        dcc.Input(id="x-plus-y"),
                        # server-side
                        html.Label("x+y / 2 (serverside)"),
                        dcc.Input(id="x-plus-y-div-2"),
                        # server-side
                        html.Div(
                            [
                                html.Label("Display x, y, x+y/2 (serverside)"),
                                dcc.Textarea(id="display-all-of-the-values"),
                            ]
                        ),
                        # clientside
                        html.Label("Mean(x, y, x+y, x+y/2) (clientside)"),
                        dcc.Input(id="mean-of-all-values"),
                    ]
                )

                self.dash.clientside_callback(
                    ClientsideFunction("clientside", "add"),
                    Output("x-plus-y", "value"),
                    [Input("x", "value"), Input("y", "value")],
                )
                self.dash.callback(
                    Output("x-plus-y-div-2", "value"), [Input("x-plus-y", "value")]
                )(self.divide_by_two)
                self.dash.callback(
                    Output("display-all-of-the-values", "value"),
                    [
                        Input("x", "value"),
                        Input("y", "value"),
                        Input("x-plus-y", "value"),
                        Input("x-plus-y-div-2", "value"),
                    ],
                )(self.display_all)
                self.dash.clientside_callback(
                    ClientsideFunction("clientside", "mean"),
                    Output("mean-of-all-values", "value"),
                    [
                        Input("x", "value"),
                        Input("y", "value"),
                        Input("x-plus-y", "value"),
                        Input("x-plus-y-div-2", "value"),
                    ],
                )

            def divide_by_two(self, value):
                self.call_counts["divide"].value += 1
                return float(value) / 2.0

            def display_all(self, *args):
                self.call_counts["display"].value += 1
                return "\n".join([str(a) for a in args])

        self.open('dash/{}/'.format(Dash.dash_name))

        test_cases = [
            ["#x", "3"],
            ["#y", "6"],
            ["#x-plus-y", "9"],
            ["#x-plus-y-div-2", "4.5"],
            ["#display-all-of-the-values", "3\n6\n9\n4.5"],
            ["#mean-of-all-values", str((3 + 6 + 9 + 4.5) / 4.0)],
        ]
        for selector, expected in test_cases:
            self.wait_for_text_to_equal(selector, expected)

        assert Dash.call_counts["display"].value == 1
        assert Dash.call_counts["divide"].value == 1

        x_input = self.wait_for_element_by_css_selector("#x")
        x_input.send_keys("1")

        test_cases = [
            ["#x", "31"],
            ["#y", "6"],
            ["#x-plus-y", "37"],
            ["#x-plus-y-div-2", "18.5"],
            ["#display-all-of-the-values", "31\n6\n37\n18.5"],
            ["#mean-of-all-values", str((31 + 6 + 37 + 18.5) / 4.0)],
        ]
        for selector, expected in test_cases:
            self.wait_for_text_to_equal(selector, expected)

        assert Dash.call_counts["display"].value == 2
        assert Dash.call_counts["divide"].value == 2

    def test_clientside_exceptions_halt_subsequent_updates(self):
        class Dash(DashView):
            def __init__(self, **kwargs):
                super(Dash, self).__init__(**kwargs)

                self.dash.layout = html.Div(
                    [
                        dcc.Input(id="first", value=1),
                        dcc.Input(id="second"),
                        dcc.Input(id="third"),
                    ]
                )

                self.dash.clientside_callback(
                    ClientsideFunction("clientside", "add1_break_at_11"),
                    Output("second", "value"),
                    [Input("first", "value")],
                )

                self.dash.clientside_callback(
                    ClientsideFunction("clientside", "add1_break_at_11"),
                    Output("third", "value"),
                    [Input("second", "value")],
                )

        self.open('dash/{}/'.format(Dash.dash_name))

        test_cases = [["#first", "1"], ["#second", "2"], ["#third", "3"]]
        for selector, expected in test_cases:
            self.wait_for_text_to_equal(selector, expected)

        first_input = self.wait_for_element_by_id("first")
        first_input.send_keys("1")
        # clientside code will prevent the update from occurring
        test_cases = [["#first", "11"], ["#second", "2"], ["#third", "3"]]
        for selector, expected in test_cases:
            self.wait_for_text_to_equal(selector, expected)

        first_input.send_keys("1")

        # the previous clientside code error should not be fatal:
        # subsequent updates should still be able to occur
        test_cases = [["#first", "111"], ["#second", "112"], ["#third", "113"]]
        for selector, expected in test_cases:
            self.wait_for_text_to_equal(selector, expected)

    def test_clientside_multiple_outputs(self):
        class Dash(DashView):
            def __init__(self, **kwargs):
                super(Dash, self).__init__(**kwargs)

                self.dash.layout = html.Div(
                    [
                        dcc.Input(id="input", value=1),
                        dcc.Input(id="output-1"),
                        dcc.Input(id="output-2"),
                        dcc.Input(id="output-3"),
                        dcc.Input(id="output-4"),
                    ]
                )

                self.dash.clientside_callback(
                    ClientsideFunction("clientside", "add_to_four_outputs"),
                    [
                        Output("output-1", "value"),
                        Output("output-2", "value"),
                        Output("output-3", "value"),
                        Output("output-4", "value"),
                    ],
                    [Input("input", "value")],
                )

        self.open('dash/{}/'.format(Dash.dash_name))

        for selector, expected in [
            ["#input", "1"],
            ["#output-1", "2"],
            ["#output-2", "3"],
            ["#output-3", "4"],
            ["#output-4", "5"],
        ]:
            self.wait_for_text_to_equal(selector, expected)

        self.wait_for_element_by_id("input").send_keys("1")

        for selector, expected in [
            ["#input", "11"],
            ["#output-1", "12"],
            ["#output-2", "13"],
            ["#output-3", "14"],
            ["#output-4", "15"],
        ]:
            self.wait_for_text_to_equal(selector, expected)

    def test_clientside_fails_when_returning_a_promise(self):
        class Dash(DashView):
            def __init__(self, **kwargs):
                super(Dash, self).__init__(**kwargs)

                self.dash.layout = html.Div(
                    [
                        html.Div(id="input", children="hello"),
                        html.Div(id="side-effect"),
                        html.Div(id="output", children="output"),
                    ]
                )

                self.dash.clientside_callback(
                    ClientsideFunction("clientside", "side_effect_and_return_a_promise"),
                    Output("output", "children"),
                    [Input("input", "children")],
                )

        self.open('dash/{}/'.format(Dash.dash_name))

        self.wait_for_text_to_equal("#input", "hello")
        self.wait_for_text_to_equal("#side-effect", "side effect")
        self.wait_for_text_to_equal("#output", "output")

    def test_PreventUpdate(self):
        class Dash(DashView):
            def __init__(self, **kwargs):
                super(Dash, self).__init__(**kwargs)

                self.dash.layout = html.Div(
                    [
                        dcc.Input(id="first", value=1),
                        dcc.Input(id="second", value=1),
                        dcc.Input(id="third", value=1)
                    ]
                )

                self.dash.clientside_callback(
                    ClientsideFunction(namespace="clientside", function_name="add1_prevent_at_11"),
                    Output("second", "value"),
                    [Input("first", "value")],
                    [State("second", "value")]
                )

                self.dash.clientside_callback(
                    ClientsideFunction(namespace="clientside", function_name="add1_prevent_at_11"),
                    Output("third", "value"),
                    [Input("second", "value")],
                    [State("third", "value")]
                )

        self.open('dash/{}/'.format(Dash.dash_name))

        self.wait_for_text_to_equal("#first", '1')
        self.wait_for_text_to_equal("#second", '2')
        self.wait_for_text_to_equal("#third", '2')

        self.wait_for_element_by_id("first").send_keys("1")

        self.wait_for_text_to_equal("#first", '11')
        self.wait_for_text_to_equal("#second", '2')
        self.wait_for_text_to_equal("#third", '2')

        self.wait_for_element_by_id("first").send_keys("1")

        self.wait_for_text_to_equal("#first", '111')
        self.wait_for_text_to_equal("#second", '3')
        self.wait_for_text_to_equal("#third", '3')

    def test_no_update(self):
        class Dash(DashView):
            def __init__(self, **kwargs):
                super(Dash, self).__init__(**kwargs)

                self.dash.layout = html.Div(
                    [
                        dcc.Input(id="first", value=1),
                        dcc.Input(id="second", value=1),
                        dcc.Input(id="third", value=1)
                    ]
                )

                self.dash.clientside_callback(
                    ClientsideFunction(namespace="clientside", function_name="add1_no_update_at_11"),
                    [Output("second", "value"),
                     Output("third", "value")],
                    [Input("first", "value")],
                    [State("second", "value"),
                     State("third", "value")]
                )

        self.open('dash/{}/'.format(Dash.dash_name))

        self.wait_for_text_to_equal("#first", '1')
        self.wait_for_text_to_equal("#second", '2')
        self.wait_for_text_to_equal("#third", '2')

        self.wait_for_element_by_id("first").send_keys("1")

        self.wait_for_text_to_equal("#first", '11')
        self.wait_for_text_to_equal("#second", '2')
        self.wait_for_text_to_equal("#third", '3')

        # self.wait_for_element_by_id("first").send_keys("1")
        #
        # self.wait_for_text_to_equal("#first", '111')
        # self.wait_for_text_to_equal("#second", '3')
        # self.wait_for_text_to_equal("#third", '4')

    def test_clientside_inline_source(self):
        class Dash(DashView):
            def __init__(self, **kwargs):
                super(Dash, self).__init__(**kwargs)

                self.dash.layout = html.Div(
                    [
                        dcc.Input(id="input"),
                        html.Div(id="output-clientside"),
                        html.Div(id="output-serverside"),
                    ]
                )

                self.dash.callback(
                    Output("output-serverside", "children"), [Input("input", "value")]
                )(self.update_output)

                self.dash.clientside_callback(
                    """
                    function (value) {
                        return 'Client says "' + value + '"';
                    }
                    """,
                    Output("output-clientside", "children"),
                    [Input("input", "value")],
                )

            def update_output(self, value):
                return 'Server says "{}"'.format(value)

        self.open('dash/{}/'.format(Dash.dash_name))

        self.wait_for_text_to_equal("#output-serverside", 'Server says "None"')
        self.wait_for_text_to_equal(
            "#output-clientside", 'Client says "undefined"'
        )

        self.wait_for_element_by_id("input").send_keys("hello world")
        self.wait_for_text_to_equal(
            "#output-serverside", 'Server says "hello world"'
        )
        self.wait_for_text_to_equal(
            "#output-clientside", 'Client says "hello world"'
        )
