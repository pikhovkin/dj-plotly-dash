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
from .version import __version__


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
    """
        Dash is a framework for building analytical web applications.
        No JavaScript required.

        If a parameter can be set by an environment variable, that is listed as:
            env: ``DASH_****``
        Values provided here take precedence over environment variables.

        :param assets_folder: a path, relative to the current working directory,
            for extra files to be used in the browser. Default ``'assets'``.
            All .js and .css files will be loaded immediately unless excluded by
            ``assets_ignore``, and other files such as images will be served if
            requested.
        :type assets_folder: string

        :param assets_ignore: A regex, as a string to pass to ``re.compile``, for
            assets to omit from immediate loading. Ignored files will still be
            served if specifically requested. You cannot use this to prevent access
            to sensitive files.
        :type assets_ignore: string

        :param url_base_pathname: A local URL prefix to use app-wide.
            Default ``'/'``. Both `requests_pathname_prefix` and
            `routes_pathname_prefix` default to `url_base_pathname`.
        :type url_base_pathname: string

        :param serve_locally: If ``True`` (default), assets and dependencies
            (Dash and Component js and css) will be served from local URLs.
            If ``False`` we will use CDN links where available.
        :type serve_locally: boolean

        :param meta_tags: html <meta> tags to be added to the index page.
            Each dict should have the attributes and values for one tag, eg:
            ``{'name': 'description', 'content': 'My App'}``
        :type meta_tags: list of dicts

        :param external_scripts: Additional JS files to load with the page.
            Each entry can be a string (the URL) or a dict with ``src`` (the URL)
            and optionally other ``<script>`` tag attributes such as ``integrity``
            and ``crossorigin``.
        :type external_scripts: list of strings or dicts

        :param external_stylesheets: Additional CSS files to load with the page.
            Each entry can be a string (the URL) or a dict with ``href`` (the URL)
            and optionally other ``<link>`` tag attributes such as ``rel``,
            ``integrity`` and ``crossorigin``.
        :type external_stylesheets: list of strings or dicts

        :param suppress_callback_exceptions: Default ``False``: check callbacks to
            ensure referenced IDs exist and props are valid. Set to ``True``
            if your layout is dynamic, to bypass these checks.
        :type suppress_callback_exceptions: boolean

        :param show_undo_redo: Default ``False``, set to ``True`` to enable undo
            and redo buttons for stepping through the history of the app state.
        :type show_undo_redo: boolean

        :param plugins: Extend Dash functionality by passing a list of objects
            with a ``plug`` method, taking a single argument: this app, which will
            be called after the view is attached.
        :type plugins: list of objects
        """

    # pylint: disable=unused-argument
    def __init__(self,
                 url_base_pathname='/',
                 meta_tags=None,
                 external_scripts=None,
                 external_stylesheets=None,
                 assets_folder=None,
                 assets_ignore='',
                 suppress_callback_exceptions=True,
                 serve_locally=True,
                 components=None,
                 show_undo_redo=False,
                 plugins=None,
                 **kwargs):
        self.components = components

        self.config = _AttributeDict(
            url_base_pathname=url_base_pathname,
            routes_pathname_prefix=url_base_pathname,
            requests_pathname_prefix=url_base_pathname,
            serve_locally=serve_locally,
            assets_folder=assets_folder,
            assets_ignore=assets_ignore,
            assets_external_path=None,
            meta_tags=meta_tags or [],
            external_scripts=external_scripts or [],
            external_stylesheets=external_stylesheets or [],
            suppress_callback_exceptions=suppress_callback_exceptions or False,
            show_undo_redo=show_undo_redo
        )
        # self.config.set_read_only([
        #     'assets_folder',
        #     'url_base_pathname',
        #     'routes_pathname_prefix',
        #     'requests_pathname_prefix',
        #     'serve_locally',
        # ], 'Read-only: can only be set in the Dash constructor')
        self.config.finalize(
            'Invalid config key. Some settings are only available '
            'via the Dash constructor'
        )

        # list of dependencies
        self.callback_map = {}

        self._favicon = ''

        # default renderer string
        self.renderer = 'var renderer = new DashRenderer();'

        # static files from the packages
        self.css = Css(serve_locally)
        self.scripts = Scripts(serve_locally)

        self.registered_paths = collections.defaultdict(set)

        # urls
        self.routes = []

        self._layout = None
        self._cached_layout = None

        self._setup_dev_tools()
        self._hot_reload = _AttributeDict(
            hash=None,
            hard=True,
            # lock=threading.RLock(),
            # watch_thread=None,
            changed_assets=[]
        )

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
                'Layout must be a dash component '
                'or a function that returns '
                'a dash component.')

        self._layout = value

        self._validate_layout()

    def _config(self):
        # pieces of config needed by the front end
        config = {
            'url_base_pathname': self.config.url_base_pathname,
            'requests_pathname_prefix': self.config.requests_pathname_prefix,
            'ui': self._dev_tools.ui,
            'props_check': self._dev_tools.props_check,
            'show_undo_redo': self.config.show_undo_redo
        }
        if self._dev_tools.hot_reload:
            config['hot_reload'] = {
                # convert from seconds to msec as used by js `setInterval`
                'interval': int(self._dev_tools.hot_reload_interval * 1000),
                'max_retry': self._dev_tools.hot_reload_max_retry
            }
        return config

    def serve_reload_hash(self, *args, **kwargs):  # pylint: disable=unused-argument
        _reload = self._hot_reload

        hard = _reload.hard
        changed = _reload.changed_assets
        _hash = _reload.hash
        return {
            'reloadHash': _hash,
            'hard': hard,
            'packages': list(self.registered_paths.keys()),
            'files': list(changed)
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
                        srcs += resource['external_url']
            elif 'absolute_path' in resource:
                raise Exception(
                    'Serving files from absolute_path isn\'t supported yet'
                )
            elif 'asset_path' in resource:
                static_url = resource['asset_path']
                # Add a cache-busting query param
                static_url += '?m={}'.format(resource['ts'])
                srcs.append(static_url)
        return srcs

    def _generate_css_dist_html(self):
        external_links = self.config.external_stylesheets
        links = self._collect_and_register_resources(self.css.get_all_css(affix=getattr(self, '_res_affix', ''),
                                                                          module_names=self.components))

        return '\n'.join([
            _format_tag('link', link, opened=True)
            if isinstance(link, dict)
            else '<link rel="stylesheet" href="{}">'.format(link)
            for link in (external_links + links)
        ])

    def _generate_scripts_html(self):
        # Dash renderer has dependencies like React which need to be rendered
        # before every other script. However, the dash renderer bundle
        # itself needs to be rendered after all of the component's
        # scripts have rendered.
        # The rest of the scripts can just be loaded after React but before
        # dash renderer.
        # pylint: disable=protected-access

        mode = 'dev' if self._dev_tools['props_check'] is True else 'prod'

        deps = []
        for js_dist_dependency in dash_renderer._js_dist_dependencies:
            dep = {}
            for key, value in js_dist_dependency.items():
                dep[key] = value[mode] if isinstance(value, dict) else value

            deps.append(dep)

        dev = self._dev_tools.serve_dev_bundles
        srcs = (
            self._collect_and_register_resources(
                self.scripts._resources._filter_resources(
                    deps, dev_bundles=dev
                )
            ) +
            self.config.external_scripts +
            self._collect_and_register_resources(
                self.scripts.get_all_scripts(
                    affix=getattr(self, '_res_affix', ''),
                    module_names=self.components,
                    dev_bundles=dev) +
                self.scripts._resources._filter_resources(
                    dash_renderer._js_dist, dev_bundles=dev
                )
            )
        )

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
        meta_tags = self.config.meta_tags
        has_ie_compat = any(
            x.get('http-equiv', '') == 'X-UA-Compatible' for x in meta_tags
        )
        has_charset = any('charset' in x for x in meta_tags)

        tags = []
        if not has_ie_compat:
            tags.append(
                '<meta http-equiv="X-UA-Compatible" content="IE=edge">'
            )
        if not has_charset:
            tags.append('<meta charset="UTF-8">')

        tags += [_format_tag('meta', x, opened=True) for x in meta_tags]

        return '\n      '.join(tags)

    # pylint: disable=unused-argument
    def serve_component_suites(self, package_name, path_in_package_dist, *args, **kwargs):
        """ Serve the JS bundles for each package
        """
        if package_name not in self.registered_paths:
            raise exceptions.DependencyException(
                'Error loading dependency.\n'
                '"{}" is not a registered library.\n'
                'Registered libraries are: {}'
                .format(package_name, list(self.registered_paths.keys())))

        if path_in_package_dist not in self.registered_paths[package_name]:
            raise exceptions.DependencyException(
                '"{}" is registered but the path requested is not valid.\n'
                'The path requested: "{}"\n'
                'List of registered paths: {}'
                .format(
                    package_name, path_in_package_dist, self.registered_paths
                )
            )

        return pkgutil.get_data(package_name, path_in_package_dist)

    def index(self, *args, **kwargs):  # pylint: disable=unused-argument
        if self.config.assets_folder:
            self._walk_assets_directory()

        scripts = self._generate_scripts_html()
        css = self._generate_css_dist_html()
        config = self._generate_config_html()
        metas = self._generate_meta_html()
        renderer = self._generate_renderer()
        title = getattr(self, 'title', 'Dash')

        if self._favicon:
            favicon_mod_time = os.path.getmtime(
                os.path.join(self.config.assets_folder, self._favicon))
            favicon_url = self._favicon + '?m={}'.format(
                favicon_mod_time
            )
        else:
            favicon_url = '{}_favicon.ico?v={}'.format(
                self.config.requests_pathname_prefix,
                __version__)

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

        if (layout is None and not self.config.suppress_callback_exceptions):
            # Without a layout, we can't do validation on the IDs and
            # properties of the elements in the callback.
            raise exceptions.LayoutIsNotDefined('''
                Attempting to assign a callback to the application but
                the `layout` property has not been assigned.
                Assign the `layout` property before assigning callbacks.
                Alternatively, suppress this warning by setting
                `suppress_callback_exceptions=True`
            '''.replace('    ', ''))

        outputs = output if is_multi else [output]
        for args, obj, name in [(outputs, Output, 'Output'),
                                (inputs, Input, 'Input'),
                                (state, State, 'State')]:

            if not isinstance(args, (list, tuple)):
                raise exceptions.IncorrectTypeException(
                    'The {} argument `{}` must be '
                    'a list or tuple of `dash.dependencies.{}`s.'.format(
                        name.lower(), str(args), name
                    ))

            for arg in args:
                if not isinstance(arg, obj):
                    raise exceptions.IncorrectTypeException(
                        'The {} argument `{}` must be '
                        'of type `dash.{}`.'.format(
                            name.lower(), str(arg), name
                        ))

                invalid_characters = ['.']
                if any(x in arg.component_id for x in invalid_characters):
                    raise exceptions.InvalidComponentIdError(
                        'The element `{}` contains {} in its ID. '
                        'Periods are not allowed in IDs.'.format(
                            arg.component_id, invalid_characters
                        ))

                if not self.config.suppress_callback_exceptions:
                    layout_id = getattr(layout, 'id', None)
                    arg_id = arg.component_id
                    arg_prop = getattr(arg, 'component_property', None)
                    if (arg_id not in layout and arg_id != layout_id):
                        raise exceptions.NonExistentIdException('''
                            Attempting to assign a callback to the
                            component with the id "{0}" but no
                            components with id "{0}" exist in the
                            app\'s layout.\n\n
                            Here is a list of IDs in layout:\n{1}\n\n
                            If you are assigning callbacks to components
                            that are generated by other callbacks
                            (and therefore not in the initial layout), then
                            you can suppress this exception by setting
                            `suppress_callback_exceptions=True`.
                        '''.format(
                            arg_id,
                            list(layout.keys()) + (
                                [layout_id] if layout_id else []
                            )
                        ).replace('    ', ''))

                    component = (
                        layout if layout_id == arg_id else layout[arg_id]
                    )

                    if (arg_prop and
                            arg_prop not in component.available_properties and
                            not any(arg_prop.startswith(w) for w in
                                    component.available_wildcard_properties)):
                        raise exceptions.NonExistentPropException('''
                            Attempting to assign a callback with
                            the property "{0}" but the component
                            "{1}" doesn't have "{0}" as a property.\n
                            Here are the available properties in "{1}":
                            {2}
                        '''.format(
                            arg_prop, arg_id, component.available_properties
                        ).replace('    ', ''))

                    if hasattr(arg, 'component_event'):
                        raise exceptions.NonExistentEventException('''
                            Events have been removed.
                            Use the associated property instead.
                        '''.replace('    ', ''))

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
                    'Same output was used more than once in a '
                    'multi output callback!\n Duplicates:\n {}'.format(
                        ',\n'.join(
                            k for k, v in
                            ((str(x), output.count(x)) for x in output)
                            if v > 1
                        )
                    )
                )

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
                ).replace('    ', '')
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

        def _raise_invalid(bad_val, outer_val, path, index=None,
                           toplevel=False):
            bad_type = type(bad_val).__name__
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
                bad_val=bad_val
            ).replace('    ', ''))

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
                            path=type(child).__name__,
                            index=index
                        )

            # val is not a Component, but is at the top level of tree
            else:
                if not _value_is_valid(val):
                    _raise_invalid(
                        bad_val=val,
                        outer_val=type(val).__name__,
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
                    '''.format(
                        property=output.component_property,
                        id=output.component_id
                    ).replace('    ', ''))

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

    def _setup_dev_tools(self, **kwargs):
        debug = kwargs.get('debug', False)
        dev_tools = self._dev_tools = _AttributeDict()

        for attr in (
                'ui',
                'props_check',
                'serve_dev_bundles',
                'hot_reload',
                'silence_routes_logging'
        ):
            dev_tools[attr] = kwargs.get(attr, None) or debug

        for attr, _type, default in (
                ('hot_reload_interval', float, 3),
                ('hot_reload_watch_interval', float, 0.5),
                ('hot_reload_max_retry', int, 8)
        ):
            dev_tools[attr] = _type(kwargs.get(attr, None) or default)

        return dev_tools

    def _walk_assets_directory(self):
        ignore_filter = [self.config.assets_ignore] if self.config.assets_ignore else None

        def add_resource(p, filepath):
            res = {'asset_path': p, 'filepath': filepath}
            if self.config.assets_external_path:
                res['external_url'] = '{}{}'.format(self.config.assets_external_path, path)
            return res

        files = list(get_files(staticfiles_storage, ignore_patterns=ignore_filter, location=self.config.assets_folder))
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
