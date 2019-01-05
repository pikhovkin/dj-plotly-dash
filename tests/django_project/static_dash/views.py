# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
from multiprocessing import Value

import dash_core_components as dcc
import dash_html_components as html
import dash_flow_example
import dash_dangerously_set_inner_html

from dash import BaseDashView, Dash
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate


class DashView(BaseDashView):
    @staticmethod
    def set_config(dash, dash_name):
        dash.config.suppress_callback_exceptions = True
        dash.config.routes_pathname_prefix = '/dash/{}/'.format(dash_name)
        dash.css.config.serve_locally = True
        dash.scripts.config.serve_locally = True

    def get(self, request, *args, **kwargs):
        return self.serve_dash_index(request, self.dash_name, *args, **kwargs)


class DashSimpleCallback(DashView):
    dash_name = 'static_dash01'
    dash_components = {dcc.__name__, html.__name__}

    dash = Dash()

    DashView.set_config(dash, dash_name)  # As an opportunity

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

    DashView.set_config(dash, dash_name)  # As an opportunity

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

    DashView.set_config(dash, dash_name)  # As an opportunity

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

    DashView.set_config(dash, dash_name)  # As an opportunity

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

    DashView.set_config(dash, dash_name)  # As an opportunity

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

    DashView.set_config(dash, dash_name)  # As an opportunity

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

    DashView.set_config(dash, dash_name)  # As an opportunity

    dash.layout = html.Div(id='content')


class DashIndexCustomization(DashView):
    dash_name = 'static_dash08'
    dash_components = {html.__name__}

    dash = Dash()
    dash.index_string = '''
    <!DOCTYPE html>
    <html>
        <head>
            {%metas%}
            <title>{%title%}</title>
            {%favicon%}
            {%css%}
        </head>
        <body>
            <div id="custom-header">My custom header</div>
            <div id="add"></div>
            {%app_entry%}
            <footer>
                {%config%}
                {%scripts%}
            </footer>
            <div id="custom-footer">My custom footer</div>
            <script>
            // Test the formatting doesn't mess up script tags.
            var elem = document.getElementById('add');
            if (!elem) {
                throw Error('could not find container to add');
            }
            elem.innerHTML = 'Got added';
            var config = {};
            fetch('/nonexist').then(r => r.json())
                .then(r => config = r).catch(err => ({config}));
            </script>
        </body>
    </html>
    '''

    DashView.set_config(dash, dash_name)  # As an opportunity

    dash.layout = html.Div('Dash app', id='app')


class DashAssets(DashView):
    dash_name = 'static_dash09'
    dash_components = {html.__name__, dcc.__name__}

    dash_template = '''
    <!DOCTYPE html>
    <html>
        <head>
            {%metas%}
            <title>{%title%}</title>
            {%css%}
        </head>
        <body>
            <div id="tested"></div>
            {%app_entry%}
            <footer>
                {%config%}
                {%scripts%}
            </footer>
        </body>
    </html>
    '''
    dash_assets_folder = 'static_dash/assets'
    dash_assets_ignore = '*ignored.*'

    dash = Dash()

    DashView.set_config(dash, dash_name)  # As an opportunity

    dash.layout = html.Div([html.Div(id='content'), dcc.Input(id='test')], id='layout')


class DashInvalidIndexString(DashView):
    dash_name = 'static_dash10'
    dash_components = {html.__name__}

    dash = Dash()

    DashView.set_config(dash, dash_name)  # As an opportunity

    dash.layout = html.Div()


class DashExternalFilesInit(DashView):
    dash_name = 'static_dash11'
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

    dash = Dash(external_scripts=js_files, external_stylesheets=css_files)
    dash.index_string = '''
    <!DOCTYPE html>
    <html>
        <head>
            {%metas%}
            <title>{%title%}</title>
            {%css%}
        </head>
        <body>
            <div id="tested"></div>
            <div id="ramda-test">Hello World</div>
            <button type="button" id="btn">Btn</button>
            {%app_entry%}
            <footer>
                {%config%}
                {%scripts%}
            </footer>
        </body>
    </html>
    '''

    DashView.set_config(dash, dash_name)  # As an opportunity

    dash.layout = html.Div()


class DashFuncLayoutAccepted(DashView):
    dash_name = 'static_dash12'
    dash_components = {html.__name__}

    dash = Dash()

    DashView.set_config(dash, dash_name)  # As an opportunity

    dash.layout = lambda: html.Div('Hello World')


class DashLateComponentRegister(DashView):
    dash_name = 'static_dash13'
    dash_components = {html.__name__, dcc.__name__}

    dash = Dash()

    DashView.set_config(dash, dash_name)  # As an opportunity

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
