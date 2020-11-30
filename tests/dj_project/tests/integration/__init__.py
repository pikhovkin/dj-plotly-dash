import dash_html_components as html
import dash_core_components as dcc

import pytest

import dash


class BaseDashView(dash.BaseDashView):
    dash_name = 'view'
    dash_components = {dcc.__name__, html.__name__}

    def __init__(self, **kwargs):
        super(BaseDashView, self).__init__(**kwargs)

        self.dash.config.routes_pathname_prefix = '/dash/{}/'.format(self.dash_name)

    def _dash_component_suites(self, request, *args, **kwargs):
        self.dash._generate_scripts_html()
        self.dash._generate_css_dist_html()

        return super(BaseDashView, self)._dash_component_suites(request, *args, **kwargs)


@pytest.fixture()
def use_static_root(settings):
    from django.contrib.staticfiles.finders import get_finder

    static_root = ('', settings.STATIC_ROOT)
    finder = get_finder('django.contrib.staticfiles.finders.FileSystemFinder')
    finder.locations.append(static_root)
    yield

    try:
        finder.locations.remove(static_root)
    except ValueError:
        pass
