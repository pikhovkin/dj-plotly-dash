from __future__ import print_function

import logging

import plotly

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import JsonResponse as BaseJsonResponse

from .dash import Dash
from ._utils import generate_hash


__all__ = (
    'MetaDashView',
    'BaseDashView'
)


logger = logging.getLogger('dj_plotly_dash')


class JsonResponse(BaseJsonResponse):
    def __init__(self, data, encoder=plotly.utils.PlotlyJSONEncoder, safe=False,
                 json_dumps_params=None, **kwargs):
        super(JsonResponse, self).__init__(data, encoder=encoder, safe=safe,
                                           json_dumps_params=json_dumps_params, **kwargs)


class MetaDashView(type):
    def __new__(cls, name, bases, attrs):
        new_cls = super(MetaDashView, cls).__new__(cls, name, bases, attrs)

        dash_name = new_cls.__dict__.get('dash_name', getattr(new_cls, 'dash_name', ''))
        if dash_name:
            new_cls._dashes[dash_name] = new_cls   # pylint: disable=protected-access
            dash_prefix = getattr(new_cls, 'dash_prefix', '').strip()
            if dash_prefix:
                # pylint: disable=protected-access
                new_cls._dashes[dash_prefix + new_cls.__dict__['dash_name']] = new_cls

        new_cls._dash_hot_reload_hash = generate_hash()   # pylint: disable=protected-access

        if new_cls.__dict__.get('dash_hot_reload', None) is None:
            try:
                new_cls.dash_hot_reload = getattr(settings, 'DASH_HOT_RELOAD', False)
            except ImproperlyConfigured:
                new_cls.dash_hot_reload = False

        return new_cls


class BaseDashView(TemplateView, metaclass=MetaDashView):
    _dashes = {}

    template_name = 'dash/base.html'
    dash_base_url = '/'
    dash_name = None
    dash_meta_tags = None
    dash_external_scripts = None
    dash_external_stylesheets = None
    dash_assets_folder = None
    dash_assets_ignore = ''
    dash_prefix = ''  # For additional special urls (for example, '_', '__' or other symbols)
    dash_serve_dev_bundles = False
    dash_components = None
    dash_hot_reload = None
    dash_suppress_callback_exceptions = True
    dash_app_entry = """
<div id="react-entry-point">
    <div class="_dash-loading">
        Loading...
    </div>
</div>
"""

    def __init__(self, **kwargs):
        dash_base_url = kwargs.pop('dash_base_url', self.dash_base_url)
        dash_meta_tags = kwargs.pop('dash_meta_tags', self.dash_meta_tags)
        dash_external_scripts = kwargs.pop('dash_external_scripts', self.dash_external_scripts)
        dash_external_stylesheets = kwargs.pop('dash_external_stylesheets', self.dash_external_stylesheets)
        dash_assets_folder = kwargs.pop('dash_assets_folder', self.dash_assets_folder)
        dash_assets_ignore = kwargs.pop('dash_assets_ignore', self.dash_assets_ignore)
        dash_serve_dev_bundles = kwargs.pop('dash_serve_dev_bundles', self.dash_serve_dev_bundles)
        dash_hot_reload = kwargs.pop('dash_hot_reload', self.dash_hot_reload)
        dash_suppress_callback_exceptions = kwargs.pop('dash_suppress_callback_exceptions',
                                                       self.dash_suppress_callback_exceptions)
        dash_app_entry = kwargs.pop('dash_app_entry', self.dash_app_entry)

        super(BaseDashView, self).__init__(**kwargs)

        dash = getattr(self, 'dash', None)
        if not isinstance(dash, Dash):
            self.dash = Dash()

        setattr(self.dash, '_res_affix', '_{}'.format(id(self.__class__)))

        if dash_base_url and self.dash.config.url_base_pathname != dash_base_url:
            self.dash.config.url_base_pathname = dash_base_url  # pylint: disable=access-member-before-definition
            # pylint: disable=access-member-before-definition
            self.dash.config.requests_pathname_prefix = dash_base_url
        self.dash.app_entry = dash_app_entry
        if dash_meta_tags and self.dash.config.meta_tags != dash_meta_tags:  # pylint: disable=protected-access
            # pylint: disable=protected-access, access-member-before-definition
            self.dash.config.meta_tags = dash_meta_tags
        # pylint: disable=protected-access
        if dash_external_scripts and self.dash.config.external_scripts != dash_external_scripts:
            # pylint: disable=protected-access, access-member-before-definition
            self.dash.config.external_scripts = dash_external_scripts
        # pylint: disable=protected-access
        if dash_external_stylesheets and self.dash.config.external_stylesheets != dash_external_stylesheets:
            # pylint: disable=protected-access, access-member-before-definition
            self.dash.config.external_stylesheets = dash_external_stylesheets
        # pylint: disable=protected-access
        if dash_assets_folder and self.dash.config.assets_folder != dash_assets_folder:
            # pylint: disable=protected-access, access-member-before-definition
            self.dash.config.assets_folder = dash_assets_folder
        if dash_assets_ignore and self.dash.config.assets_ignore != dash_assets_ignore:
            self.dash.config.assets_ignore = dash_assets_ignore
        if dash_serve_dev_bundles and self.dash._dev_tools.serve_dev_bundles != dash_serve_dev_bundles:
            self.dash._dev_tools.serve_dev_bundles = dash_serve_dev_bundles
        if self.dash._dev_tools.hot_reload != dash_hot_reload:
            self.dash._dev_tools.hot_reload = dash_hot_reload
        if self.dash.config.suppress_callback_exceptions is not dash_suppress_callback_exceptions:
            self.dash.config.suppress_callback_exceptions = dash_suppress_callback_exceptions

        self.dash.components = set(self.dash_components or [])
        # self.dash.dash_name = self.dash_name
        self.dash._reload_hash = self._dash_hot_reload_hash  # pylint: disable=no-member

        self.setup_conf()
        self.setup_callbacks()

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context.update(**self._dash_index(request, *args, **kwargs))
        return self.render_to_response(context)

    def setup_conf(self):
        """Setup view settings, view variables and etc here
        """
        pass

    def setup_callbacks(self):
        """Setup Dash callbacks
        """
        pass

    def dash_layout(self):
        """Get Dash layout
        """
        raise NotImplementedError('Not implemented dash_layout')

    @staticmethod
    def _dash_base_url(path, part):
        return path[:path.find(part) + 1]

    def _dash_index(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        return self.dash.index()

    def _dash_dependencies(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        self.dash._generate_scripts_html()
        self.dash._generate_css_dist_html()
        return JsonResponse(self.dash.dependencies())

    def _dash_layout(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        if not self.dash._layout:
            self.dash.layout = self.dash_layout()
        # TODO - Set browser cache limit - pass hash into frontend
        return JsonResponse(self.dash._layout_value())  # pylint: disable=protected-access

    def _dash_upd_component(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        output = request.output
        outputs = request.outputs_list
        inputs = request.inputs_list
        state = request.states_list

        self.response = JsonResponse({})  # pylint: disable=attribute-defined-outside-init
        output_value, dash_response = self.dash.update_component(output, outputs, inputs, state)
        self.response.content = JsonResponse(dash_response).content
        return self.response

    def _dash_component_suites(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        self.dash._generate_scripts_html()
        self.dash._generate_css_dist_html()

        ext = kwargs.get('fingerprinted_path', '').split('.')[-1]
        mimetype = {
            'js': 'application/javascript',
            'css': 'text/css',
            'map': 'application/json',
        }[ext]

        response = HttpResponse(self.dash.serve_component_suites(*args, **kwargs), content_type=mimetype)
        # response['Cache-Control'] = 'public, max-age={}'.format(self.dash.config.components_cache_max_age)
        return response

    def _dash_routes(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        return JsonResponse(self.dash.serve_routes(*args, **kwargs))

    def _dash_reload_hash(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        return JsonResponse(self.dash.serve_reload_hash(*args, **kwargs))

    def _dash_default_favicon(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        response = HttpResponse(self.dash.serve_default_favicon(*args, **kwargs), content_type='image/x-icon')
        # response['Cache-Control'] = 'public, max-age={}'.format(self.dash.config.components_cache_max_age)
        return response

    @classmethod
    def serve_dash_index(cls, request, dash_name, *args, **kwargs):
        logger.debug('serve_dash_index')
        view = cls._dashes[dash_name](dash_base_url=request.path)
        view.setup(request, *args, **kwargs)
        return view.get(request, *args, **kwargs)   # pylint: disable=protected-access

    @classmethod
    def serve_dash_dependencies(cls, request, dash_name, *args, **kwargs):
        logger.debug('serve_dash_dependencies')
        view = cls._dashes[dash_name](dash_base_url=cls._dash_base_url(request.path, '/_dash-dependencies'))
        view.setup(request, *args, **kwargs)
        return view._dash_dependencies(request, *args, **kwargs)   # pylint: disable=protected-access

    @classmethod
    def serve_dash_layout(cls, request, dash_name, *args, **kwargs):
        logger.debug('serve_dash_layout')
        view = cls._dashes[dash_name](dash_base_url=cls._dash_base_url(request.path, '/_dash-layout'))
        view.setup(request, *args, **kwargs)
        return view._dash_layout(request, *args, **kwargs)   # pylint: disable=protected-access

    @classmethod
    @csrf_exempt
    def serve_dash_upd_component(cls, request, dash_name, *args, **kwargs):
        logger.debug('serve_dash_upd_component')
        view = cls._dashes[dash_name](dash_base_url=cls._dash_base_url(request.path, '/_dash-update-component'))
        view.setup(request, *args, **kwargs)
        return view._dash_upd_component(request, *args, **kwargs)   # pylint: disable=protected-access

    @classmethod
    def serve_dash_component_suites(cls, request, dash_name, *args, **kwargs):
        logger.debug('serve_dash_component_suites')
        view = cls._dashes[dash_name](dash_base_url=cls._dash_base_url(request.path, '/_dash-component-suites'))
        return view._dash_component_suites(request, *args, **kwargs)   # pylint: disable=protected-access

    @classmethod
    def serve_dash_routes(cls, request, dash_name, *args, **kwargs):
        logger.debug('serve_dash_routes')
        view = cls._dashes[dash_name](dash_base_url=cls._dash_base_url(request.path, '/_dash-routes'))
        return view._dash_routes(request, *args, **kwargs)   # pylint: disable=protected-access

    @classmethod
    def serve_reload_hash(cls, request, dash_name, *args, **kwargs):
        logger.debug('serve_reload_hash')
        view = cls._dashes[dash_name](dash_base_url=cls._dash_base_url(request.path, '/_reload-hash'))
        return view._dash_reload_hash(request, *args, **kwargs)   # pylint: disable=protected-access

    @classmethod
    def serve_default_favicon(cls, request, dash_name, *args, **kwargs):
        logger.debug('serve_default_favicon')
        view = cls._dashes[dash_name](dash_base_url=cls._dash_base_url(request.path, '/_favicon.ico'))
        return view._dash_default_favicon(request, *args, **kwargs)   # pylint: disable=protected-access
