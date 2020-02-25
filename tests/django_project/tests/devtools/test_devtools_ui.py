import time

import dash_core_components as dcc
import dash_html_components as html

import dash

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
    def test_disable_props_check_config(self):
        class DashDisablePropsCheckConfig(DashView):
            dash_name = 'disable_props_check_config'
            dash_components = {dcc.__name__, html.__name__}

            def __init__(self, **kwargs):
                super(DashDisablePropsCheckConfig, self).__init__(**kwargs)

                self.dash._dev_tools.ui = True
                self.dash._dev_tools.props_check = False
                self.dash._dev_tools.serve_dev_bundles = True
                # self.dash._dev_tools.hot_reload = True
                self.dash._dev_tools.silence_routes_logging = True

                self.dash.layout = html.Div(
                    [
                        html.P(id="tcid", children="Hello Props Check"),
                        dcc.Graph(id="broken", animate=3),  # error ignored by disable
                    ]
                )

        self.open('dash/{}/'.format(DashDisablePropsCheckConfig.dash_name))

        self.wait_for_text_to_equal("#tcid", "Hello Props Check")
        assert self.find_elements(
            "#broken svg.main-svg"
        ), "graph should be rendered"

        assert self.find_elements(
            ".dash-debug-menu"
        ), "the debug menu icon should show up"

    def test_disable_ui_config(self):
        class DashDisableUIConfig(DashView):
            dash_name = 'disable_ui_config'
            dash_components = {dcc.__name__, html.__name__}
            # dash_serve_dev_bundles = True

            def __init__(self, **kwargs):
                super(DashDisableUIConfig, self).__init__(**kwargs)

                self.dash._dev_tools.ui = False
                self.dash._dev_tools.props_check = True
                self.dash._dev_tools.serve_dev_bundles = True
                # self.dash._dev_tools.hot_reload = True
                self.dash._dev_tools.silence_routes_logging = True
                self.dash._dev_tools.prune_errors = True

                self.dash.layout = html.Div(
                    [
                        html.P(id="tcid", children="Hello Disable UI"),
                        dcc.Graph(id="broken", animate='3'),  # error ignored by disable
                    ]
                )

        self.open('dash/{}/'.format(DashDisableUIConfig.dash_name))

        self.wait_for_text_to_equal("#tcid", "Hello Disable UI")
        # logs = str(until(self.get_logs, 1))
        logs = str(self.wait_until_get_log(timeout=1))
        assert (
            "Invalid argument `animate` passed into Graph" in logs
        ), "the error should present in the console without DEV tools UI"

        assert not self.find_elements(
            ".dash-debug-menu"
        ), "the debug menu icon should NOT show up"
