from multiprocessing import Value
import time
import datetime

from bs4 import BeautifulSoup
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import dash_html_components as html
import dash_core_components as dcc
import dash_flow_example
import dash_dangerously_set_inner_html

from dash import no_update
from dash.dependencies import Input, Output, State
from dash.exceptions import (
    PreventUpdate,
    DuplicateCallbackOutput,
    CallbackException,
    MissingCallbackContextException,
    InvalidCallbackReturnValue,
    IncorrectTypeException,
    NonExistentIdException,
)

from . import DashView as BaseDashView
from .IntegrationTests import IntegrationTests
from .utils import wait_for


class DashView(BaseDashView):
    dash_name = 'view'
    dash_components = {dcc.__name__, html.__name__}


class Tests(IntegrationTests):
    def test_simple_callback(self):
        class Dash(DashView):
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
                self.call_count.value += 1
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

    def test_aborted_callback(self):
        """
        Raising PreventUpdate OR returning no_update
        prevents update and triggering dependencies
        """
        class Dash(DashView):
            initial_input = 'initial input'
            initial_output = 'initial output'

            callback1_count = Value("i", 0)
            callback2_count = Value("i", 0)

            def __init__(self, **kwargs):
                super(Dash, self).__init__(**kwargs)

                self.dash.layout = html.Div(
                    [
                        dcc.Input(id="input", value=self.initial_input),
                        html.Div(self.initial_output, id="output1"),
                        html.Div(self.initial_output, id="output2"),
                    ]
                )

                self.dash.callback(Output("output1", "children"), [Input("input", "value")])(self.callback1)
                self.dash.callback(Output("output2", "children"), [Input("output1", "children")])(self.callback2)

            def callback1(self, value):
                self.callback1_count.value += 1
                if self.callback1_count.value > 2:
                    return no_update
                raise PreventUpdate('testing callback does not update')
                return value

            def callback2(self, value):
                self.callback2_count.value += 1
                return value

        self.open('dash/{}/'.format(Dash.dash_name))

        input_ = self.wait_for_element_by_id("input")
        input_.send_keys("xyz")
        self.wait_for_text_to_equal("#input", "initial inputxyz")

        # callback1 runs 4x (initial page load and 3x through send_keys)
        wait_for(lambda: Dash.callback1_count.value == 4)

        # callback2 is never triggered, even on initial load
        self.assertTrue(Dash.callback2_count.value == 0, "callback2 is never triggered, even on initial load")

        # double check that output1 and output2 children were not updated
        self.assertTrue(self.wait_for_element_by_id("output1").text == Dash.initial_output)
        self.assertTrue(self.wait_for_element_by_id("output2").text == Dash.initial_output)

        self.assertTrue(self.is_console_clean())

    def test_wildcard_data_attributes(self):
        class Dash(DashView):
            test_time = datetime.datetime(2012, 1, 10, 2, 3)
            test_date = datetime.date(test_time.year, test_time.month, test_time.day)
            attrs = {
                "id": "inner-element",
                "data-string": "multiple words",
                "data-number": 512,
                "data-none": None,
                "data-date": test_date,
                "aria-progress": 5,
            }

            def __init__(self, **kwargs):
                super(Dash, self).__init__(**kwargs)
                self.dash.layout = html.Div([html.Div(**self.attrs)], id="data-element")

        self.open('dash/{}/'.format(Dash.dash_name))

        div = self.wait_for_element_by_id('data-element')

        # attribute order is ill-defined - BeautifulSoup will sort them
        actual = BeautifulSoup(div.get_attribute("innerHTML"), "lxml").decode()
        expected = BeautifulSoup(
            "<div "
            + " ".join(
                '{}="{!s}"'.format(k, v) for k, v in Dash.attrs.items() if v is not None
            )
            + "></div>",
            "lxml",
        ).decode()

        assert actual == expected, "all attrs are included except None values"

        self.assertTrue(self.is_console_clean())

    def test_no_props_component(self):
        class Dash(DashView):
            dash_components = {html.__name__, dash_dangerously_set_inner_html.__name__}

            def __init__(self, **kwargs):
                super(Dash, self).__init__(**kwargs)

                self.dash.layout = html.Div(
                    [
                        dash_dangerously_set_inner_html.DangerouslySetInnerHTML(
                            """
                        <h1>No Props Component</h1>
                    """
                        )
                    ]
                )

        self.open('dash/{}/'.format(Dash.dash_name))

        self.assertTrue(self.is_console_clean())

    def test_flow_component(self):
        class Dash(DashView):
            dash_components = {html.__name__, dash_flow_example.__name__}

            def __init__(self, **kwargs):
                super(Dash, self).__init__(**kwargs)

                self.dash.layout = html.Div(
                    [
                        dash_flow_example.ExampleReactComponent(
                            id="react", value="my-value", label="react component"
                        ),
                        dash_flow_example.ExampleFlowComponent(
                            id="flow", value="my-value", label="flow component"
                        ),
                        html.Hr(),
                        html.Div(id="output"),
                    ]
                )

                self.dash.callback(
                    Output("output", "children"),
                    [Input("react", "value"), Input("flow", "value")],
                )(self.display_output)

            def display_output(self, react_value, flow_value):
                return html.Div(
                    [
                        "You have entered {} and {}".format(react_value, flow_value),
                        html.Hr(),
                        html.Label("Flow Component Docstring"),
                        html.Pre(dash_flow_example.ExampleFlowComponent.__doc__),
                        html.Hr(),
                        html.Label("React PropTypes Component Docstring"),
                        html.Pre(dash_flow_example.ExampleReactComponent.__doc__),
                        html.Div(id="waitfor"),
                    ]
                )

        self.open('dash/{}/'.format(Dash.dash_name))

        self.wait_for_element_by_id('waitfor')

    def test_meta_tags(self):
        class Dash(DashView):
            metas = [
                {"name": "description", "content": "my dash app"},
                {"name": "custom", "content": "customized"},
            ]

            def __init__(self, **kwargs):
                super(Dash, self).__init__(dash_meta_tags=self.metas, **kwargs)

                self.dash.layout = html.Div(id="content")

        self.open('dash/{}/'.format(Dash.dash_name))

        metas = Dash.metas
        meta = self.driver.find_elements_by_tag_name('meta')

        # -2 for the meta charset and http-equiv.
        assert len(meta) == len(metas) + 2, "Should have 2 extra meta tags"

        for i in range(2, len(meta)):
            meta_tag = meta[i]
            meta_info = metas[i - 2]
            assert meta_tag.get_attribute("name") == meta_info["name"]
            assert meta_tag.get_attribute("content") == meta_info["content"]

    def test_index_customization(self):
        class Dash(DashView):
            def __init__(self, **kwargs):
                super(Dash, self).__init__(**kwargs)

                self.template_name = 'dash_index_customization.html'
                self.dash.layout = html.Div("Dash app", id="app")

        self.open('dash/{}/'.format(Dash.dash_name))

        assert self.wait_for_element_by_id("custom-header").text == "My custom header"
        assert self.wait_for_element_by_id("custom-footer").text == "My custom footer"
        assert self.wait_for_element_by_id("add").text == "Got added"


    def _test_inin009_invalid_index_string(self):
        app = Dash()

        def will_raise():
            app.index_string = """
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
                    <footer>
                    </footer>
                </body>
            </html>
            """

        with pytest.raises(Exception) as err:
            will_raise()

        exc_msg = str(err.value)
        assert "{%app_entry%}" in exc_msg
        assert "{%config%}" in exc_msg
        assert "{%scripts%}" in exc_msg

        app.layout = html.Div("Hello World", id="a")

        dash_duo.start_server(app)
        assert sel.wait_for_element_by_id("#a").text == "Hello World"

    def test_func_layout_accepted(self):
        class Dash(DashView):
            def __init__(self, **kwargs):
                super(Dash, self).__init__(**kwargs)

                def create_layout():
                    return html.Div("Hello World", id="a")

                self.dash.layout = create_layout

        self.open('dash/{}/'.format(Dash.dash_name))

        assert self.wait_for_element_by_id("a").text == "Hello World"

    def test_multi_output(self):
        class Dash(DashView):
            def __init__(self, **kwargs):
                super(Dash, self).__init__(**kwargs)

                self.dash.layout = html.Div(
                    [
                        html.Button("OUTPUT", id="output-btn"),
                        html.Table(
                            [
                                html.Thead(
                                    [html.Tr([html.Th("Output 1"), html.Th("Output 2")])]
                                ),
                                html.Tbody(
                                    [
                                        html.Tr(
                                            [html.Td(id="output1"), html.Td(id="output2")]
                                        )
                                    ]
                                ),
                            ]
                        ),
                        html.Div(id="output3"),
                        html.Div(id="output4"),
                        html.Div(id="output5"),
                    ]
                )

                self.dash.callback(
                    [Output("output1", "children"), Output("output2", "children")],
                    [Input("output-btn", "n_clicks")],
                    [State("output-btn", "n_clicks_timestamp")],
                )(self.on_click)
                self.dash.callback(
                    Output("output3", "children"), [Input("output-btn", "n_clicks")]
                )(self.dummy_callback)

            def on_click(self, n_clicks, n_clicks_timestamp):
                if n_clicks is None:
                    raise PreventUpdate

                return n_clicks, n_clicks_timestamp

            def dummy_callback(self, n_clicks):
                if n_clicks is None:
                    raise PreventUpdate

                return "Output 3: {}".format(n_clicks)

            def on_click_duplicate(self, n_clicks):
                if n_clicks is None:
                    raise PreventUpdate
                return "something else"

            def on_click_duplicate_multi(self, n_clicks):
                if n_clicks is None:
                    raise PreventUpdate
                return "something else"

            def on_click_same_output(self, n_clicks):
                return n_clicks

            def overlapping_multi_output(self, n_clicks):
                return n_clicks

        view = Dash if getattr(Dash, 'dash', None) else Dash()

        with self.assertRaises(
                DuplicateCallbackOutput,
                msg="multi output can't be included in a single output"
        ) as err:
            view.dash.callback(
                Output("output1", "children"), [Input("output-btn", "n_clicks")]
            )(view.on_click_duplicate)

        assert "output1" in err.exception.args[0]

        with self.assertRaises(
                DuplicateCallbackOutput,
                msg="multi output cannot contain a used single output"
        ) as err:
            view.dash.callback(
                [Output("output3", "children"), Output("output4", "children")],
                [Input("output-btn", "n_clicks")],
            )(view.on_click_duplicate_multi)

        assert "output3" in err.exception.args[0]

        with self.assertRaises(
                DuplicateCallbackOutput,
                msg="same output cannot be used twice in one callback"
        ) as err:
            view.dash.callback([
                Output("output5", "children"), Output("output5", "children")],
                [Input("output-btn", "n_clicks")],
            )(view.on_click_same_output)

        assert 'output5' in err.exception.args[0]

        with self.assertRaises(
                DuplicateCallbackOutput,
                msg="no part of an existing multi-output can be used in another"
        ) as err:
            view.dash.callback(
                [Output("output1", "children"), Output("output5", "children")],
                [Input("output-btn", "n_clicks")],
            )(view.overlapping_multi_output)

        assert (
            "{'output1.children'}" in err.exception.args[0]
            or "set(['output1.children'])" in err.exception.args[0]
        )

        self.open('dash/{}/'.format(Dash.dash_name))

        t = time.time()

        btn = self.driver.find_element_by_id('output-btn')
        btn.click()
        time.sleep(1)

        self.wait_for_text_to_equal('#output1', '1')

        assert int(self.driver.find_element_by_id('output2').text) > t

    def test_multi_output_no_update(self):
        class Dash(DashView):
            def __init__(self, **kwargs):
                super(Dash, self).__init__(**kwargs)

                self.dash.layout = html.Div(
                    [
                        html.Button("B", "btn"),
                        html.P("initial1", "n1"),
                        html.P("initial2", "n2"),
                        html.P("initial3", "n3"),
                    ]
                )

                self.dash.callback(
                    [
                        Output("n1", "children"),
                        Output("n2", "children"),
                        Output("n3", "children"),
                    ],
                    [Input("btn", "n_clicks")],
                )(self.show_clicks)

            def show_clicks(self, n):
                # partial or complete cancelation of updates via no_update
                return [
                    no_update if n and n > 4 else n,
                    no_update if n and n > 2 else n,
                    no_update,
                ]

        self.open('dash/{}/'.format(Dash.dash_name))

        self.multiple_click('#btn', 10)

        self.wait_for_text_to_equal('#n1', '4')
        self.wait_for_text_to_equal('#n2', '2')
        self.wait_for_text_to_equal('#n3', 'initial3')

    def test_no_update_chains(self):
        class Dash(DashView):
            def __init__(self, **kwargs):
                super(Dash, self).__init__(**kwargs)

                self.dash.layout = html.Div(
                    [
                        dcc.Input(id="a_in", value="a"),
                        dcc.Input(id="b_in", value="b"),
                        html.P("", id="a_out"),
                        html.P("", id="a_out_short"),
                        html.P("", id="b_out"),
                        html.P("", id="ab_out"),
                    ]
                )

                self.dash.callback(
                    [Output("a_out", "children"), Output("a_out_short", "children")],
                    [Input("a_in", "value")],
                )(self.a_out)
                self.dash.callback(Output("b_out", "children"), [Input("b_in", "value")])(self.b_out)
                self.dash.callback(
                    Output("ab_out", "children"),
                    [Input("a_out_short", "children")],
                    [State("b_out", "children")],
                )(self.ab_out)

            def a_out(self, a):
                return (a, a if len(a) < 3 else no_update)

            def b_out(self, b):
                return b

            def ab_out(self, a, b):
                return a + " " + b

        self.open('dash/{}/'.format(Dash.dash_name))

        a_in = self.find_element("#a_in")
        b_in = self.find_element("#b_in")

        b_in.send_keys("b")
        a_in.send_keys("a")
        self.wait_for_text_to_equal("#a_out", "aa")
        self.wait_for_text_to_equal("#b_out", "bb")
        self.wait_for_text_to_equal("#a_out_short", "aa")
        self.wait_for_text_to_equal("#ab_out", "aa bb")

        b_in.send_keys("b")
        a_in.send_keys("a")
        self.wait_for_text_to_equal("#a_out", "aaa")
        self.wait_for_text_to_equal("#b_out", "bbb")
        self.wait_for_text_to_equal("#a_out_short", "aa")
        # ab_out has not been triggered because a_out_short received no_update
        self.wait_for_text_to_equal("#ab_out", "aa bb")

        b_in.send_keys("b")
        a_in.send_keys(Keys.END)
        a_in.send_keys(Keys.BACKSPACE)
        self.wait_for_text_to_equal("#a_out", "aa")
        self.wait_for_text_to_equal("#b_out", "bbbb")
        self.wait_for_text_to_equal("#a_out_short", "aa")
        # now ab_out *is* triggered - a_out_short got a new value
        # even though that value is the same as the last value it got
        self.wait_for_text_to_equal("#ab_out", "aa bbbb")

    def test_with_custom_renderer(self):
        class Dash(DashView):
            template_name = 'dash_with_custom_renderer.html'

            def __init__(self, **kwargs):
                super(Dash, self).__init__(**kwargs)

                self.dash.layout = html.Div(
                    [
                        dcc.Input(id="input", value="initial value"),
                        html.Div(
                            html.Div(
                                [
                                    html.Div(id="output-1"),
                                    html.Div(id="output-pre"),
                                    html.Div(id="output-post"),
                                ]
                            )
                        ),
                    ]
                )

                self.dash.callback(Output("output-1", "children"), [Input("input", "value")])(self.update_output)

            def update_output(self, value):
                return value

        self.open('dash/{}/'.format(Dash.dash_name))

        input1 = self.find_element("#input")
        self.clear_input(input1)

        input1.send_keys("fire request hooks")

        self.wait_for_text_to_equal("#output-1", "fire request hooks")
        assert self.find_element("#output-pre").text == "request_pre!!!"
        assert self.find_element("#output-post").text == "request_post ran!"

    def test_with_custom_renderer_interpolated(self):
        class Dash(DashView):
            template_name = 'dash_with_custom_renderer_interpolated.html'

            def __init__(self, **kwargs):
                super(Dash, self).__init__(**kwargs)

                self.dash.layout = html.Div(
                    [
                        dcc.Input(id="input", value="initial value"),
                        html.Div(
                            html.Div(
                                [
                                    html.Div(id="output-1"),
                                    html.Div(id="output-pre"),
                                    html.Div(id="output-post"),
                                ]
                            )
                        ),
                    ]
                )

                self.dash.callback(Output("output-1", "children"), [Input("input", "value")])(self.update_output)

            def update_output(self, value):
                return value

            def _generate_renderer(self):
                return """
                    <script id="_dash-renderer" type="application/javascript">
                        console.log('firing up a custom renderer!')
                        const renderer = new DashRenderer({
                            request_pre: () => {
                                var output = document.getElementById('output-pre')
                                if(output) {
                                    output.innerHTML = 'request_pre was here!';
                                }
                            },
                            request_post: () => {
                                var output = document.getElementById('output-post')
                                if(output) {
                                    output.innerHTML = 'request_post!!!';
                                }
                            }
                        })
                    </script>
                """

        self.open('dash/{}/'.format(Dash.dash_name))

        input1 = self.find_element("#input")
        self.clear_input(input1)

        input1.send_keys("fire request hooks")

        self.wait_for_text_to_equal("#output-1", "fire request hooks")
        assert self.find_element("#output-pre").text == "request_pre was here!"
        assert self.find_element("#output-post").text == "request_post!!!"

    def test_modified_response(self):
        class Dash(DashView):
            def __init__(self, **kwargs):
                super(Dash, self).__init__(**kwargs)

                self.dash.layout = html.Div(
                    [dcc.Input(id="input", value="ab"), html.Div(id="output")]
                )

                self.dash.callback(Output("output", "children"), [Input("input", "value")])(self.update_output)

            def update_output(self, value):
                self.response.set_cookie(
                    "dash cookie", value + " - cookie"
                )
                return value + " - output"

        self.open('dash/{}/'.format(Dash.dash_name))

        self.wait_for_text_to_equal("#output", "ab - output")
        input1 = self.find_element("#input")

        input1.send_keys("cd")

        self.wait_for_text_to_equal("#output", "abcd - output")
        cookie = self.driver.get_cookie("dash cookie")
        # cookie gets json encoded
        assert cookie["value"] == '"abcd - cookie"'

        assert not self.get_logs()
        # self.assertTrue(self.is_console_clean())

    def test_late_component_register(self):
        class Dash(DashView):
            def __init__(self, **kwargs):
                super(Dash, self).__init__(**kwargs)

                self.dash.layout = html.Div(
                    [
                        html.Button("Click me to put a dcc ", id="btn-insert"),
                        html.Div(id="output"),
                    ]
                )

                self.dash.callback(
                    Output("output", "children"), [Input("btn-insert", "n_clicks")]
                )(self.update_output)

            def update_output(self, value):
                if value is None:
                    raise PreventUpdate

                return dcc.Input(id="inserted-input")

        self.open('dash/{}/'.format(Dash.dash_name))

        btn = self.find_element("#btn-insert")
        btn.click()

        self.find_element("#inserted-input")

    def test_output_input_invalid_callback(self):
        class Dash(DashView):
            def __init__(self, **kwargs):
                super(Dash, self).__init__(**kwargs)

                self.dash.layout = html.Div(
                    [html.Div("child", id="input-output"), html.Div(id="out")]
                )

            def failure(self, children):
                pass

            def failure2(self, children):
                pass

        view = Dash if getattr(Dash, 'dash', None) else Dash()

        with self.assertRaises(CallbackException) as err:
            view.dash.callback(
                Output("input-output", "children"),
                [Input("input-output", "children")],
            )(view.failure)

        msg = "Same output and input: input-output.children"
        assert err.exception.args[0] == msg

        # Multi output version.
        with self.assertRaises(CallbackException) as err:
            view.dash.callback(
                [Output("out", "children"), Output("input-output", "children")],
                [Input("input-output", "children")],
            )(view.failure2)

        msg = "Same output and input: input-output.children"
        assert err.exception.args[0] == msg

    def test_callback_dep_types(self):
        class Dash(DashView):
            def __init__(self, **kwargs):
                super(Dash, self).__init__(**kwargs)

                self.dash.layout = html.Div(
                    [
                        html.Div("child", id="in"),
                        html.Div("state", id="state"),
                        html.Div(id="out"),
                    ]
                )

            def f(self, i):
                return i

            def f2(self, i):
                return i

            def f3(self, i):
                return i

            def f4(self, i):
                return i

        view = Dash if getattr(Dash, 'dash', None) else Dash()

        with self.assertRaises(IncorrectTypeException, msg="extra output nesting"):
            view.dash.callback([[Output("out", "children")]], [Input("in", "children")])(view.f)

        with self.assertRaises(IncorrectTypeException, msg="un-nested input"):
            view.dash.callback(Output("out", "children"), Input("in", "children"))(view.f2)

        with self.assertRaises(IncorrectTypeException, msg="un-nested state"):
            view.dash.callback(
                Output("out", "children"),
                [Input("in", "children")],
                State("state", "children"),
            )(view.f3)

        # all OK with tuples
        view.dash.callback(
            (Output("out", "children"),),
            (Input("in", "children"),),
            (State("state", "children"),),
        )(view.f4)

    def test_callback_return_validation(self):
        class Dash(DashView):
            def __init__(self, **kwargs):
                super(Dash, self).__init__(**kwargs)

                self.dash.layout = html.Div(
                    [
                        html.Div(id="a"),
                        html.Div(id="b"),
                        html.Div(id="c"),
                        html.Div(id="d"),
                        html.Div(id="e"),
                        html.Div(id="f"),
                    ]
                )

                self.dash.callback(Output("b", "children"), [Input("a", "children")])(self.single)
                self.dash.callback(
                    [Output("c", "children"), Output("d", "children")],
                    [Input("a", "children")],
                )(self.multi)
                self.dash.callback(
                    [Output("e", "children"), Output("f", "children")],
                    [Input("a", "children")],
                )(self.multi2)

            def single(self, a):
                return set([1])

            def multi(self, a):
                return [1, set([2])]

            def multi2(self, a):
                return ["abc"]

        view = Dash if getattr(Dash, 'dash', None) else Dash()

        with self.assertRaises(InvalidCallbackReturnValue, msg="not serializable"):
            view.single("aaa")

        with self.assertRaises(InvalidCallbackReturnValue, msg="nested non-serializable"):
            view.multi("aaa")

        with self.assertRaises(InvalidCallbackReturnValue, msg="wrong-length list"):
            view.multi2("aaa")

    def test_callback_context(self):
        class Dash(DashView):
            btns = ["btn-{}".format(x) for x in range(1, 6)]

            def __init__(self, **kwargs):
                super(Dash, self).__init__(**kwargs)

                self.dash.layout = html.Div(
                    [
                        html.Div([html.Button(btn, id=btn) for btn in self.btns]),
                        html.Div(id="output"),
                    ]
                )

                self.dash.callback(
                    Output("output", "children"), [Input(x, "n_clicks") for x in self.btns]
                )(self.on_click)

            def on_click(self, *args):
                if not callback_context.triggered:
                    raise PreventUpdate
                trigger = callback_context.triggered[0]
                return "Just clicked {} for the {} time!".format(
                    trigger["prop_id"].split(".")[0], trigger["value"]
                )

        self.open('dash/{}/'.format(Dash.dash_name))

        for i in range(1, 5):
            for btn in Dash.btns:
                self.find_element("#" + btn).click()
                self.wait_for_text_to_equal(
                    "#output", "Just clicked {} for the {} time!".format(btn, i)
                )

    def test_no_callback_context(self):
        for attr in ["inputs", "states", "triggered", "response"]:
            with self.assertRaises(MissingCallbackContextException):
                getattr(callback_context, attr)

    def test_wrong_callback_id(self):
        class Dash(DashView):
            def __init__(self, **kwargs):
                super(Dash, self).__init__(**kwargs)

                self.dash.layout = html.Div(
                    [
                        html.Div(
                            [html.Div(id="inner-div"), dcc.Input(id="inner-input")], id="outer-div"
                        ),
                        dcc.Input(id="outer-input"),
                    ],
                    id="main",
                )

            def f(self, a):
                return a

            def g(self, a):
                return a

            def g2(self, a):
                return [a, a]

            def h(self, a):
                return a

        view = Dash if getattr(Dash, 'dash', None) else Dash()

        ids = ["main", "inner-div", "inner-input", "outer-div", "outer-input"]
        with self.assertRaises(NonExistentIdException) as err:
            view.dash.callback(Output("nuh-uh", "children"), [Input("inner-input", "value")])(view.f)

        assert '"nuh-uh"' in err.exception.args[0]
        for component_id in ids:
            assert component_id in err.exception.args[0]

        with self.assertRaises(NonExistentIdException) as err:
            view.dash.callback(Output("inner-div", "children"), [Input("yeah-no", "value")])(view.g)

        assert '"yeah-no"' in err.exception.args[0]
        for component_id in ids:
            assert component_id in err.exception.args[0]

        with self.assertRaises(NonExistentIdException) as err:
            view.dash.callback(
                [Output("inner-div", "children"), Output("nope", "children")],
                [Input("inner-input", "value")],
            )(view.g2)

        # the right way
        view.dash.callback(Output("inner-div", "children"), [Input("inner-input", "value")])(view.h)
