from __future__ import print_function

import itertools
import os
import sys
import collections
import importlib
import json
import pkgutil
import pprint

from functools import wraps

import plotly
import dash_renderer

from django.contrib.staticfiles.utils import get_files
from django.contrib.staticfiles.storage import staticfiles_storage
from django.http import JsonResponse as BaseJsonResponse
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.safestring import mark_safe

from .dependencies import Input, Output, State
from .resources import Scripts, Css
from .development.base_component import Component
from . import exceptions
from ._utils import AttributeDict as _AttributeDict
from ._utils import format_tag as _format_tag
from ._utils import patch_collections_abc as _patch_collections_abc
from ._utils import create_callback_id as _create_callback_id


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


class _NoUpdate(object):
    # pylint: disable=too-few-public-methods
    pass


# Singleton signal to not update an output, alternative to PreventUpdate
no_update = _NoUpdate()


# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-arguments, too-many-locals
class Dash(object):
    # pylint: disable=unused-argument
    def __init__(self,
                 url_base_pathname='/',
                 meta_tags=None,
                 external_scripts=None,
                 external_stylesheets=None,
                 assets_folder=None,
                 assets_ignore='',
                 suppress_callback_exceptions=True,
                 components_cache_max_age=None,
                 serve_dev_bundles=False,
                 components=None,
                 show_undo_redo=False,
                 plugins=None,
                 **kwargs):
        self._assets_folder = assets_folder

        self.components = components

        self.url_base_pathname = url_base_pathname
        self.config = _AttributeDict({
            'suppress_callback_exceptions': suppress_callback_exceptions or False,
            'routes_pathname_prefix': url_base_pathname,
            'requests_pathname_prefix': url_base_pathname,
            'assets_external_path': None,
            'components_cache_max_age': components_cache_max_age or 2678400,
            'show_undo_redo': show_undo_redo
        })

        # list of dependencies
        self.callback_map = {}

        self._meta_tags = meta_tags or []
        self._favicon = ''

        # default renderer string
        self.renderer = 'var renderer = new DashRenderer();'

        # static files from the packages
        self.css = Css()
        self.scripts = Scripts()

        self._external_scripts = external_scripts or []
        self._external_stylesheets = external_stylesheets or []

        self.assets_ignore = assets_ignore

        self.registered_paths = collections.defaultdict(set)

        # urls
        self.routes = []

        self._layout = None
        self._cached_layout = None
        self._dev_tools = _AttributeDict({
            'serve_dev_bundles': serve_dev_bundles,
            'hot_reload': False,
            'hot_reload_interval': 3000,
            'hot_reload_watch_interval': 0.5,
            'hot_reload_max_retry': 8,
            'ui': False,
            'props_check': False,
        })

        # hot reload
        self._reload_hash = None

        if isinstance(plugins, _patch_collections_abc('Iterable')):
            for plugin in plugins:
                plugin.plug(self)

    @property
    def layout(self):
        return self._layout

    def _layout_value(self):
        if isinstance(self._layout, _patch_collections_abc('Callable')):
            self._cached_layout = self._layout()
        else:
            self._cached_layout = self._layout
        return self._cached_layout

    @layout.setter
    def layout(self, value):
        if (not isinstance(value, Component) and
                not isinstance(value, _patch_collections_abc('Callable'))):
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
            'requests_pathname_prefix': self.config.requests_pathname_prefix,
            'ui': self._dev_tools.ui,
            'props_check': self._dev_tools.props_check,
            'show_undo_redo': self.config.show_undo_redo
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

    def _generate_renderer(self):
        return (
            '<script id="_dash-renderer" type="application/javascript">'
            '{}'
            '</script>'
        ).format(self.renderer)

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

        if path_in_package_dist not in self.registered_paths[package_name]:
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
        renderer = self._generate_renderer()
        title = getattr(self, 'title', 'Dash')

        if self._favicon:
            favicon_mod_time = os.path.getmtime(
                os.path.join(self._assets_folder, self._favicon))
            favicon_url = self._favicon + '?m={}'.format(
                favicon_mod_time
            )
        else:
            favicon_url = '{}_favicon.ico'.format(
                self.config.requests_pathname_prefix)

        favicon = _format_tag('link', {
            'rel': 'icon',
            'type': 'image/x-icon',
            'href': favicon_url
        }, opened=True)

        return dict(
            metas=mark_safe(metas),
            favicon=mark_safe(favicon),
            title=mark_safe(title),
            css=mark_safe(css),
            config=mark_safe(config),
            scripts=mark_safe(scripts),
            app_entry=mark_safe(_app_entry),
            renderer=mark_safe(renderer)
        )

    def dependencies(self, *args, **kwargs):  # pylint: disable=unused-argument
        return [
            {
                'output': k,
                'inputs': v['inputs'],
                'state': v['state'],
                'clientside_function': v.get('clientside_function', None)
            } for k, v in self.callback_map.items()
        ]

    def _validate_callback(self, output, inputs, state):
        # pylint: disable=too-many-branches
        layout = self._cached_layout or self._layout_value()
        is_multi = isinstance(output, (list, tuple))

        for i in inputs:
            bad = None
            if is_multi:
                for o in output:
                    if o == i:
                        bad = o
            else:
                if output == i:
                    bad = output
            if bad:
                raise exceptions.SameInputOutputException(
                    'Same output and input: {}'.format(bad)
                )

        if is_multi:
            if len(set(output)) != len(output):
                raise exceptions.DuplicateCallbackOutput(
                    'Same output was used in a'
                    ' multi output callback!\n Duplicates:\n {}'.format(
                        ',\n'.join(
                            k for k, v in
                            ((str(x), output.count(x)) for x in output)
                            if v > 1
                        )
                    )
                )

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

        for args, obj, name in [(output if isinstance(output, (list, tuple))
                                 else [output],
                                 (Output, list, tuple),
                                 'Output'),
                                (inputs, Input, 'Input'),
                                (state, State, 'State')]:

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

                invalid_characters = ['.']
                if any(x in arg.component_id for x in invalid_characters):
                    raise exceptions.InvalidComponentIdError('''The element
                    `{}` contains {} in its ID.
                    Periods are not allowed in IDs right now.'''.format(
                        arg.component_id,
                        invalid_characters
                    ))

                if (not self.config.first('suppress_callback_exceptions',
                                          'supress_callback_exceptions') and
                        arg.component_id not in layout and
                        arg.component_id != getattr(layout, 'id', None)):
                    raise exceptions.NonExistentIdException('''
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
                        raise exceptions.NonExistentPropException('''
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

                    if hasattr(arg, 'component_event'):
                        raise exceptions.NonExistentEventException('''
                            Events have been removed.
                            Use the associated property instead.
                        ''')

        if state and not inputs:
            raise exceptions.MissingInputsException('''
                This callback has {} `State` {}
                but no `Input` elements.\n
                Without `Input` elements, this callback
                will never get called.\n
                (Subscribing to input components will cause the
                callback to be called whenever their values change.)
            '''.format(
                len(state),
                'elements' if len(state) > 1 else 'element'
            ).replace('    ', ''))

        callback_id = _create_callback_id(output)

        callbacks = set(itertools.chain(*(
            x[2:-2].split('...')
            if x.startswith('..')
            else [x]
            for x in self.callback_map
        )))
        ns = {
            'duplicates': set()
        }
        if is_multi:
            def duplicate_check():
                ns['duplicates'] = callbacks.intersection(
                    str(y) for y in output
                )
                return ns['duplicates']
        else:
            def duplicate_check():
                return callback_id in callbacks
        if duplicate_check():
            if is_multi:
                msg = '''
                Multi output {} contains an `Output` object
                that was already assigned.
                Duplicates:
                {}
                '''.format(
                    callback_id,
                    pprint.pformat(ns['duplicates'])
                )
            else:
                msg = '''
                You have already assigned a callback to the output
                with ID "{}" and property "{}". An output can only have
                a single callback function. Try combining your inputs and
                callback functions together into one function.
                '''.format(
                    output.component_id,
                    output.component_property
                ).replace('    ', '')
            raise exceptions.DuplicateCallbackOutput(msg)

    @staticmethod
    def _validate_callback_output(output_value, output):
        valid = [str, dict, int, float, type(None), Component]

        def _raise_invalid(bad_val, outer_val, bad_type, path, index=None,
                           toplevel=False):
            outer_id = "(id={:s})".format(outer_val.id) \
                if getattr(outer_val, 'id', False) else ''
            outer_type = type(outer_val).__name__
            raise exceptions.InvalidCallbackReturnValue('''
            The callback for `{output:s}`
            returned a {object:s} having type `{type:s}`
            which is not JSON serializable.

            {location_header:s}{location:s}
            and has string representation
            `{bad_val}`

            In general, Dash properties can only be
            dash components, strings, dictionaries, numbers, None,
            or lists of those.
            '''.format(
                output=repr(output),
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
                # pylint: disable=protected-access
                for p, j in val._traverse_with_paths():
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

    # pylint: disable=dangerous-default-value
    def clientside_callback(
            self, clientside_function, output, inputs=[], state=[]):
        """
        Create a callback that updates the output by calling a clientside
        (JavaScript) function instead of a Python function.

        Unlike `@app.calllback`, `clientside_callback` is not a decorator:
        it takes a
        `dash.dependencies.ClientsideFunction(namespace, function_name)`
        argument that describes which JavaScript function to call
        (Dash will look for the JavaScript function at
        `window[namespace][function_name]`).

        For example:
        ```
        app.clientside_callback(
            ClientsideFunction('my_clientside_library', 'my_function'),
            Output('my-div' 'children'),
            [Input('my-input', 'value'),
             Input('another-input', 'value')]
        )
        ```

        With this signature, Dash's front-end will call
        `window.my_clientside_library.my_function` with the current
        values of the `value` properties of the components
        `my-input` and `another-input` whenever those values change.

        Include a JavaScript file by including it your `assets/` folder.
        The file can be named anything but you'll need to assign the
        function's namespace to the `window`. For example, this file might
        look like:
        ```
        window.my_clientside_library = {
            my_function: function(input_value_1, input_value_2) {
                return (
                    parseFloat(input_value_1, 10) +
                    parseFloat(input_value_2, 10)
                );
            }
        }
        ```
        """
        self._validate_callback(output, inputs, state)
        callback_id = _create_callback_id(output)

        self.callback_map[callback_id] = {
            'inputs': [
                {'id': c.component_id, 'property': c.component_property}
                for c in inputs
            ],
            'state': [
                {'id': c.component_id, 'property': c.component_property}
                for c in state
            ],
            'clientside_function': {
                'namespace': clientside_function.namespace,
                'function_name': clientside_function.function_name
            }
        }

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
    def callback(self, output, inputs=[], state=[]):
        self._validate_callback(output, inputs, state)

        callback_id = _create_callback_id(output)
        multi = isinstance(output, (list, tuple))

        self.callback_map[callback_id] = {
            'inputs': [
                {'id': c.component_id, 'property': c.component_property}
                for c in inputs
            ],
            'state': [
                {'id': c.component_id, 'property': c.component_property}
                for c in state
            ],
        }

        def wrap_func(func):
            @wraps(func)
            def add_context(*args, **kwargs):
                output_value = func(*args, **kwargs)
                if multi:
                    if not isinstance(output_value, (list, tuple)):
                        raise exceptions.InvalidCallbackReturnValue(
                            'The callback {} is a multi-output.\n'
                            'Expected the output type to be a list'
                            ' or tuple but got {}.'.format(
                                callback_id, repr(output_value)
                            )
                        )

                    if not len(output_value) == len(output):
                        raise exceptions.InvalidCallbackReturnValue(
                            'Invalid number of output values for {}.\n'
                            ' Expected {} got {}'.format(
                                callback_id,
                                len(output),
                                len(output_value)
                            )
                        )

                    component_ids = collections.defaultdict(dict)
                    has_update = False
                    for i, o in enumerate(output):
                        val = output_value[i]
                        if val is not no_update:
                            has_update = True
                            o_id, o_prop = o.component_id, o.component_property
                            component_ids[o_id][o_prop] = val

                    if not has_update:
                        raise exceptions.PreventUpdate

                    response = {
                        'response': component_ids,
                        'multi': True
                    }
                else:
                    if output_value is no_update:
                        raise exceptions.PreventUpdate

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

    def update_component(self, output, inputs, state, changed_props, **kwargs):
        # target_id = '{}.{}'.format(output['id'], output['property'])
        args = []

        # # flask.g.input_values = \
        # input_values = {
        #     '{}.{}'.format(x['id'], x['property']): x.get('value')
        #     for x in inputs
        # }
        # # flask.g.\
        # state_values = {  # noqa: F841
        #     '{}.{}'.format(x['id'], x['property']): x.get('value')
        #     for x in state
        # }
        # # changed_props = kwargs.get('changedPropIds', []) or []
        # # flask.g.\
        # triggered_inputs = [  # noqa: F841
        #     {'prop_id': x, 'value': input_values[x]}
        #     for x in changed_props
        # ] if changed_props else []

        for component_registration in self.callback_map[output]['inputs']:
            args.append([
                c.get('value', None) for c in inputs if
                c['property'] == component_registration['property'] and
                c['id'] == component_registration['id']
            ][0])

        for component_registration in self.callback_map[output]['state']:
            args.append([
                c.get('value', None) for c in state if
                c['property'] == component_registration['property'] and
                c['id'] == component_registration['id']
            ][0])

        return self.callback_map[output]['callback'](*args, **kwargs)

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
        # pylint: disable=protected-access
        for component in to_validate._traverse():
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

    def serve_default_favicon(self, *args, **kwargs):  # pylint: disable=no-self-use
        return pkgutil.get_data('dash', 'favicon.ico')
