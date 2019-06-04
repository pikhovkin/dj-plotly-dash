from __future__ import print_function

import os
import sys
import collections
import importlib
import json
import pkgutil
from functools import wraps

import plotly
import dash_renderer

from django.contrib.staticfiles.utils import get_files
from django.contrib.staticfiles.storage import staticfiles_storage
from django.http import JsonResponse as BaseJsonResponse
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.safestring import mark_safe

from .dependencies import Event, Input, Output, State
from .resources import Scripts, Css
from .development.base_component import Component
from . import exceptions
from ._utils import AttributeDict as _AttributeDict
from ._utils import format_tag as _format_tag


__all__ = (
    'Dash',
)


class JsonResponse(BaseJsonResponse):
    def __init__(self, data, encoder=plotly.utils.PlotlyJSONEncoder, safe=False,
                 json_dumps_params=None, **kwargs):
        super(JsonResponse, self).__init__(data, encoder=encoder, safe=safe,
                                           json_dumps_params=json_dumps_params, **kwargs)


_app_entry = '''
<div id="react-entry-point">
    <div class="_dash-loading">
        Loading...
    </div>
</div>
'''


# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-arguments, too-many-locals
class Dash(object):
    # pylint: disable=unused-argument
    def __init__(self, url_base_pathname='/',
                 meta_tags=None,
                 external_scripts=None,
                 external_stylesheets=None,
                 assets_folder=None,
                 assets_ignore='',
                 suppress_callback_exceptions=True,
                 components_cache_max_age=None,
                 serve_dev_bundles=False,
                 components=None,
                 **kwargs):
        self._assets_folder = assets_folder

        self.components = components

        self.url_base_pathname = url_base_pathname
        self.config = _AttributeDict({
            'suppress_callback_exceptions': suppress_callback_exceptions or False,
            'routes_pathname_prefix': url_base_pathname,
            'requests_pathname_prefix': url_base_pathname,
            'assets_external_path': None,
            'components_cache_max_age': components_cache_max_age or 2678400
        })

        # list of dependencies
        self.callback_map = {}

        self._meta_tags = meta_tags or []
        self._favicon = None

        # static files from the packages
        self.css = Css()
        self.scripts = Scripts()

        self._external_scripts = external_scripts or []
        self._external_stylesheets = external_stylesheets or []

        self.assets_ignore = assets_ignore

        self.registered_paths = collections.defaultdict(set)

        self._layout = None
        self._cached_layout = None
        self.routes = []

        self._dev_tools = _AttributeDict({
            'serve_dev_bundles': serve_dev_bundles,
            'hot_reload': False,
            'hot_reload_interval': 3000,
            'hot_reload_watch_interval': 0.5,
            'hot_reload_max_retry': 8
        })

        # hot reload
        self._reload_hash = None

    @property
    def layout(self):
        return self._layout

    def _layout_value(self):
        if isinstance(self._layout, collections.Callable):
            self._cached_layout = self._layout()
        else:
            self._cached_layout = self._layout
        return self._cached_layout

    @layout.setter
    def layout(self, value):
        if (not isinstance(value, Component) and
                not isinstance(value, collections.Callable)):
            raise exceptions.NoLayoutException(
                ''
                'Layout must be a dash component '
                'or a function that returns '
                'a dash component.')

        self._layout = value

        self._validate_layout()

        layout_value = self._layout_value()
        # pylint: disable=protected-access
        self.css._update_layout(layout_value)
        self.scripts._update_layout(layout_value)

    def _config(self):
        config = {
            'url_base_pathname': self.url_base_pathname,
            'requests_pathname_prefix': self.config['requests_pathname_prefix']
        }
        if self._dev_tools.hot_reload:
            config['hot_reload'] = {
                'interval': self._dev_tools.hot_reload_interval,
                'max_retry': self._dev_tools.hot_reload_max_retry
            }
        return config

    def serve_reload_hash(self, *args, **kwargs):
        return {
            'reloadHash': self._reload_hash,
            'hard': True,
            'packages': list(self.registered_paths.keys()),
            'files': []
        }

    def serve_routes(self, *args, **kwargs):  # pylint: disable=unused-argument
        return self.routes

    def _collect_and_register_resources(self, resources):
        # now needs the app context.
        # template in the necessary component suite JS bundles
        # add the version number of the package as a query parameter
        # for cache busting
        def _relative_url_path(path_prefix, relative_package_path='', namespace=''):

            module_path = os.path.join(
                os.path.dirname(sys.modules[namespace].__file__),
                relative_package_path)

            modified = int(os.stat(module_path).st_mtime)

            return '{}_dash-component-suites/{}/{}?v={}&m={}'.format(
                path_prefix,
                namespace,
                relative_package_path,
                importlib.import_module(namespace).__version__,
                modified
            )

        try:
            DASH_COMPONENT_SUITES_URL = getattr(settings, 'DASH_COMPONENT_SUITES_URL', '')
        except ImproperlyConfigured:
            DASH_COMPONENT_SUITES_URL = ''

        path_prefix = DASH_COMPONENT_SUITES_URL or self.config['requests_pathname_prefix']

        srcs = []
        for resource in resources:
            is_dynamic_resource = resource.get('dynamic', False)

            if 'relative_package_path' in resource:
                paths = resource['relative_package_path']
                paths = [paths] if isinstance(paths, str) else paths

                for rel_path in paths:
                    self.registered_paths[resource['namespace']].add(rel_path)

                    if not is_dynamic_resource:
                        srcs.append(_relative_url_path(
                            path_prefix,
                            relative_package_path=rel_path,
                            namespace=resource['namespace']
                        ))
            elif 'external_url' in resource:
                if not is_dynamic_resource:
                    if isinstance(resource['external_url'], str):
                        srcs.append(resource['external_url'])
                    else:
                        for url in resource['external_url']:
                            srcs.append(url)
            elif 'absolute_path' in resource:
                raise Exception(
                    'Serving files from absolute_path isn\'t supported yet'
                )
            elif 'asset_path' in resource:
                static_url = resource['asset_path']
                # Add a bust query param
                static_url += '?m={}'.format(resource['ts'])
                srcs.append(static_url)
        return srcs

    def _generate_css_dist_html(self):
        links = self._external_stylesheets + \
                self._collect_and_register_resources(self.css.get_all_css(affix=getattr(self, '_res_affix', ''),
                                                                          module_names=self.components))

        return '\n'.join([
            _format_tag('link', link, opened=True)
            if isinstance(link, dict)
            else '<link rel="stylesheet" href="{}">'.format(link)
            for link in links
        ])

    def _generate_scripts_html(self):
        # Dash renderer has dependencies like React which need to be rendered
        # before every other script. However, the dash renderer bundle
        # itself needs to be rendered after all of the component's
        # scripts have rendered.
        # The rest of the scripts can just be loaded after React but before
        # dash renderer.
        # pylint: disable=protected-access
        srcs = self._collect_and_register_resources(
            self.scripts._resources._filter_resources(
                dash_renderer._js_dist_dependencies,
                dev_bundles=self._dev_tools.serve_dev_bundles
            )) + self._external_scripts + self._collect_and_register_resources(
                self.scripts.get_all_scripts(
                    affix=getattr(self, '_res_affix', ''),
                    module_names=self.components,
                    dev_bundles=self._dev_tools.serve_dev_bundles) +
                self.scripts._resources._filter_resources(
                    dash_renderer._js_dist,
                    dev_bundles=self._dev_tools.serve_dev_bundles
                ))

        return '\n'.join([
            _format_tag('script', src)
            if isinstance(src, dict)
            else '<script src="{}"></script>'.format(src)
            for src in srcs
        ])

    def _generate_config_html(self, **kwargs):
        config = self._config()
        config.update(kwargs)
        return (
            '<script id="_dash-config" type="application/json">'
            '{}'
            '</script>'
        ).format(json.dumps(config, cls=plotly.utils.PlotlyJSONEncoder))

    def _generate_meta_html(self):
        has_ie_compat = any(
            x.get('http-equiv', '') == 'X-UA-Compatible'
            for x in self._meta_tags)
        has_charset = any('charset' in x for x in self._meta_tags)

        tags = []
        if not has_ie_compat:
            tags.append(
                '<meta http-equiv="X-UA-Compatible" content="IE=edge">'
            )
        if not has_charset:
            tags.append('<meta charset="UTF-8">')

        tags = tags + [
            _format_tag('meta', x, opened=True) for x in self._meta_tags
        ]

        return '\n      '.join(tags)

    # pylint: disable=unused-argument
    def serve_component_suites(self, package_name, path_in_package_dist, *args, **kwargs):
        """ Serve the JS bundles for each package
        """
        if package_name not in self.registered_paths:
            raise exceptions.DependencyException(
                'Error loading dependency.\n'
                '"{}" is not a registered library.\n'
                'Registered libraries are: {}'.format(package_name, list(self.registered_paths.keys())))

        elif path_in_package_dist not in self.registered_paths[package_name]:
            raise exceptions.DependencyException(
                '"{}" is registered but the path requested is not valid.\n'
                'The path requested: "{}"\n'
                'List of registered paths: {}'.format(package_name, path_in_package_dist, self.registered_paths))

        return pkgutil.get_data(package_name, path_in_package_dist)

    def index(self, *args, **kwargs):  # pylint: disable=unused-argument
        if self._assets_folder:
            self._walk_assets_directory()

        scripts = self._generate_scripts_html()
        css = self._generate_css_dist_html()
        config = self._generate_config_html()
        metas = self._generate_meta_html()
        title = getattr(self, 'title', 'Dash')

        if self._favicon:
            favicon = '<link rel="icon" type="image/x-icon" href="{}">'.format(self._favicon)
        else:
            favicon = ''

        # if self._favicon:
        #     favicon_mod_time = os.path.getmtime(
        #         os.path.join(self._assets_folder, self._favicon))
        #     favicon_url = self.get_asset_url(self._favicon) + '?m={}'.format(
        #         favicon_mod_time
        #     )
        # else:
        #     favicon_url = '{}_favicon.ico'.format(
        #         self.config.requests_pathname_prefix)
        #
        # favicon = _format_tag('link', {
        #     'rel': 'icon',
        #     'type': 'image/x-icon',
        #     'href': favicon_url
        # }, opened=True)

        return dict(
            metas=mark_safe(metas),
            title=mark_safe(title),
            css=mark_safe(css),
            config=mark_safe(config),
            scripts=mark_safe(scripts),
            favicon=mark_safe(favicon),
            app_entry=mark_safe(_app_entry)
        )

    def dependencies(self, *args, **kwargs):  # pylint: disable=unused-argument
        return [
            {
                'output': {
                    'id': k.split('.')[0],
                    'property': k.split('.')[1]
                },
                'inputs': v['inputs'],
                'state': v['state'],
                'events': v['events']
            } for k, v in self.callback_map.items()
        ]

    # pylint: disable=unused-argument, no-self-use
    def react(self, *args, **kwargs):
        raise exceptions.DashException(
            'Yo! `react` is no longer used. \n'
            'Use `callback` instead. `callback` has a new syntax too, '
            'so make sure to call `help(app.callback)` to learn more.')

    def _validate_callback(self, output, inputs, state, events):
        # pylint: disable=too-many-branches
        layout = self._cached_layout or self._layout_value()

        if (layout is None and
                not self.config.first('suppress_callback_exceptions',
                                      'supress_callback_exceptions')):
            # Without a layout, we can't do validation on the IDs and
            # properties of the elements in the callback.
            raise exceptions.LayoutIsNotDefined('''
                Attempting to assign a callback to the application but
                the `layout` property has not been assigned.
                Assign the `layout` property before assigning callbacks.
                Alternatively, suppress this warning by setting
                `app.config['suppress_callback_exceptions']=True`
            '''.replace('    ', ''))

        for args, obj, name in [([output], Output, 'Output'),
                                (inputs, Input, 'Input'),
                                (state, State, 'State'),
                                (events, Event, 'Event')]:

            if not isinstance(args, list):
                raise exceptions.IncorrectTypeException(
                    'The {} argument `{}` is '
                    'not a list of `dash.dependencies.{}`s.'.format(
                        name.lower(), str(args), name
                    ))

            for arg in args:
                if not isinstance(arg, obj):
                    raise exceptions.IncorrectTypeException(
                        'The {} argument `{}` is '
                        'not of type `dash.{}`.'.format(
                            name.lower(), str(arg), name
                        ))

                if (not self.config.first('suppress_callback_exceptions',
                                          'supress_callback_exceptions') and
                        arg.component_id not in layout and
                        arg.component_id != getattr(layout, 'id', None)):
                    raise exceptions.NonExistantIdException('''
                        Attempting to assign a callback to the
                        component with the id "{}" but no
                        components with id "{}" exist in the
                        app\'s layout.\n\n
                        Here is a list of IDs in layout:\n{}\n\n
                        If you are assigning callbacks to components
                        that are generated by other callbacks
                        (and therefore not in the initial layout), then
                        you can suppress this exception by setting
                        `app.config['suppress_callback_exceptions']=True`.
                    '''.format(
                        arg.component_id,
                        arg.component_id,
                        list(layout.keys()) + (
                            [] if not hasattr(layout, 'id') else
                            [layout.id]
                        )
                    ).replace('    ', ''))

                if not self.config.first('suppress_callback_exceptions',
                                         'supress_callback_exceptions'):

                    if getattr(layout, 'id', None) == arg.component_id:
                        component = layout
                    else:
                        component = layout[arg.component_id]

                    if (hasattr(arg, 'component_property') and
                            arg.component_property not in
                            component.available_properties and not
                            any(arg.component_property.startswith(w) for w in
                                component.available_wildcard_properties)):
                        raise exceptions.NonExistantPropException('''
                            Attempting to assign a callback with
                            the property "{}" but the component
                            "{}" doesn't have "{}" as a property.\n
                            Here is a list of the available properties in "{}":
                            {}
                        '''.format(
                            arg.component_property,
                            arg.component_id,
                            arg.component_property,
                            arg.component_id,
                            component.available_properties).replace(
                                '    ', ''))

                    if (hasattr(arg, 'component_event') and
                            arg.component_event not in
                            component.available_events):
                        raise exceptions.NonExistantEventException('''
                            Attempting to assign a callback with
                            the event "{}" but the component
                            "{}" doesn't have "{}" as an event.\n
                            Here is a list of the available events in "{}":
                            {}
                        '''.format(
                            arg.component_event,
                            arg.component_id,
                            arg.component_event,
                            arg.component_id,
                            component.available_events).replace('    ', ''))

        if state and not events and not inputs:
            raise exceptions.MissingEventsException('''
                This callback has {} `State` {}
                but no `Input` elements or `Event` elements.\n
                Without `Input` or `Event` elements, this callback
                will never get called.\n
                (Subscribing to input components will cause the
                callback to be called whenever their values
                change and subscribing to an event will cause the
                callback to be called whenever the event is fired.)
            '''.format(
                len(state),
                'elements' if len(state) > 1 else 'element'
            ).replace('    ', ''))

        if '.' in output.component_id:
            raise exceptions.IDsCantContainPeriods('''The Output element
            `{}` contains a period in its ID.
            Periods are not allowed in IDs right now.'''.format(
                output.component_id
            ))

        callback_id = '{}.{}'.format(
            output.component_id, output.component_property)
        if callback_id in self.callback_map:
            raise exceptions.CantHaveMultipleOutputs('''
                You have already assigned a callback to the output
                with ID "{}" and property "{}". An output can only have
                a single callback function. Try combining your inputs and
                callback functions together into one function.
            '''.format(
                output.component_id,
                output.component_property).replace('    ', ''))

    def _validate_callback_output(self, output_value, output):
        valid = [str, dict, int, float, type(None), Component]

        def _raise_invalid(bad_val, outer_val, bad_type, path, index=None,
                           toplevel=False):
            outer_id = "(id={:s})".format(outer_val.id) \
                if getattr(outer_val, 'id', False) else ''
            outer_type = type(outer_val).__name__
            raise exceptions.InvalidCallbackReturnValue('''
            The callback for property `{property:s}` of component `{id:s}`
            returned a {object:s} having type `{type:s}`
            which is not JSON serializable.

            {location_header:s}{location:s}
            and has string representation
            `{bad_val}`

            In general, Dash properties can only be
            dash components, strings, dictionaries, numbers, None,
            or lists of those.
            '''.format(
                property=output.component_property,
                id=output.component_id,
                object='tree with one value' if not toplevel else 'value',
                type=bad_type,
                location_header=(
                    'The value in question is located at'
                    if not toplevel else
                    '''The value in question is either the only value returned,
                    or is in the top level of the returned list,'''
                ),
                location=(
                    "\n" +
                    ("[{:d}] {:s} {:s}".format(index, outer_type, outer_id)
                     if index is not None
                     else ('[*] ' + outer_type + ' ' + outer_id))
                    + "\n" + path + "\n"
                ) if not toplevel else '',
                bad_val=bad_val).replace('    ', ''))

        def _value_is_valid(val):
            return (
                # pylint: disable=unused-variable
                any([isinstance(val, x) for x in valid]) or
                type(val).__name__ == 'unicode'
            )

        def _validate_value(val, index=None):
            # val is a Component
            if isinstance(val, Component):
                for p, j in val.traverse_with_paths():
                    # check each component value in the tree
                    if not _value_is_valid(j):
                        _raise_invalid(
                            bad_val=j,
                            outer_val=val,
                            bad_type=type(j).__name__,
                            path=p,
                            index=index
                        )

                    # Children that are not of type Component or
                    # list/tuple not returned by traverse
                    child = getattr(j, 'children', None)
                    if not isinstance(child, (tuple,
                                              collections.MutableSequence)):
                        if child and not _value_is_valid(child):
                            _raise_invalid(
                                bad_val=child,
                                outer_val=val,
                                bad_type=type(child).__name__,
                                path=p + "\n" + "[*] " + type(child).__name__,
                                index=index
                            )

                # Also check the child of val, as it will not be returned
                child = getattr(val, 'children', None)
                if not isinstance(child, (tuple, collections.MutableSequence)):
                    if child and not _value_is_valid(child):
                        _raise_invalid(
                            bad_val=child,
                            outer_val=val,
                            bad_type=type(child).__name__,
                            path=type(child).__name__,
                            index=index
                        )

            # val is not a Component, but is at the top level of tree
            else:
                if not _value_is_valid(val):
                    _raise_invalid(
                        bad_val=val,
                        outer_val=type(val).__name__,
                        bad_type=type(val).__name__,
                        path='',
                        index=index,
                        toplevel=True
                    )

        if isinstance(output_value, list):
            for i, val in enumerate(output_value):
                _validate_value(val, index=i)
        else:
            _validate_value(output_value)

    # TODO - Update nomenclature.
    # "Parents" and "Children" should refer to the DOM tree
    # and not the dependency tree.
    # The dependency tree should use the nomenclature
    # "observer" and "controller".
    # "observers" listen for changes from their "controllers". For example,
    # if a graph depends on a dropdown, the graph is the "observer" and the
    # dropdown is a "controller". In this case the graph's "dependency" is
    # the dropdown.
    # TODO - Check this map for recursive or other ill-defined non-tree
    # relationships
    # pylint: disable=dangerous-default-value
    def callback(self, output, inputs=[], state=[], events=[]):
        self._validate_callback(output, inputs, state, events)

        callback_id = '{}.{}'.format(
            output.component_id, output.component_property
        )
        self.callback_map[callback_id] = {
            'inputs': [
                {'id': c.component_id, 'property': c.component_property}
                for c in inputs
            ],
            'state': [
                {'id': c.component_id, 'property': c.component_property}
                for c in state
            ],
            'events': [
                {'id': c.component_id, 'event': c.component_event}
                for c in events
            ]
        }

        def wrap_func(func):
            @wraps(func)
            def add_context(*args, **kwargs):
                output_value = func(*args, **kwargs)
                response = {
                    'response': {
                        'props': {
                            output.component_property: output_value
                        }
                    }
                }

                try:
                    return JsonResponse(response)
                except TypeError:
                    self._validate_callback_output(output_value, output)
                    raise exceptions.InvalidCallbackReturnValue('''
                    The callback for property `{property:s}`
                    of component `{id:s}` returned a value
                    which is not JSON serializable.

                    In general, Dash properties can only be
                    dash components, strings, dictionaries, numbers, None,
                    or lists of those.
                    '''.format(property=output.component_property,
                               id=output.component_id))

            self.callback_map[callback_id]['callback'] = add_context

            return add_context

        return wrap_func

    def update_component(self, output, inputs, state, **kwargs):
        target_id = '{}.{}'.format(output['id'], output['property'])
        args = []
        for component_registration in self.callback_map[target_id]['inputs']:
            args.append([
                c.get('value', None) for c in inputs if
                c['property'] == component_registration['property'] and
                c['id'] == component_registration['id']
            ][0])

        for component_registration in self.callback_map[target_id]['state']:
            args.append([
                c.get('value', None) for c in state if
                c['property'] == component_registration['property'] and
                c['id'] == component_registration['id']
            ][0])

        return self.callback_map[target_id]['callback'](*args, **kwargs)

    def _validate_layout(self):
        if self.layout is None:
            raise exceptions.NoLayoutException(
                ''
                'The layout was `None` '
                'at the time that `run_server` was called. '
                'Make sure to set the `layout` attribute of your application '
                'before running the server.')

        to_validate = self._layout_value()

        layout_id = getattr(self.layout, 'id', None)

        component_ids = {layout_id} if layout_id else set()
        for component in to_validate.traverse():
            component_id = getattr(component, 'id', None)
            if component_id and component_id in component_ids:
                raise exceptions.DuplicateIdError(
                    'Duplicate component id found'
                    ' in the initial layout: `{}`'.format(component_id))
            component_ids.add(component_id)

    def _walk_assets_directory(self):
        ignore_filter = [self.assets_ignore] if self.assets_ignore else None

        def add_resource(p, filepath):
            res = {'asset_path': p, 'filepath': filepath}
            if self.config.assets_external_path:
                res['external_url'] = '{}{}'.format(self.config.assets_external_path, path)
            return res

        files = list(get_files(staticfiles_storage, ignore_patterns=ignore_filter, location=self._assets_folder))
        for f in sorted(files):
            path = staticfiles_storage.url(f)
            full = staticfiles_storage.path(f)

            if f.endswith('js'):
                self.scripts.append_script(add_resource(path, full))
            elif f.endswith('css'):
                self.css.append_css(add_resource(path, full))
            elif f.endswith('favicon.ico'):
                self._favicon = path
