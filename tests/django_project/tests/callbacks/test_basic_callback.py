from multiprocessing import Value

from bs4 import BeautifulSoup
import dash_core_components as dcc
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
    @property
    def redux_state_rqs(self):
        return self.driver.execute_script(
            "return window.store.getState().requestQueue"
        )

    @property
    def redux_state_paths(self):
        return self.driver.execute_script(
            "return window.store.getState().paths"
        )

    @property
    def dash_entry_locator(self):
        return "#react-entry-point"

    def _get_dash_dom_by_attribute(self, attr):
        return BeautifulSoup(
            self.find_element(self.dash_entry_locator).get_attribute(attr),
            "lxml",
        )

    @property
    def dash_innerhtml_dom(self):
        return self._get_dash_dom_by_attribute("innerHTML")

    def test_simple_callback(self):
        class DashCallbacksSimpleCallback(DashView):
            dash_name = 'callbacks_simple_callback'
            dash_components = {dcc.__name__, html.__name__}

            call_count = Value("i", 0)

            def __init__(self, **kwargs):
                super(DashCallbacksSimpleCallback, self).__init__(**kwargs)

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

        self.open('dash/{}/'.format(DashCallbacksSimpleCallback.dash_name))

        assert self.find_element("#output-1").text == "initial value"

        input_ = self.find_element("#input")
        self.clear_input(input_)

        input_.send_keys("hello world")

        assert self.find_element("#output-1").text == "hello world"

        assert DashCallbacksSimpleCallback.call_count.value == 2 + len(
            "hello world"
        ), "initial count + each key stroke"

        rqs = self.redux_state_rqs
        assert len(rqs) == 1

        assert self.get_logs() == []


    def test_callbacks_generating_children(self):
        """ Modify the DOM tree by adding new components in the callbacks
        """
        class DashCallbacksGeneratingChildren(DashView):
            dash_name = 'callbacks_generating_children'
            dash_components = {dcc.__name__, html.__name__}

            call_count = Value('i', 0)

            def __init__(self, **kwargs):
                super(DashCallbacksGeneratingChildren, self).__init__(**kwargs)

                self.dash.layout = html.Div(
                    [dcc.Input(id='input', value='initial value'), html.Div(id='output')]
                )

                self.dash.callback(Output('output', 'children'), [Input('input', 'value')])(self.pad_output)
                self.dash.callback(Output('sub-output-1', 'children'), [Input('sub-input-1', 'value')])(self.update_input)

            def pad_output(self, input):
                return html.Div(
                    [
                        dcc.Input(id='sub-input-1', value='sub input initial value'),
                        html.Div(id='sub-output-1'),
                    ]
                )

            def update_input(self, value):
                self.call_count.value = self.call_count.value + 1
                return value

        self.open('dash/{}/'.format(DashCallbacksGeneratingChildren.dash_name))

        self.wait_for_text_to_equal("#sub-output-1", "sub input initial value")

        assert DashCallbacksGeneratingChildren.call_count.value == 1, "called once at initial stage"

        pad_input, pad_div = self.dash_innerhtml_dom.select_one(
            "#output > div"
        ).contents

        assert (
            pad_input.attrs["value"] == "sub input initial value"
            and pad_input.attrs["id"] == "sub-input-1"
        )
        assert pad_input.name == "input"

        assert (
            pad_div.text == pad_input.attrs["value"]
            and pad_div.get("id") == "sub-output-1"
        ), "the sub-output-1 content reflects to sub-input-1 value"

        assert self.redux_state_paths == {
            "input": ["props", "children", 0],
            "output": ["props", "children", 1],
            "sub-input-1": [
                "props",
                "children",
                1,
                "props",
                "children",
                "props",
                "children",
                0,
            ],
            "sub-output-1": [
                "props",
                "children",
                1,
                "props",
                "children",
                "props",
                "children",
                1,
            ],
        }, "the paths should include these new output IDs"

        # editing the input should modify the sub output
        self.find_element("#sub-input-1").send_keys("deadbeef")

        assert (
            self.find_element("#sub-output-1").text == pad_input.attrs["value"] + "deadbeef"
        ), "deadbeef is added"

        # the total updates is initial one + the text input changes
        self.wait_for_text_to_equal(
            "#sub-output-1", pad_input.attrs["value"] + "deadbeef"
        )

        rqs = self.redux_state_rqs
        assert rqs, "request queue is not empty"
        assert all((rq["status"] == 200 and not rq["rejected"] for rq in rqs))

        assert self.get_logs() == [], "console is clean"
