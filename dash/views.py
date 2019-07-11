from __future__ import print_function

import json

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from django.conf import settings
from django.utils import six
from django.core.exceptions import ImproperlyConfigured
from django.http import JsonResponse as BaseJsonResponse

import plotly

from .dash import Dash
from ._utils import generate_hash
from . import exceptions


__all__ = (
    'MetaDashView',
    'BaseDashView'
)


class JsonResponse(BaseJsonResponse):
    def __init__(self, data, encoder=plotly.utils.PlotlyJSONEncoder, safe=False,
                 json_dumps_params=None, **kwargs):
        super(JsonResponse, self).__init__(data, encoder=encoder, safe=safe,
                                           json_dumps_params=json_dumps_params, **kwargs)


class MetaDashView(type):
    def __new__(cls, name, bases, attrs):
        new_cls = super(MetaDashView, cls).__new__(cls, name, bases, attrs)

        if new_cls.__dict__.get('dash_name', ''):
            new_cls._dashes[new_cls.__dict__['dash_name']] = new_cls   # pylint: disable=protected-access
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


class BaseDashView(six.with_metaclass(MetaDashView, TemplateView)):
    _dashes = {}

    template_name = 'base.html'
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

    def __init__(self, **kwargs):
        dash_base_url = kwargs.pop('dash_base_url', self.dash_base_url)
        dash_meta_tags = kwargs.pop('dash_meta_tags', self.dash_meta_tags)
        dash_external_scripts = kwargs.pop('dash_external_scripts', self.dash_external_scripts)
        dash_external_stylesheets = kwargs.pop('dash_external_stylesheets', self.dash_external_stylesheets)
        dash_assets_folder = kwargs.pop('dash_assets_folder', self.dash_assets_folder)
        dash_assets_ignore = kwargs.pop('dash_assets_ignore', self.dash_assets_ignore)
        dash_serve_dev_bundles = kwargs.pop('dash_serve_dev_bundles', self.dash_serve_dev_bundles)
        dash_hot_reload = kwargs.pop('dash_hot_reload', self.dash_hot_reload)

        super(BaseDashView, self).__init__(**kwargs)

        dash = getattr(self, 'dash', None)
        if not isinstance(dash, Dash):
            self.dash = Dash()

        setattr(self.dash, '_res_affix', '_{}'.format(id(self.__class__)))

        if dash_base_url and self.dash.config.url_base_pathname != dash_base_url:
            self.dash.config.url_base_pathname = dash_base_url  # pylint: disable=access-member-before-definition
            # pylint: disable=access-member-before-definition
            self.dash.config.requests_pathname_prefix = dash_base_url

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

        self.dash.components = set(self.dash_components or [])
        self.dash._reload_hash = self._dash_hot_reload_hash  # pylint: disable=no-member

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context.update(**self._dash_index(request, *args, **kwargs))
        return self.render_to_response(context)

    @staticmethod
    def _dash_base_url(path, part):
        return path[:path.find(part) + 1]

    def _dash_index(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        return self.dash.index()

    def _dash_dependencies(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        return JsonResponse(self.dash.dependencies())

    def _dash_layout(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        # TODO - Set browser cache limit - pass hash into frontend
        return JsonResponse(self.dash._layout_value())  # pylint: disable=protected-access

    def _dash_upd_component(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        body = json.loads(request.body)

        output = body['output']
        inputs = body.get('inputs', [])
        state = body.get('state', [])
        changed_props = body.get('changedPropIds', [])

        self.response = JsonResponse({})  # pylint: disable=attribute-defined-outside-init
        output_value, response = self.dash.update_component(output, inputs, state, changed_props)
        try:
            self.response.content = JsonResponse(response).content
        except TypeError:
            self.dash._validate_callback_output(output_value, output)  # pylint: disable=protected-access
            raise exceptions.InvalidCallbackReturnValue('''
            The callback for property `{property:s}`
            of component `{id:s}` returned a value
            which is not JSON serializable.

            In general, Dash properties can only be
            dash components, strings, dictionaries, numbers, None,
            or lists of those.
            '''.format(
                property=output.component_property,
                id=output.component_id
            ).replace('    ', ''))

        return self.response

    def _dash_component_suites(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        ext = kwargs.get('path_in_package_dist', '').split('.')[-1]
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
        view = cls._dashes[dash_name](dash_base_url=request.path)
        view.request = request
        view.args = args
        view.kwargs = kwargs
        return view.get(request, *args, **kwargs)   # pylint: disable=protected-access

    @classmethod
    def serve_dash_dependencies(cls, request, dash_name, *args, **kwargs):
        view = cls._dashes[dash_name](dash_base_url=cls._dash_base_url(request.path, '/_dash-dependencies'))
        return view._dash_dependencies(request, *args, **kwargs)   # pylint: disable=protected-access

    @classmethod
    def serve_dash_layout(cls, request, dash_name, *args, **kwargs):
        view = cls._dashes[dash_name](dash_base_url=cls._dash_base_url(request.path, '/_dash-layout'))
        return view._dash_layout(request, *args, **kwargs)   # pylint: disable=protected-access

    @classmethod
    @csrf_exempt
    def serve_dash_upd_component(cls, request, dash_name, *args, **kwargs):
        view = cls._dashes[dash_name](dash_base_url=cls._dash_base_url(request.path, '/_dash-update-component'))
        return view._dash_upd_component(request, *args, **kwargs)   # pylint: disable=protected-access

    @classmethod
    def serve_dash_component_suites(cls, request, dash_name, *args, **kwargs):
        view = cls._dashes[dash_name](dash_base_url=cls._dash_base_url(request.path, '/_dash-component-suites'))
        return view._dash_component_suites(request, *args, **kwargs)   # pylint: disable=protected-access

    @classmethod
    def serve_dash_routes(cls, request, dash_name, *args, **kwargs):
        view = cls._dashes[dash_name](dash_base_url=cls._dash_base_url(request.path, '/_dash-routes'))
        return view._dash_routes(request, *args, **kwargs)   # pylint: disable=protected-access

    @classmethod
    def serve_reload_hash(cls, request, dash_name, *args, **kwargs):
        view = cls._dashes[dash_name](dash_base_url=cls._dash_base_url(request.path, '/_reload-hash'))
        return view._dash_reload_hash(request, *args, **kwargs)   # pylint: disable=protected-access

    @classmethod
    def serve_default_favicon(cls, request, dash_name, *args, **kwargs):
        view = cls._dashes[dash_name](dash_base_url=cls._dash_base_url(request.path, '/_favicon.ico'))
        return view._dash_default_favicon(request, *args, **kwargs)   # pylint: disable=protected-access
