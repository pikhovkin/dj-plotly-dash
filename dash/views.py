from __future__ import print_function

import json

import six

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from .dash import Dash, JsonResponse


__all__ = (
    'MetaDashView',
    'BaseDashView'
)


class MetaDashView(type):
    def __new__(cls, name, bases, attrs):
        new_cls = super(MetaDashView, cls).__new__(cls, name, bases, attrs)

        if new_cls.__dict__.get('dash_name', ''):
            new_cls._dashes[new_cls.__dict__['dash_name']] = new_cls   # pylint: disable=protected-access
            dash_prefix = getattr(new_cls, 'dash_prefix', '').strip()
            if dash_prefix:
                # pylint: disable=protected-access
                new_cls._dashes[dash_prefix + new_cls.__dict__['dash_name']] = new_cls

        return new_cls


class BaseDashView(six.with_metaclass(MetaDashView, View)):
    dash_template = None
    dash_base_url = '/'
    dash_name = None
    dash_meta_tags = None
    dash_external_scripts = None
    dash_external_stylesheets = None
    dash_assets_folder = None
    dash_assets_ignore = ''
    dash_prefix = ''  # For additional special urls
    dash_serve_dev_bundles = False
    dash_components = None
    _dashes = {}

    def __init__(self, **kwargs):
        dash_base_url = kwargs.pop('dash_base_url', self.dash_base_url)
        dash_template = kwargs.pop('dash_template', self.dash_template)
        dash_meta_tags = kwargs.pop('dash_meta_tags', self.dash_meta_tags)
        dash_external_scripts = kwargs.pop('dash_external_scripts', self.dash_external_scripts)
        dash_external_stylesheets = kwargs.pop('dash_external_stylesheets', self.dash_external_stylesheets)
        dash_assets_folder = kwargs.pop('dash_assets_folder', self.dash_assets_folder)
        dash_assets_ignore = kwargs.pop('dash_assets_ignore', self.dash_assets_ignore)
        dash_serve_dev_bundles = kwargs.pop('dash_serve_dev_bundles', self.dash_serve_dev_bundles)

        super(BaseDashView, self).__init__(**kwargs)

        dash = getattr(self, 'dash', None)
        if not isinstance(dash, Dash):
            self.dash = Dash()

        setattr(self.dash, '_res_affix', '_{}'.format(id(self.__class__)))

        if dash_base_url and self.dash.url_base_pathname != dash_base_url:
            self.dash.url_base_pathname = dash_base_url  # pylint: disable=access-member-before-definition
            # pylint: disable=access-member-before-definition
            self.dash.config.requests_pathname_prefix = dash_base_url

        if dash_template and self.dash.index_string != dash_template:
            self.dash.index_string = dash_template
        if dash_meta_tags and self.dash._meta_tags != dash_meta_tags:  # pylint: disable=protected-access
            # pylint: disable=protected-access, access-member-before-definition
            self.dash._meta_tags = dash_meta_tags
        # pylint: disable=protected-access
        if dash_external_scripts and self.dash._external_scripts != dash_external_scripts:
            # pylint: disable=protected-access, access-member-before-definition
            self.dash._external_scripts = dash_external_scripts
        # pylint: disable=protected-access
        if dash_external_stylesheets and self.dash._external_stylesheets != dash_external_stylesheets:
            # pylint: disable=protected-access, access-member-before-definition
            self.dash._external_stylesheets = dash_external_stylesheets
        # pylint: disable=protected-access
        if dash_assets_folder and self.dash._assets_folder != dash_assets_folder:
            # pylint: disable=protected-access, access-member-before-definition
            self.dash._assets_folder = dash_assets_folder
        if dash_assets_ignore and self.dash.assets_ignore != dash_assets_ignore:
            self.dash.assets_ignore = dash_assets_ignore
        if dash_serve_dev_bundles and self.dash._dev_tools.serve_dev_bundles != dash_serve_dev_bundles:
            self.dash._dev_tools.serve_dev_bundles = dash_serve_dev_bundles
        self.dash.components = set(self.dash_components or [])

    @staticmethod
    def _dash_base_url(path, part):
        return path[:path.find(part) + 1]

    def _dash_index(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        return HttpResponse(self.dash.index())

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

        return self.dash.update_component(output, inputs, state)

    def _dash_component_suites(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        ext = kwargs.get('path_in_package_dist', '').split('.')[-1]
        mimetype = {
            'js': 'application/JavaScript',
            'css': 'text/css'
        }[ext]

        response = HttpResponse(self.dash.serve_component_suites(*args, **kwargs), content_type=mimetype)
        response['Cache-Control'] = 'public, max-age={}'.format(self.dash.config.components_cache_max_age)

        return response

    def _dash_routes(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        return JsonResponse(self.dash.serve_routes(*args, **kwargs))

    def _dash_reload_hash(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        return JsonResponse(self.dash.serve_reload_hash(*args, **kwargs))

    @classmethod
    def serve_dash_index(cls, request, dash_name, *args, **kwargs):
        view = cls._dashes[dash_name](dash_base_url=request.path)
        return view._dash_index(request, *args, **kwargs)   # pylint: disable=protected-access

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
        view = cls._dashes[dash_name](dash_base_url=cls._dash_base_url(request.path, '/_dash-routes'))
        return view._dash_reload_hash(request, *args, **kwargs)   # pylint: disable=protected-access
