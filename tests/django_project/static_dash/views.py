# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
from multiprocessing import Value

import dash_core_components as dcc
import dash_html_components as html
import dash_flow_example
import dash_dangerously_set_inner_html

from dash._utils import create_callback_id as _create_callback_id
from dash import BaseDashView, Dash, no_update
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate


class DashView(BaseDashView):
    def __init__(self, **kwargs):
        super(DashView, self).__init__(**kwargs)

        self.dash.config.routes_pathname_prefix = '/dash/{}/'.format(self.dash_name)
        self.dash.css.config.serve_locally = True
        self.dash.scripts.config.serve_locally = True


class DashSimpleCallback(DashView):
    dash_name = 'static_dash01'
    dash_components = {dcc.__name__, html.__name__}

    dash = Dash()
    dash.layout = html.Div([
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

    call_count = Value('i', 0)

    @staticmethod
    @dash.callback(Output('output-1', 'children'), [Input('input', 'value')])
    def update_output(value):
        DashSimpleCallback.call_count.value = DashSimpleCallback.call_count.value + 1

        return value


class DashWildcardCallback(DashView):
    dash_name = 'static_dash02'
    dash_components = {html.__name__, dcc.__name__}

    dash = Dash()
    dash.layout = html.Div([
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

    call_count = Value('i', 0)

    @classmethod  # As an opportunity
    def update_data(cls, value):
        cls.call_count.value = cls.call_count.value + 1

        return value

    @staticmethod  # As an opportunity
    @dash.callback(Output('output-1', 'children'), [Input('output-1', 'data-cb')])
    def update_text(data):
        return data


DashWildcardCallback.dash.callback(Output('output-1', 'data-cb'),
                                   [Input('input', 'value')])(DashWildcardCallback.update_data)


class DashAbortedCallback(DashView):
    dash_name = 'static_dash03'
    dash_components = {html.__name__, dcc.__name__}

    initial_input = 'initial input'
    initial_output = 'initial output'

    dash = Dash()
    dash.layout = html.Div([
        dcc.Input(id='input', value=initial_input),
        html.Div(initial_output, id='output1'),
        html.Div(initial_output, id='output2'),
    ])

    callback1_count = Value('i', 0)
    callback2_count = Value('i', 0)

    @classmethod  # As an opportunity
    def callback1(cls, value):
        cls.callback1_count.value = cls.callback1_count.value + 1
        if cls.callback1_count.value > 2:
            return no_update
        raise PreventUpdate('testing callback does not update')
        return value

    @staticmethod  # As an opportunity
    @dash.callback(Output('output2', 'children'), [Input('output1', 'children')])
    def callback2(value):
        DashAbortedCallback.callback2_count.value = DashAbortedCallback.callback2_count.value + 1
        return value


DashAbortedCallback.dash.callback(Output('output1', 'children'),
                                  [Input('input', 'value')])(DashAbortedCallback.callback1)


class DashWildcardDataAttributes(DashView):
    dash_name = 'static_dash04'
    dash_components = {html.__name__}

    test_time = datetime.datetime(2012, 1, 10, 2, 3)
    test_date = datetime.date(test_time.year, test_time.month, test_time.day)

    dash = Dash()
    dash.layout = html.Div([
        html.Div(
            id='inner-element',
            **{
                'data-string': 'multiple words',
                'data-number': 512,
                'data-none': None,
                'data-date': test_date,
                'aria-progress': 5
            }
        )
    ], id='data-element')


class DashFlowComponent(DashView):
    dash_name = 'static_dash05'
    dash_components = {html.__name__, dash_flow_example.__name__}

    dash = Dash()
    dash.layout = html.Div([
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

    @staticmethod
    @dash.callback(Output('output', 'children'),
                   [Input('react', 'value'), Input('flow', 'value')])
    def display_output(react_value, flow_value):
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
    dash_name = 'static_dash06'
    dash_components = {html.__name__, dash_dangerously_set_inner_html.__name__}

    dash = Dash()
    dash.layout = html.Div([
        dash_dangerously_set_inner_html.DangerouslySetInnerHTML('''
            <h1>No Props Component</h1>
        ''')
    ])


class DashMetaTags(DashView):
    dash_name = 'static_dash07'
    dash_components = {html.__name__}

    metas = [
        {'name': 'description', 'content': 'my dash app'},
        {'name': 'custom', 'content': 'customized'},
    ]

    dash = Dash(meta_tags=metas)
    dash.layout = html.Div(id='content')


class DashIndexCustomization(DashView):
    dash_name = 'static_dash08'
    dash_components = {html.__name__}
    template_name = 'dash_index_customization.html'

    dash = Dash()
    dash.layout = html.Div('Dash app', id='app')


class DashAssets(DashView):
    dash_name = 'static_dash09'
    dash_components = {html.__name__, dcc.__name__}
    template_name = 'dash_assets.html'

    dash_assets_folder = 'static_dash/assets'
    dash_assets_ignore = '*ignored.*'

    dash = Dash()
    dash.layout = html.Div([html.Div(id='content'), dcc.Input(id='test')], id='layout')


class DashInvalidIndexString(DashView):
    dash_name = 'static_dash10'
    dash_components = {html.__name__}

    dash = Dash()
    dash.layout = html.Div()


class DashExternalFilesInit(DashView):
    dash_name = 'static_dash11'
    dash_components = {html.__name__}
    template_name = 'dash_external_files_init.html'

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

    dash = Dash(external_scripts=js_files, external_stylesheets=css_files)
    dash.layout = html.Div()


class DashFuncLayoutAccepted(DashView):
    dash_name = 'static_dash12'
    dash_components = {html.__name__}

    dash = Dash()
    dash.layout = lambda: html.Div('Hello World')


class DashLateComponentRegister(DashView):
    dash_name = 'static_dash13'
    dash_components = {html.__name__, dcc.__name__}

    dash = Dash()
    dash.layout = html.Div([
        html.Button('Click me to put a dcc', id='btn-insert'),
        html.Div(id='output')
    ])

    @staticmethod  # As an opportunity
    @dash.callback(Output('output', 'children'), [Input('btn-insert', 'n_clicks')])
    def update_output(value):
        if value is None:
            raise PreventUpdate()

        return dcc.Input(id='inserted-input')


class DashMultiOutput(DashView):
    dash_name = 'static_dash14'
    dash_components = {html.__name__}

    dash = Dash()
    dash.layout = html.Div([
        html.Button('OUTPUT', id='output-btn'),

        html.Table([
            html.Thead([
                html.Tr([html.Th('Output 1'), html.Th('Output 2')])
            ]),
            html.Tbody([
                html.Tr([html.Td(id='output1'), html.Td(id='output2')]),
            ])
        ]),

        html.Div(id='output3'),
        html.Div(id='output4'),
        html.Div(id='output5')
    ])

    @staticmethod
    @dash.callback([Output('output1', 'children'), Output('output2', 'children')],
                   [Input('output-btn', 'n_clicks')],
                   [State('output-btn', 'n_clicks_timestamp')])
    def on_click(n_clicks, n_clicks_timestamp):
        if n_clicks is None:
            raise PreventUpdate

        return n_clicks, n_clicks_timestamp

    @staticmethod
    @dash.callback(Output('output3', 'children'),
                  [Input('output-btn', 'n_clicks')])
    def dummy_callback(self, n_clicks):
        """Dummy callback for DuplicateCallbackOutput test
        """
        if n_clicks is None:
            raise PreventUpdate

        return 'Output 3: {}'.format(n_clicks)

    @staticmethod
    def on_click_duplicate(n_clicks):
        if n_clicks is None:
            raise PreventUpdate

        return 'something else'

    @staticmethod
    def on_click_duplicate_multi(n_clicks):
        if n_clicks is None:
            raise PreventUpdate

        return 'something else'

    @staticmethod
    def on_click_same_output(n_clicks):
        return n_clicks


class DashMultiOutputNoUpdate(DashView):
    dash_name = 'static_dash15'
    dash_components = {html.__name__}

    dash = Dash()
    dash.layout = html.Div([
        html.Button('B', 'btn'),
        html.P('initial1', 'n1'),
        html.P('initial2', 'n2'),
        html.P('initial3', 'n3')
    ])

    @staticmethod
    @dash.callback([Output('n1', 'children'), Output('n2', 'children'), Output('n3', 'children')],
                   [Input('btn', 'n_clicks')])
    def show_clicks(n):
        # partial or complete cancelation of updates via no_update
        return [
            no_update if n and n > 4 else n,
            no_update if n and n > 2 else n,
            no_update
        ]


class DashNoUpdateChains(DashView):
    dash_name = 'static_dash16'
    dash_components = {html.__name__, dcc.__name__}

    dash = Dash()
    dash.layout = html.Div([
        dcc.Input(id='a_in', value='a'),
        dcc.Input(id='b_in', value='b'),
        html.P('', id='a_out'),
        html.P('', id='a_out_short'),
        html.P('', id='b_out'),
        html.P('', id='ab_out')
    ])

    @staticmethod
    @dash.callback([Output('a_out', 'children'), Output('a_out_short', 'children')],
                   [Input('a_in', 'value')])
    def a_out(a):
        return (a, a if len(a) < 3 else no_update)


    @staticmethod
    @dash.callback(Output('b_out', 'children'), [Input('b_in', 'value')])
    def b_out(b):
        return b

    @staticmethod
    @dash.callback(Output('ab_out', 'children'),
                   [Input('a_out_short', 'children')],
                   [State('b_out', 'children')])
    def ab_out(a, b):
        return a + ' ' + b


class DashWithCustomRenderer(DashView):
    dash_name = 'static_dash17'
    dash_components = {html.__name__, dcc.__name__}
    template_name = 'dash_with_custom_renderer.html'

    dash = Dash()
    dash.layout = html.Div([
        dcc.Input(id='input', value='initial value'),
        html.Div(
            html.Div([
                html.Div(id='output-1'),
                html.Div(id='output-pre'),
                html.Div(id='output-post')
            ])
        )
    ])

    @staticmethod
    @dash.callback(Output('output-1', 'children'), [Input('input', 'value')])
    def update_output(value):
        return value


class DashModifiedResponse(DashView):
    dash_name = 'static_dash18'
    dash_components = {html.__name__, dcc.__name__}

    dash = Dash()
    dash.layout = html.Div([
        dcc.Input(id='input', value='ab'),
        html.Div(id='output')
    ])

    def __init__(self, **kwargs):
        super(DashModifiedResponse, self).__init__(**kwargs)

        output = Output('output', 'children')
        callback_id = _create_callback_id(output)
        if callback_id not in self.dash.callback_map:
            self.dash.callback(output, [Input('input', 'value')])(self.update_output)

    def update_output(self, value):
        self.response.set_cookie('dash_cookie', value + ' - cookie')
        return value + ' - output'


class DashOutputInputInvalidCallback(DashView):
    dash_name = 'static_dash21'
    dash_components = {html.__name__}

    dash = Dash()
    dash.layout = html.Div([
        html.Div('child', id='input-output'),
        html.Div(id='out')
    ])

    @staticmethod
    def failure(children):
        pass

    staticmethod
    def failure2(children):
        pass
