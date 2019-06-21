# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
from multiprocessing import Value

import dash_core_components as dcc
import dash_html_components as html
import dash_flow_example
import dash_dangerously_set_inner_html

from dash import BaseDashView, no_update
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate


class DashView(BaseDashView):
    def __init__(self, **kwargs):
        super(DashView, self).__init__(**kwargs)

        self.dash.config.routes_pathname_prefix = '/dash/{}/'.format(self.dash_name)
        self.dash.css.config.serve_locally = True
        self.dash.scripts.config.serve_locally = True

    def _dash_component_suites(self, request, *args, **kwargs):
        self.dash._generate_scripts_html()
        self.dash._generate_css_dist_html()

        return super(DashView, self)._dash_component_suites(request, *args, **kwargs)


class DashSimpleCallback(DashView):
    dash_name = 'dash01'
    dash_components = {dcc.__name__, html.__name__}

    call_count = Value('i', 0)

    def __init__(self, **kwargs):
        super(DashSimpleCallback, self).__init__(**kwargs)

        self.dash.layout = html.Div([
            dcc.Input(
                id='input',
                value='initial value'
            ),
            html.Div(
                html.Div([
                    1.5,
                    None,
                    'string',
                    html.Div(id='output-1')
                ])
            )
        ])

        self.dash.callback(Output('output-1', 'children'),
                           [Input('input', 'value')])(self.update_output)

    def update_output(self, value):
        self.call_count.value = self.call_count.value + 1

        return value


class DashWildcardCallback(DashView):
    dash_name = 'dash02'
    dash_components = {html.__name__, dcc.__name__}

    call_count = Value('i', 0)

    def __init__(self, **kwargs):
        super(DashWildcardCallback, self).__init__(**kwargs)

        self.dash.layout = html.Div([
            dcc.Input(
                id='input',
                value='initial value'
            ),
            html.Div(
                html.Div([
                    1.5,
                    None,
                    'string',
                    html.Div(id='output-1', **{'data-cb': 'initial value',
                                               'aria-cb': 'initial value'})
                ])
            )
        ])

        self.dash.callback(Output('output-1', 'data-cb'),
                           [Input('input', 'value')])(self.update_data)
        self.dash.callback(Output('output-1', 'children'),
                           [Input('output-1', 'data-cb')])(self.update_text)

    def update_data(self, value):
        self.call_count.value = self.call_count.value + 1

        return value

    def update_text(self, data):
        return data


class DashAbortedCallback(DashView):
    dash_name = 'dash03'
    dash_components = {html.__name__, dcc.__name__}

    initial_input = 'initial input'
    initial_output = 'initial output'

    callback1_count = Value('i', 0)
    callback2_count = Value('i', 0)

    def __init__(self, **kwargs):
        super(DashAbortedCallback, self).__init__(**kwargs)

        self.dash.layout = html.Div([
            dcc.Input(id='input', value=self.initial_input),
            html.Div(self.initial_output, id='output1'),
            html.Div(self.initial_output, id='output2'),
        ])

        self.dash.callback(Output('output1', 'children'),
                           [Input('input', 'value')])(self.callback1)
        self.dash.callback(Output('output2', 'children'),
                           [Input('output1', 'children')])(self.callback2)

    def callback1(self, value):
        self.callback1_count.value += 1
        if self.callback1_count.value > 2:
            return no_update
        raise PreventUpdate('testing callback does not update')
        return value

    def callback2(self, value):
        self.callback2_count.value += 1
        return value


class DashWildcardDataAttributes(DashView):
    dash_name = 'dash04'
    dash_components = {html.__name__}

    test_time = datetime.datetime(2012, 1, 10, 2, 3)
    test_date = datetime.date(test_time.year, test_time.month, test_time.day)

    def __init__(self, **kwargs):
        super(DashWildcardDataAttributes, self).__init__(**kwargs)

        self.dash.layout = html.Div([
            html.Div(
                id='inner-element',
                **{
                    'data-string': 'multiple words',
                    'data-number': 512,
                    'data-none': None,
                    'data-date': self.test_date,
                    'aria-progress': 5
                }
            )
        ], id='data-element')


class DashFlowComponent(DashView):
    dash_name = 'dash05'
    dash_components = {html.__name__, dash_flow_example.__name__}

    def __init__(self, **kwargs):
        super(DashFlowComponent, self).__init__(**kwargs)

        self.dash.layout = html.Div([
            dash_flow_example.ExampleReactComponent(
                id='react',
                value='my-value',
                label='react component'
            ),
            dash_flow_example.ExampleFlowComponent(
                id='flow',
                value='my-value',
                label='flow component'
            ),
            html.Hr(),
            html.Div(id='output')
        ])

        self.dash.callback(Output('output', 'children'),
                           [Input('react', 'value'),
                            Input('flow', 'value')])(self.display_output)

    def display_output(self, react_value, flow_value):
        return html.Div([
            'You have entered {} and {}'.format(react_value, flow_value),
            html.Hr(),
            html.Label('Flow Component Docstring'),
            html.Pre(dash_flow_example.ExampleFlowComponent.__doc__),
            html.Hr(),
            html.Label('React PropTypes Component Docstring'),
            html.Pre(dash_flow_example.ExampleReactComponent.__doc__),
            html.Div(id='waitfor')
        ])


class DashNoPropsComponent(DashView):
    dash_name = 'dash06'
    dash_components = {html.__name__, dash_dangerously_set_inner_html.__name__}

    def __init__(self, **kwargs):
        super(DashNoPropsComponent, self).__init__(**kwargs)

        self.dash.layout = html.Div([
            dash_dangerously_set_inner_html.DangerouslySetInnerHTML('''
                <h1>No Props Component</h1>
            ''')
        ])


class DashMetaTags(DashView):
    dash_name = 'dash07'
    dash_components = {html.__name__}

    metas = [
        {'name': 'description', 'content': 'my dash app'},
        {'name': 'custom', 'content': 'customized'},
    ]

    def __init__(self, **kwargs):
        super(DashMetaTags, self).__init__(dash_meta_tags=self.metas, **kwargs)

        self.dash.layout = html.Div(id='content')


class DashIndexCustomization(DashView):
    dash_name = 'dash08'
    dash_components = {html.__name__}

    def __init__(self, **kwargs):
        super(DashIndexCustomization, self).__init__(**kwargs)

        self.template_name = 'dash_index_customization.html'
        self.dash.layout = html.Div('Dash app', id='app')


class DashAssets(DashView):
    dash_name = 'dash09'
    dash_components = {html.__name__, dcc.__name__}
    template_name = 'dash_assets.html'

    dash_assets_folder = 'dynamic_dash/assets'
    dash_assets_ignore = '*ignored.*'

    def __init__(self, **kwargs):
        super(DashAssets, self).__init__(**kwargs)

        self.dash.layout = html.Div([html.Div(id='content'), dcc.Input(id='test')], id='layout')


class DashInvalidIndexString(DashView):
    dash_name = 'dash10'
    dash_components = {html.__name__}

    def __init__(self, **kwargs):
        super(DashInvalidIndexString, self).__init__(**kwargs)

        self.dash.layout = html.Div()


class DashExternalFilesInit(DashView):
    dash_name = 'dash11'
    dash_components = {html.__name__}

    js_files = [
        'https://www.google-analytics.com/analytics.js',
        {'src': 'https://cdn.polyfill.io/v2/polyfill.min.js'},
        {
            'src': 'https://cdnjs.cloudflare.com/ajax/libs/ramda/0.26.1/ramda.min.js',
            'integrity': 'sha256-43x9r7YRdZpZqTjDT5E0Vfrxn1ajIZLyYWtfAXsargA=',
            'crossorigin': 'anonymous'
        },
        {
            'src': 'https://cdnjs.cloudflare.com/ajax/libs/lodash.js/4.17.11/lodash.min.js',
            'integrity': 'sha256-7/yoZS3548fXSRXqc/xYzjsmuW3sFKzuvOCHd06Pmps=',
            'crossorigin': 'anonymous'
        }
    ]

    css_files = [
        'https://codepen.io/chriddyp/pen/bWLwgP.css',
        {
            'href': 'https://stackpath.bootstrapcdn.com/bootstrap/4.1.3/css/bootstrap.min.css',
            'rel': 'stylesheet',
            'integrity': 'sha384-MCw98/SFnGE8fJT3GXwEOngsV7Zt27NXFoaoApmYm81iuXoPkFOJwJ8ERdknLPMO',
            'crossorigin': 'anonymous'
        }
    ]

    def __init__(self, **kwargs):
        super(DashExternalFilesInit, self).__init__(dash_external_scripts=self.js_files,
                                                    dash_external_stylesheets=self.css_files, **kwargs)

        self.template_name = 'dash_external_files_init.html'
        self.dash.layout = html.Div()


class DashFuncLayoutAccepted(DashView):
    dash_name = 'dash12'
    dash_components = {html.__name__}

    def __init__(self, **kwargs):
        super(DashFuncLayoutAccepted, self).__init__(**kwargs)

        def create_layout():
            return html.Div('Hello World')

        self.dash.layout = create_layout


class DashLateComponentRegister(DashView):
    dash_name = 'dash13'
    dash_components = {html.__name__, dcc.__name__}

    def __init__(self, **kwargs):
        super(DashLateComponentRegister, self).__init__(**kwargs)

        self.dash.layout = html.Div([
            html.Button('Click me to put a dcc', id='btn-insert'),
            html.Div(id='output')
        ])

        self.dash.callback(Output('output', 'children'),
                           [Input('btn-insert', 'n_clicks')])(self.update_output)

    def update_output(self, value):
        if value is None:
            raise PreventUpdate()

        return dcc.Input(id='inserted-input')
