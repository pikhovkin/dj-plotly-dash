# -*- coding: UTF-8 -*-
from multiprocessing import Value
import time

import dash_html_components as html
import dash_core_components as dcc

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import dash
from dash.dependencies import Input, Output, ClientsideFunction

from .IntegrationTests import IntegrationTests, TIMEOUT


class DashView(dash.BaseDashView):
    def __init__(self, **kwargs):
        super(DashView, self).__init__(**kwargs)

        self.dash.config.routes_pathname_prefix = '/dash/{}/'.format(self.dash_name)

    def _dash_component_suites(self, request, *args, **kwargs):
        self.dash._generate_scripts_html()
        self.dash._generate_css_dist_html()

        return super(DashView, self)._dash_component_suites(request, *args, **kwargs)


class Tests(IntegrationTests):
    def wait_for_style_to_equal(self, selector, style, assertion_style, timeout=TIMEOUT):
        start = time.time()
        exception = Exception('Time ran out, {} on {} not found'.format(
            assertion_style, selector))
        while time.time() < start + timeout:
            element = self.wait_for_element_by_css_selector(selector)
            try:
                self.assertEqual(
                    assertion_style, element.value_of_css_property(style))
            except Exception as e:
                exception = e
            else:
                return
            time.sleep(0.1)

        raise exception

    def test_simple_clientside_serverside_callback(self):
        class DashSimpleClientsideServersideCallback(DashView):
            dash_name = 'simple_clientside_serverside_callback'
            dash_assets_folder = 'dynamic_dash/clientside_assets'
            dash_components = {dcc.__name__, html.__name__}

            def __init__(self, **kwargs):
                super(DashSimpleClientsideServersideCallback, self).__init__(**kwargs)

                self.dash.layout = html.Div([
                    dcc.Input(id='input'),
                    html.Div(id='output-clientside'),
                    html.Div(id='output-serverside')
                ])

                self.dash.callback(Output('output-serverside', 'children'),
                                   [Input('input', 'value')])(self.update_output)
                self.dash.clientside_callback(
                    ClientsideFunction(
                        namespace='clientside',
                        function_name='display'
                    ),
                    Output('output-clientside', 'children'),
                    [Input('input', 'value')]
                )

            def update_output(self, value):
                return 'Server says "{}"'.format(value)

        self.open('dash/{}/'.format(DashSimpleClientsideServersideCallback.dash_name))

        input = self.wait_for_element_by_css_selector('#input')
        self.wait_for_text_to_equal('#output-serverside', 'Server says "None"')
        self.wait_for_text_to_equal(
            '#output-clientside', 'Client says "undefined"'
        )

        input.send_keys('hello world')
        self.wait_for_text_to_equal(
            '#output-serverside', 'Server says "hello world"'
        )
        self.wait_for_text_to_equal(
            '#output-clientside', 'Client says "hello world"'
        )

    def test_chained_serverside_clientside_callbacks(self):
        class DashChainedServersideClientsideCallback(DashView):
            dash_name = 'chained_serverside_clientside_callbacks'
            dash_assets_folder = 'dynamic_dash/clientside_assets'
            dash_components = {dcc.__name__, html.__name__}

            call_counts = {
                'divide': Value('i', 0),
                'display': Value('i', 0)
            }

            def __init__(self, **kwargs):
                super(DashChainedServersideClientsideCallback, self).__init__(**kwargs)

                self.dash.layout = html.Div([
                    html.Label('x'),
                    dcc.Input(id='x', value=3),

                    html.Label('y'),
                    dcc.Input(id='y', value=6),

                    # clientside
                    html.Label('x + y (clientside)'),
                    dcc.Input(id='x-plus-y'),

                    # server-side
                    html.Label('x+y / 2 (serverside)'),
                    dcc.Input(id='x-plus-y-div-2'),

                    # server-side
                    html.Div([
                        html.Label('Display x, y, x+y/2 (serverside)'),
                        dcc.Textarea(id='display-all-of-the-values'),
                    ]),

                    # clientside
                    html.Label('Mean(x, y, x+y, x+y/2) (clientside)'),
                    dcc.Input(id='mean-of-all-values'),

                ])

                self.dash.clientside_callback(
                    ClientsideFunction('clientside', 'add'),
                    Output('x-plus-y', 'value'),
                    [Input('x', 'value'), Input('y', 'value')])
                self.dash.callback(
                    Output('x-plus-y-div-2', 'value'),
                    [Input('x-plus-y', 'value')])(self.divide_by_two)
                self.dash.callback(
                    Output('display-all-of-the-values', 'value'),
                    [Input('x', 'value'),
                     Input('y', 'value'),
                     Input('x-plus-y', 'value'),
                     Input('x-plus-y-div-2', 'value')])(self.display_all)
                self.dash.clientside_callback(
                    ClientsideFunction('clientside', 'mean'),
                    Output('mean-of-all-values', 'value'),
                    [Input('x', 'value'),
                     Input('y', 'value'),
                     Input('x-plus-y', 'value'),
                     Input('x-plus-y-div-2', 'value')])

            def divide_by_two(self, value):
                self.call_counts['divide'].value += 1
                return float(value) / 2.0

            def display_all(self, *args):
                self.call_counts['display'].value += 1
                return '\n'.join([str(a) for a in args])

        self.open('dash/{}/'.format(DashChainedServersideClientsideCallback.dash_name))

        test_cases = [
            ['#x', '3'],
            ['#y', '6'],
            ['#x-plus-y', '9'],
            ['#x-plus-y-div-2', '4.5'],
            ['#display-all-of-the-values', '3\n6\n9\n4.5'],
            ['#mean-of-all-values', str((3 + 6 + 9 + 4.5) / 4.0)],
        ]
        for test_case in test_cases:
            self.wait_for_text_to_equal(test_case[0], test_case[1])

        self.assertEqual(DashChainedServersideClientsideCallback.call_counts['display'].value, 1)
        self.assertEqual(DashChainedServersideClientsideCallback.call_counts['divide'].value, 1)

        x_input = self.wait_for_element_by_css_selector('#x')
        x_input.send_keys('1')

        test_cases = [
            ['#x', '31'],
            ['#y', '6'],
            ['#x-plus-y', '37'],
            ['#x-plus-y-div-2', '18.5'],
            ['#display-all-of-the-values', '31\n6\n37\n18.5'],
            ['#mean-of-all-values', str((31 + 6 + 37 + 18.5) / 4.0)],
        ]
        for test_case in test_cases:
            self.wait_for_text_to_equal(test_case[0], test_case[1])

        self.assertEqual(DashChainedServersideClientsideCallback.call_counts['display'].value, 2)
        self.assertEqual(DashChainedServersideClientsideCallback.call_counts['divide'].value, 2)

    def test_clientside_exceptions_halt_subsequent_updates(self):
        class DashClientsideExceptionsHaltSubsequentUpdates(DashView):
            dash_name = 'clientside_exceptions_halt_subsequent_updates'
            dash_assets_folder = 'dynamic_dash/clientside_assets'
            dash_components = {dcc.__name__, html.__name__}

            def __init__(self, **kwargs):
                super(DashClientsideExceptionsHaltSubsequentUpdates, self).__init__(**kwargs)

                self.dash.layout = html.Div([
                    dcc.Input(id='first', value=1),
                    dcc.Input(id='second'),
                    dcc.Input(id='third'),
                ])
                self.dash.clientside_callback(
                    ClientsideFunction('clientside', 'add1_break_at_11'),
                    Output('second', 'value'),
                    [Input('first', 'value')],
                )
                self.dash.clientside_callback(
                    ClientsideFunction('clientside', 'add1_break_at_11'),
                    Output('third', 'value'),
                    [Input('second', 'value')],
                )

        self.open('dash/{}/'.format(DashClientsideExceptionsHaltSubsequentUpdates.dash_name))

        test_cases = [
            ['#first', '1'],
            ['#second', '2'],
            ['#third', '3'],
        ]
        for test_case in test_cases:
            self.wait_for_text_to_equal(test_case[0], test_case[1])

        first_input = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, 'first'))
        )
        first_input.send_keys('1')
        # clientside code will prevent the update from occurring
        test_cases = [
            ['#first', '11'],
            ['#second', '2'],
            ['#third', '3']
        ]
        for test_case in test_cases:
            self.wait_for_text_to_equal(test_case[0], test_case[1])

        first_input.send_keys('1')

        # the previous clientside code error should not be fatal:
        # subsequent updates should still be able to occur
        test_cases = [
            ['#first', '111'],
            ['#second', '112'],
            ['#third', '113']
        ]
        for test_case in test_cases:
            self.wait_for_text_to_equal(test_case[0], test_case[1])

    def test_clientside_multiple_outputs(self):
        class DashClientsideMultipleOutputs(DashView):
            dash_name = 'clientside_multiple_outputs'
            dash_assets_folder = 'dynamic_dash/clientside_assets'
            dash_components = {dcc.__name__, html.__name__}

            def __init__(self, **kwargs):
                super(DashClientsideMultipleOutputs, self).__init__(**kwargs)

                self.dash.layout = html.Div([
                    dcc.Input(id='input', value=1),
                    dcc.Input(id='output-1'),
                    dcc.Input(id='output-2'),
                    dcc.Input(id='output-3'),
                    dcc.Input(id='output-4'),
                ])

                self.dash.clientside_callback(
                    ClientsideFunction('clientside', 'add_to_four_outputs'),
                    [Output('output-1', 'value'),
                     Output('output-2', 'value'),
                     Output('output-3', 'value'),
                     Output('output-4', 'value')],
                    [Input('input', 'value')])

        self.open('dash/{}/'.format(DashClientsideMultipleOutputs.dash_name))

        for test_case in [
            ['#input', '1'],
            ['#output-1', '2'],
            ['#output-2', '3'],
            ['#output-3', '4'],
            ['#output-4', '5']
        ]:
            self.wait_for_text_to_equal(test_case[0], test_case[1])

        input = self.wait_for_element_by_css_selector('#input')
        input.send_keys('1')

        for test_case in [
            ['#input', '11'],
            ['#output-1', '12'],
            ['#output-2', '13'],
            ['#output-3', '14'],
            ['#output-4', '15']
        ]:
            self.wait_for_text_to_equal(test_case[0], test_case[1])

    def test_clientside_fails_when_returning_a_promise(self):
        class DashClientsideFailsWhenReturningAPromise(DashView):
            dash_name = 'clientside_fails_when_returning_a_promise'
            dash_assets_folder = 'dynamic_dash/clientside_assets'
            dash_components = {dcc.__name__, html.__name__}

            def __init__(self, **kwargs):
                super(DashClientsideFailsWhenReturningAPromise, self).__init__(**kwargs)

                self.dash.layout = html.Div([
                    html.Div(id='input', children='hello'),
                    html.Div(id='side-effect'),
                    html.Div(id='output', children='output')
                ])

                self.dash.clientside_callback(
                    ClientsideFunction('clientside', 'side_effect_and_return_a_promise'),
                    Output('output', 'children'),
                    [Input('input', 'children')])

        self.open('dash/{}/'.format(DashClientsideFailsWhenReturningAPromise.dash_name))

        self.wait_for_text_to_equal('#input', 'hello')
        self.wait_for_text_to_equal('#side-effect', 'side effect')
        self.wait_for_text_to_equal('#output', 'output')
