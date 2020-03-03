from multiprocessing import Value
import time

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import dash_html_components as html
import dash_core_components as dcc
from dash import exceptions
from dash.dependencies import Input, Output, State

from . import DashView
from .IntegrationTests import IntegrationTests


class Tests(IntegrationTests):
    def test_simple_callback(self):
        class Dash(DashView):
            dash_name = 'view'
            dash_components = {dcc.__name__, html.__name__}

            call_count = Value('i', 0)

            def __init__(self, **kwargs):
                super(Dash, self).__init__(**kwargs)

                self.dash.layout = html.Div(
                    [
                        dcc.Input(id="input", value="initial value"),
                        html.Div(html.Div([1.5, None, "string", html.Div(id="output-1")])),
                    ]
                )

                self.dash.callback(Output("output-1", "children"), [Input("input", "value")])(self.update_output)

            def update_output(self, value):
                self.call_count.value = self.call_count.value + 1

                return value

        self.open('dash/{}/'.format(Dash.dash_name))

        self.wait_for_text_to_equal('#output-1', 'initial value')

        input1 = self.wait_for_element_by_id('input')
        chain = (
            ActionChains(self.driver)
                .click(input1)
                .send_keys(Keys.HOME)
                .key_down(Keys.SHIFT)
                .send_keys(Keys.END)
                .key_up(Keys.SHIFT)
                .send_keys(Keys.DELETE))
        chain.perform()

        input1.send_keys('hello world')

        self.wait_for_text_to_equal('#output-1', 'hello world')

        self.assertEqual(
            Dash.call_count.value,
            # an initial call to retrieve the first value
            # and one for clearing the input
            2 +
            # one for each hello world character
            len('hello world')
        )

        self.assertTrue(self.is_console_clean())

    def test_wildcard_callback(self):
        class Dash(DashView):
            dash_name = 'view'
            dash_components = {html.__name__, dcc.__name__}

            input_call_count = Value('i', 0)

            def __init__(self, **kwargs):
                super(Dash, self).__init__(**kwargs)

                self.dash.layout = html.Div(
                    [
                        dcc.Input(id="input", value="initial value"),
                        html.Div(
                            html.Div(
                                [
                                    1.5,
                                    None,
                                    "string",
                                    html.Div(
                                        id="output-1",
                                        **{
                                            "data-cb": "initial value",
                                            "aria-cb": "initial value",
                                        }
                                    ),
                                ]
                            )
                        ),
                    ]
                )

                self.dash.callback(Output("output-1", "data-cb"), [Input("input", "value")])(self.update_data)
                self.dash.callback(Output("output-1", "children"), [Input("output-1", "data-cb")])(self.update_text)

            def update_data(self, value):
                self.input_call_count.value += 1

                return value

            def update_text(self, data):
                return data

        self.open('dash/{}/'.format(Dash.dash_name))

        self.wait_for_text_to_equal("#output-1", "initial value")

        input1 = self.wait_for_element_by_css_selector('#input')
        self.clear_input(input1)
        input1.send_keys("hello world")

        self.wait_for_text_to_equal("#output-1", "hello world")

        # an initial call, one for clearing the input
        # and one for each hello world character
        self.assertTrue(Dash.input_call_count.value == 2 + len('hello world'))

        self.assertTrue(self.is_console_clean())
