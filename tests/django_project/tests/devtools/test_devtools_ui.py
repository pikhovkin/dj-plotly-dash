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
                # self.dash._dev_tools.props_check = True
                self.dash._dev_tools.serve_dev_bundles = True
                # self.dash._dev_tools.hot_reload = True
                # self.dash._dev_tools.silence_routes_logging = True

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
