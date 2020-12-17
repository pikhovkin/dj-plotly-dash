from __future__ import print_function

import os
import sys
import collections
import importlib
import json
import pkgutil
import logging
import mimetypes
import hashlib
import base64
from functools import wraps

from django.contrib.staticfiles.utils import get_files
from django.contrib.staticfiles.storage import staticfiles_storage
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.safestring import mark_safe

import plotly
import dash_renderer

from .fingerprint import build_fingerprint, check_fingerprint
from .resources import Scripts, Css
from .dependencies import handle_callback_args
from .exceptions import PreventUpdate
from .version import __version__
from ._utils import (
    AttributeDict,
    create_callback_id,
    format_tag,
    generate_hash,
    inputs_to_vals,
    interpolate_str,
    patch_collections_abc,
    stringify_id,
)
from . import _validate


__all__ = (
    'Dash',
)

# Add explicit mapping for map files
mimetypes.add_type("application/json", ".map", True)

_app_entry = """
<div id="react-entry-point">
    <div class="_dash-loading">
        Loading...
    </div>
</div>
"""


class _NoUpdate(object):
    # pylint: disable=too-few-public-methods
    pass


# Singleton signal to not update an output, alternative to PreventUpdate
no_update = _NoUpdate()


_inline_clientside_template = """
var clientside = window.dash_clientside = window.dash_clientside || {{}};
var ns = clientside["{namespace}"] = clientside["{namespace}"] || {{}};
ns["{function_name}"] = {clientside_function};
"""


# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-arguments, too-many-locals
class Dash(object):
    """Dash is a framework for building analytical web applications.
    No JavaScript required.

    If a parameter can be set by an environment variable, that is listed as:
        env: ``DASH_****``
    Values provided here take precedence over environment variables.

    :param name: The name Flask should use for your app. Even if you provide
        your own ``server``, ``name`` will be used to help find assets.
        Typically ``__name__`` (the magic global var, not a string) is the
        best value to use. Default ``'__main__'``, env: ``DASH_APP_NAME``
    :type name: string

    :param server: Sets the Flask server for your app. There are three options:
        ``True`` (default): Dash will create a new server
        ``False``: The server will be added later via ``app.init_app(server)``
            where ``server`` is a ``flask.Flask`` instance.
        ``flask.Flask``: use this pre-existing Flask server.
    :type server: boolean or flask.Flask

    :param assets_folder: a path, relative to the current working directory,
        for extra files to be used in the browser. Default ``'assets'``.
        All .js and .css files will be loaded immediately unless excluded by
        ``assets_ignore``, and other files such as images will be served if
        requested.
    :type assets_folder: string

    :param assets_url_path: The local urls for assets will be:
        ``requests_pathname_prefix + assets_url_path + '/' + asset_path``
        where ``asset_path`` is the path to a file inside ``assets_folder``.
        Default ``'assets'``.
    :type asset_url_path: string

    :param assets_ignore: A regex, as a string to pass to ``re.compile``, for
        assets to omit from immediate loading. Ignored files will still be
        served if specifically requested. You cannot use this to prevent access
        to sensitive files.
    :type assets_ignore: string

    :param assets_external_path: an absolute URL from which to load assets.
        Use with ``serve_locally=False``. Dash can still find js and css to
        automatically load if you also keep local copies in your assets
        folder that Dash can index, but external serving can improve
        performance and reduce load on the Dash server.
        env: ``DASH_ASSETS_EXTERNAL_PATH``
    :type assets_external_path: string

    :param include_assets_files: Default ``True``, set to ``False`` to prevent
        immediate loading of any assets. Assets will still be served if
        specifically requested. You cannot use this to prevent access
        to sensitive files. env: ``DASH_INCLUDE_ASSETS_FILES``
    :type include_assets_files: boolean

    :param url_base_pathname: A local URL prefix to use app-wide.
        Default ``'/'``. Both `requests_pathname_prefix` and
        `routes_pathname_prefix` default to `url_base_pathname`.
        env: ``DASH_URL_BASE_PATHNAME``
    :type url_base_pathname: string

    :param requests_pathname_prefix: A local URL prefix for file requests.
        Defaults to `url_base_pathname`, and must end with
        `routes_pathname_prefix`. env: ``DASH_REQUESTS_PATHNAME_PREFIX``
    :type requests_pathname_prefix: string

    :param routes_pathname_prefix: A local URL prefix for JSON requests.
        Defaults to ``url_base_pathname``, and must start and end
        with ``'/'``. env: ``DASH_ROUTES_PATHNAME_PREFIX``
    :type routes_pathname_prefix: string

    :param serve_locally: If ``True`` (default), assets and dependencies
        (Dash and Component js and css) will be served from local URLs.
        If ``False`` we will use CDN links where available.
    :type serve_locally: boolean

    :param compress: Use gzip to compress files and data served by Flask.
        Default ``True``
    :type compress: boolean

    :param meta_tags: html <meta> tags to be added to the index page.
        Each dict should have the attributes and values for one tag, eg:
        ``{'name': 'description', 'content': 'My App'}``
    :type meta_tags: list of dicts

    :param index_string: Override the standard Dash index page.
        Must contain the correct insertion markers to interpolate various
        content into it depending on the app config and components used.
        See https://dash.plotly.com/external-resources for details.
    :type index_string: string

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
        env: ``DASH_SUPPRESS_CALLBACK_EXCEPTIONS``
    :type suppress_callback_exceptions: boolean

    :param prevent_initial_callbacks: Default ``False``: Sets the default value
        of ``prevent_initial_call`` for all callbacks added to the app.
        Normally all callbacks are fired when the associated outputs are first
        added to the page. You can disable this for individual callbacks by
        setting ``prevent_initial_call`` in their definitions, or set it
        ``True`` here in which case you must explicitly set it ``False`` for
        those callbacks you wish to have an initial call. This setting has no
        effect on triggering callbacks when their inputs change later on.

    :param show_undo_redo: Default ``False``, set to ``True`` to enable undo
        and redo buttons for stepping through the history of the app state.
    :type show_undo_redo: boolean

    :param plugins: Extend Dash functionality by passing a list of objects
        with a ``plug`` method, taking a single argument: this app, which will
        be called after the Flask server is attached.
    :type plugins: list of objects

    :param title: Default ``Dash``. Configures the document.title
    (the text that appears in a browser tab).

    :param update_title: Default ``Updating...``. Configures the document.title
    (the text that appears in a browser tab) text when a callback is being run.
    Set to None or '' if you don't want the document.title to change or if you
    want to control the document.title through a separate component or
    clientside callback.
    """

    # pylint: disable=unused-argument
    def __init__(self,
                 name=None,  # for tests only
                 assets_folder=None,
                 assets_ignore='',
                 eager_loading=False,
                 url_base_pathname='/',
                 serve_locally=True,
                 meta_tags=None,
                 external_scripts=None,
                 external_stylesheets=None,
                 suppress_callback_exceptions=True,
                 prevent_initial_callbacks=False,
                 show_undo_redo=False,
                 plugins=None,
                 title="Dash",
                 update_title="Updating...",
                 components=None,  # feature of dj-plotly-dash
                 **kwargs):
        _validate.check_obsolete(kwargs)

        self.components = components

        self.config = AttributeDict(
            assets_folder=assets_folder,
            assets_ignore=assets_ignore,
            assets_external_path=None,
            eager_loading=eager_loading,
            url_base_pathname=url_base_pathname,
            routes_pathname_prefix=url_base_pathname,
            requests_pathname_prefix=url_base_pathname,
            serve_locally=serve_locally,
            meta_tags=meta_tags or [],
            external_scripts=external_scripts or [],
            external_stylesheets=external_stylesheets or [],
            suppress_callback_exceptions=suppress_callback_exceptions or False,
            prevent_initial_callbacks=prevent_initial_callbacks,
            show_undo_redo=show_undo_redo,
            title=title,
            update_title=update_title,
        )
        # self.config.set_read_only(
        #     [
        #         "name",
        #         "assets_folder",
        #         "assets_url_path",
        #         "eager_loading",
        #         "url_base_pathname",
        #         "routes_pathname_prefix",
        #         "requests_pathname_prefix",
        #         "serve_locally",
        #         "compress",
        #     ],
        #     "Read-only: can only be set in the Dash constructor",
        # )
        self.config.finalize(
            "Invalid config key. Some settings are only available "
            "via the Dash constructor"
        )

        # keep title as a class property for backwards compatibility
        self.title = title

        # list of dependencies - this one is used by the back end for dispatching
        self.callback_map = {}
        # same deps as a list to catch duplicate outputs, and to send to the front end
        self._callback_list = []

        # list of inline scripts
        self._inline_scripts = []

        # # index_string has special setter so can't go in config
        # self._index_string = ""
        # self.index_string = index_string
        self._favicon = ''

        # default renderer string
        self.renderer = "var renderer = new DashRenderer();"

        # static files from the packages
        self.css = Css(serve_locally)
        self.scripts = Scripts(serve_locally, eager_loading)

        self.registered_paths = collections.defaultdict(set)

        # urls
        self.routes = []

        self._layout = None
        self._layout_is_function = False
        self.validation_layout = None

        self._setup_dev_tools()
        self._hot_reload = AttributeDict(
            hash=None,
            hard=True,
            # lock=threading.RLock(),
            # watch_thread=None,
            changed_assets=[],
        )

        # self._assets_files = []

        self.logger = logging.getLogger('dj_plotly_dash')
        # self.logger.addHandler(logging.StreamHandler(stream=sys.stdout))

        if isinstance(plugins, patch_collections_abc("Iterable")):
            for plugin in plugins:
                plugin.plug(self)

        # if self.server is not None:
        #     self.init_app()

        # self.logger.setLevel(logging.INFO)

    # def init_app(self, app=None):
    #     """Initialize the parts of Dash that require a flask app."""
    #     config = self.config
    #
    #     if app is not None:
    #         self.server = app
    #
    #     assets_blueprint_name = "{}{}".format(
    #         config.routes_pathname_prefix.replace("/", "_"), "dash_assets"
    #     )
    #
    #     self.server.register_blueprint(
    #         flask.Blueprint(
    #             assets_blueprint_name,
    #             config.name,
    #             static_folder=self.config.assets_folder,
    #             static_url_path="{}{}".format(
    #                 config.routes_pathname_prefix,
    #                 self.config.assets_url_path.lstrip("/"),
    #             ),
    #         )
    #     )
    #
    #     if config.compress:
    #         # gzip
    #         Compress(self.server)
    #
    #     @self.server.errorhandler(PreventUpdate)
    #     def _handle_error(_):
    #         """Handle a halted callback and return an empty 204 response."""
    #         return "", 204
    #
    #     self.server.before_first_request(self._setup_server)
    #
    #     # add a handler for components suites errors to return 404
    #     self.server.errorhandler(InvalidResourceError)(self._invalid_resources_handler)
    #
    #     self._add_url(
    #         "_dash-component-suites/<string:package_name>/<path:fingerprinted_path>",
    #         self.serve_component_suites,
    #     )
    #     self._add_url("_dash-layout", self.serve_layout)
    #     self._add_url("_dash-dependencies", self.dependencies)
    #     self._add_url("_dash-update-component", self.dispatch, ["POST"])
    #     self._add_url("_reload-hash", self.serve_reload_hash)
    #     self._add_url("_favicon.ico", self._serve_default_favicon)
    #     self._add_url("", self.index)
    #
    #     # catch-all for front-end routes, used by dcc.Location
    #     self._add_url("<path:path>", self.index)
    #
    # def _add_url(self, name, view_func, methods=("GET",)):
    #     full_name = self.config.routes_pathname_prefix + name
    #
    #     self.server.add_url_rule(
    #         full_name, view_func=view_func, endpoint=full_name, methods=list(methods)
    #     )
    #
    #     # record the url in Dash.routes so that it can be accessed later
    #     # e.g. for adding authentication with flask_login
    #     self.routes.append(full_name)

    @property
    def layout(self):
        return self._layout

    def _layout_value(self):
        return self._layout() if self._layout_is_function else self._layout

    @layout.setter
    def layout(self, value):
        _validate.validate_layout_type(value)
        self._layout_is_function = isinstance(value, patch_collections_abc("Callable"))
        self._layout = value

        # for using flask.has_request_context() to deliver a full layout for
        # validation inside a layout function - track if a user might be doing this.
        if (
            self._layout_is_function
            and not self.validation_layout
            and not self.config.suppress_callback_exceptions
        ):

            def simple_clone(c, children=None):
                cls = type(c)
                # in Py3 we can use the __init__ signature to reduce to just
                # required args and id; in Py2 this doesn't work so we just
                # empty out children.
                sig = getattr(cls.__init__, "__signature__", None)
                props = {
                    p: getattr(c, p)
                    for p in c._prop_names  # pylint: disable=protected-access
                    if hasattr(c, p)
                    and (
                        p == "id" or not sig or sig.parameters[p].default == c.REQUIRED
                    )
                }
                if props.get("children", children):
                    props["children"] = children or []
                return cls(**props)

            layout_value = self._layout_value()
            _validate.validate_layout(value, layout_value)
            self.validation_layout = simple_clone(
                # pylint: disable=protected-access
                layout_value,
                [simple_clone(c) for c in layout_value._traverse_ids()],
            )

    # @property
    # def index_string(self):
    #     return self._index_string
    #
    # @index_string.setter
    # def index_string(self, value):
    #     checks = (_re_index_entry, _re_index_config, _re_index_scripts)
    #     _validate.validate_index("index string", checks, value)
    #     self._index_string = value
    #
    # def serve_layout(self):
    #     layout = self._layout_value()
    #
    #     # TODO - Set browser cache limit - pass hash into frontend
    #     return flask.Response(
    #         json.dumps(layout, cls=plotly.utils.PlotlyJSONEncoder),
    #         mimetype="application/json",
    #     )

    def _config(self):
        # pieces of config needed by the front end
        config = {
            "url_base_pathname": self.config.url_base_pathname,
            "requests_pathname_prefix": self.config.requests_pathname_prefix,
            "ui": self._dev_tools.ui,
            "props_check": self._dev_tools.props_check,
            "show_undo_redo": self.config.show_undo_redo,
            "suppress_callback_exceptions": self.config.suppress_callback_exceptions,
            "update_title": self.config.update_title,
        }
        if self._dev_tools.hot_reload:
            config["hot_reload"] = {
                # convert from seconds to msec as used by js `setInterval`
                "interval": int(self._dev_tools.hot_reload_interval * 1000),
                "max_retry": self._dev_tools.hot_reload_max_retry,
            }
        if self.validation_layout and not self.config.suppress_callback_exceptions:
            config["validation_layout"] = self.validation_layout

        return config

    def serve_reload_hash(self, *args, **kwargs):  # pylint: disable=unused-argument
        _reload = self._hot_reload

        hard = _reload.hard
        changed = _reload.changed_assets
        _hash = generate_hash()
        return {
            "reloadHash": _hash,
            "hard": hard,
            "packages": list(self.registered_paths.keys()),
            "files": list(changed)
        }

    def serve_routes(self, *args, **kwargs):  # pylint: disable=unused-argument
        return self.routes

    def _collect_and_register_resources(self, resources):
        # now needs the app context.
        # template in the necessary component suite JS bundles
        # add the version number of the package as a query parameter
        # for cache busting
        def _relative_url_path(path_prefix, relative_package_path="", namespace=""):

            module_path = os.path.join(
                os.path.dirname(sys.modules[namespace].__file__),
                relative_package_path,
            )

            modified = int(os.stat(module_path).st_mtime)

            return "{}_dash-component-suites/{}/{}".format(
                path_prefix,
                namespace,
                build_fingerprint(
                    relative_package_path,
                    importlib.import_module(namespace).__version__,
                    modified,
                ),
            )

        try:
            DASH_COMPONENT_SUITES_URL = getattr(settings, 'DASH_COMPONENT_SUITES_URL', '')
        except ImproperlyConfigured:
            DASH_COMPONENT_SUITES_URL = ''

        path_prefix = DASH_COMPONENT_SUITES_URL or self.config['requests_pathname_prefix']

        srcs = []
        for resource in resources:
            is_dynamic_resource = resource.get("dynamic", False)

            if "relative_package_path" in resource:
                paths = resource["relative_package_path"]
                paths = [paths] if isinstance(paths, str) else paths

                for rel_path in paths:
                    self.registered_paths[resource["namespace"]].add(rel_path)

                    if not is_dynamic_resource:
                        srcs.append(
                            _relative_url_path(
                                path_prefix,
                                relative_package_path=rel_path,
                                namespace=resource["namespace"],
                            )
                        )
            elif "external_url" in resource:
                if not is_dynamic_resource:
                    if isinstance(resource["external_url"], str):
                        srcs.append(resource["external_url"])
                    else:
                        srcs += resource["external_url"]
            elif "absolute_path" in resource:
                raise Exception("Serving files from absolute_path isn't supported yet")
            elif "asset_path" in resource:
                static_url = resource["asset_path"]
                # Add a cache-busting query param
                static_url += "?m={}".format(resource["ts"])
                srcs.append(static_url)
        return srcs

    def _generate_css_dist_html(self):
        external_links = self.config.external_stylesheets
        links = self._collect_and_register_resources(self.css.get_all_css(
            affix=getattr(self, "_res_affix", ""),
            module_names=self.components))

        return "\n".join(
            [
                format_tag("link", link, opened=True)
                if isinstance(link, dict)
                else '<link rel="stylesheet" href="{}">'.format(link)
                for link in (external_links + links)
            ]
        )

    def _generate_scripts_html(self):
        # Dash renderer has dependencies like React which need to be rendered
        # before every other script. However, the dash renderer bundle
        # itself needs to be rendered after all of the component's
        # scripts have rendered.
        # The rest of the scripts can just be loaded after React but before
        # dash renderer.
        # pylint: disable=protected-access

        mode = "dev" if self._dev_tools["props_check"] is True else "prod"

        deps = []
        for js_dist_dependency in dash_renderer._js_dist_dependencies:
            dep = {}
            for key, value in js_dist_dependency.items():
                dep[key] = value[mode] if isinstance(value, dict) else value

            deps.append(dep)

        dev = self._dev_tools.serve_dev_bundles
        srcs = (
            self._collect_and_register_resources(
                self.scripts._resources._filter_resources(deps, dev_bundles=dev)
            )
            + self.config.external_scripts
            + self._collect_and_register_resources(
                self.scripts.get_all_scripts(
                    affix=getattr(self, "_res_affix", ""),
                    module_names=self.components,
                    dev_bundles=dev)
                + self.scripts._resources._filter_resources(
                    dash_renderer._js_dist, dev_bundles=dev
                )
            )
        )

        return "\n".join(
            [
                format_tag("script", src)
                if isinstance(src, dict)
                else '<script src="{}"></script>'.format(src)
                for src in srcs
            ]
            + ["<script>{}</script>".format(src) for src in self._inline_scripts]
        )

    def _generate_config_html(self, **kwargs):
        config = self._config()
        config.update(kwargs)
        return '<script id="_dash-config" type="application/json">{}</script>'.format(
            json.dumps(config, cls=plotly.utils.PlotlyJSONEncoder)
        )

    def _generate_renderer(self):
        return (
            '<script id="_dash-renderer" type="application/javascript">'
            "{}"
            "</script>"
        ).format(self.renderer)

    def _generate_meta_html(self):
        meta_tags = self.config.meta_tags
        has_ie_compat = any(
            x.get("http-equiv", "") == "X-UA-Compatible" for x in meta_tags
        )
        has_charset = any("charset" in x for x in meta_tags)

        tags = []
        if not has_ie_compat:
            tags.append('<meta http-equiv="X-UA-Compatible" content="IE=edge">')
        if not has_charset:
            tags.append('<meta charset="UTF-8">')

        tags += [format_tag("meta", x, opened=True) for x in meta_tags]

        return "\n      ".join(tags)

    # pylint: disable=unused-argument
    def serve_component_suites(self, package_name, fingerprinted_path, *args, **kwargs):
        """ Serve the JS bundles for each package
        """
        path_in_pkg, has_fingerprint = check_fingerprint(fingerprinted_path)

        _validate.validate_js_path(self.registered_paths, package_name, path_in_pkg)

        # extension = "." + path_in_pkg.split(".")[-1]
        # mimetype = mimetypes.types_map.get(extension, "application/octet-stream")
        #
        # package = sys.modules[package_name]
        # self.logger.debug(
        #     "serving -- package: %s[%s] resource: %s => location: %s",
        #     package_name,
        #     package.__version__,
        #     path_in_pkg,
        #     package.__path__,
        # )
        #
        # response = flask.Response(
        #     pkgutil.get_data(package_name, path_in_pkg), mimetype=mimetype
        # )
        #
        # if has_fingerprint:
        #     # Fingerprinted resources are good forever (1 year)
        #     # No need for ETag as the fingerprint changes with each build
        #     response.cache_control.max_age = 31536000  # 1 year
        # else:
        #     # Non-fingerprinted resources are given an ETag that
        #     # will be used / check on future requests
        #     response.add_etag()
        #     tag = response.get_etag()[0]
        #
        #     request_etag = flask.request.headers.get("If-None-Match")
        #
        #     if '"{}"'.format(tag) == request_etag:
        #         response = flask.Response(None, status=304)
        #
        return pkgutil.get_data(package_name, path_in_pkg)

    def index(self, *args, **kwargs):  # pylint: disable=unused-argument
        if self.config.assets_folder:
            self._walk_assets_directory()

        scripts = self._generate_scripts_html()
        css = self._generate_css_dist_html()
        config = self._generate_config_html()
        metas = self._generate_meta_html()
        renderer = self._generate_renderer()

        # use self.title instead of app.config.title for backwards compatibility
        title = self.title

        if self._favicon:
            favicon_mod_time = os.path.getmtime(
                os.path.join(self.config.assets_folder, self._favicon)
            )
            favicon_url = self._favicon + "?m={}".format(
                favicon_mod_time
            )
        else:
            favicon_url = "{}_favicon.ico?v={}".format(
                self.config.requests_pathname_prefix, __version__
            )

        favicon = format_tag(
            "link",
            {"rel": "icon", "type": "image/x-icon", "href": favicon_url},
            opened=True,
        )

        index = dict(
            metas=mark_safe(metas),
            title=mark_safe(title),
            css=mark_safe(css),
            config=mark_safe(config),
            scripts=mark_safe(scripts),
            app_entry=mark_safe(getattr(self, 'app_entry', _app_entry)),
            favicon=mark_safe(favicon),
            renderer=mark_safe(renderer)
        )

        # checks = (
        #     _re_index_entry_id,
        #     _re_index_config_id,
        #     _re_index_scripts_id,
        #     _re_renderer_scripts_id,
        # )
        # _validate.validate_index("index", checks, index)
        return index

    def interpolate_index(
        self,
        metas="",
        title="",
        css="",
        config="",
        scripts="",
        app_entry="",
        favicon="",
        renderer="",
    ):
        """Called to create the initial HTML string that is loaded on page.
        Override this method to provide you own custom HTML.

        :Example:

            class MyDash(dash.Dash):
                def interpolate_index(self, **kwargs):
                    return '''<!DOCTYPE html>
                    <html>
                        <head>
                            <title>My App</title>
                        </head>
                        <body>
                            <div id="custom-header">My custom header</div>
                            {app_entry}
                            {config}
                            {scripts}
                            {renderer}
                            <div id="custom-footer">My custom footer</div>
                        </body>
                    </html>'''.format(app_entry=kwargs.get('app_entry'),
                                      config=kwargs.get('config'),
                                      scripts=kwargs.get('scripts'),
                                      renderer=kwargs.get('renderer'))

        :param metas: Collected & formatted meta tags.
        :param title: The title of the app.
        :param css: Collected & formatted css dependencies as <link> tags.
        :param config: Configs needed by dash-renderer.
        :param scripts: Collected & formatted scripts tags.
        :param renderer: A script tag that instantiates the DashRenderer.
        :param app_entry: Where the app will render.
        :param favicon: A favicon <link> tag if found in assets folder.
        :return: The interpolated HTML string for the index.
        """
        return interpolate_str(
            self.index_string,
            metas=metas,
            title=title,
            css=css,
            config=config,
            scripts=scripts,
            favicon=favicon,
            renderer=renderer,
            app_entry=app_entry,
        )

    def dependencies(self, *args, **kwargs):  # pylint: disable=unused-argument
        return self._callback_list

    def _insert_callback(self, output, inputs, state, prevent_initial_call):
        if prevent_initial_call is None:
            prevent_initial_call = self.config.prevent_initial_callbacks

        callback_id = create_callback_id(output)
        callback_spec = {
            "output": callback_id,
            "inputs": [c.to_dict() for c in inputs],
            "state": [c.to_dict() for c in state],
            "clientside_function": None,
            "prevent_initial_call": prevent_initial_call,
        }
        self.callback_map[callback_id] = {
            "inputs": callback_spec["inputs"],
            "state": callback_spec["state"],
        }
        self._callback_list.append(callback_spec)

        return callback_id

    def clientside_callback(self, clientside_function, *args, **kwargs):
        """Create a callback that updates the output by calling a clientside
        (JavaScript) function instead of a Python function.

        Unlike `@app.callback`, `clientside_callback` is not a decorator:
        it takes either a
        `dash.dependencies.ClientsideFunction(namespace, function_name)`
        argument that describes which JavaScript function to call
        (Dash will look for the JavaScript function at
        `window.dash_clientside[namespace][function_name]`), or it may take
        a string argument that contains the clientside function source.

        For example, when using a `dash.dependencies.ClientsideFunction`:
        ```
        app.clientside_callback(
            ClientsideFunction('my_clientside_library', 'my_function'),
            Output('my-div' 'children'),
            [Input('my-input', 'value'),
             Input('another-input', 'value')]
        )
        ```

        With this signature, Dash's front-end will call
        `window.dash_clientside.my_clientside_library.my_function` with the
        current values of the `value` properties of the components `my-input`
        and `another-input` whenever those values change.

        Include a JavaScript file by including it your `assets/` folder. The
        file can be named anything but you'll need to assign the function's
        namespace to the `window.dash_clientside` namespace. For example,
        this file might look:
        ```
        window.dash_clientside = window.dash_clientside || {};
        window.dash_clientside.my_clientside_library = {
            my_function: function(input_value_1, input_value_2) {
                return (
                    parseFloat(input_value_1, 10) +
                    parseFloat(input_value_2, 10)
                );
            }
        }
        ```

        Alternatively, you can pass the JavaScript source directly to
        `clientside_callback`. In this case, the same example would look like:
        ```
        app.clientside_callback(
            '''
            function(input_value_1, input_value_2) {
                return (
                    parseFloat(input_value_1, 10) +
                    parseFloat(input_value_2, 10)
                );
            }
            ''',
            Output('my-div' 'children'),
            [Input('my-input', 'value'),
             Input('another-input', 'value')]
        )
        ```

        The last, optional argument `prevent_initial_call` causes the callback
        not to fire when its outputs are first added to the page. Defaults to
        `False` unless `prevent_initial_callbacks=True` at the app level.
        """
        output, inputs, state, prevent_initial_call = handle_callback_args(args, kwargs)
        self._insert_callback(output, inputs, state, prevent_initial_call)

        # If JS source is explicitly given, create a namespace and function
        # name, then inject the code.
        if isinstance(clientside_function, str):

            out0 = output
            if isinstance(output, (list, tuple)):
                out0 = output[0]

            namespace = "_dashprivate_{}".format(out0.component_id)
            function_name = "{}".format(out0.component_property)

            self._inline_scripts.append(
                _inline_clientside_template.format(
                    namespace=namespace.replace('"', '\\"'),
                    function_name=function_name.replace('"', '\\"'),
                    clientside_function=clientside_function,
                )
            )

        # Callback is stored in an external asset.
        else:
            namespace = clientside_function.namespace
            function_name = clientside_function.function_name

        self._callback_list[-1]["clientside_function"] = {
            "namespace": namespace,
            "function_name": function_name,
        }

    def callback(self, *_args, **_kwargs):
        """
        Normally used as a decorator, `@app.callback` provides a server-side
        callback relating the values of one or more `Output` items to one or
        more `Input` items which will trigger the callback when they change,
        and optionally `State` items which provide additional information but
        do not trigger the callback directly.

        The last, optional argument `prevent_initial_call` causes the callback
        not to fire when its outputs are first added to the page. Defaults to
        `False` unless `prevent_initial_callbacks=True` at the app level.


        """
        output, inputs, state, prevent_initial_call = handle_callback_args(
            _args, _kwargs
        )
        callback_id = self._insert_callback(output, inputs, state, prevent_initial_call)
        multi = isinstance(output, (list, tuple))

        def wrap_func(func):
            @wraps(func)
            def add_context(*args, **kwargs):
                output_spec = kwargs.pop("outputs_list")

                # don't touch the comment on the next line - used by debugger
                output_value = func(*args, **kwargs)  # %% callback invoked %%

                if isinstance(output_value, _NoUpdate):
                    raise PreventUpdate

                # wrap single outputs so we can treat them all the same
                # for validation and response creation
                if not multi:
                    output_value, output_spec = [output_value], [output_spec]

                _validate.validate_multi_return(output_spec, output_value, callback_id)

                component_ids = collections.defaultdict(dict)
                has_update = False
                for val, spec in zip(output_value, output_spec):
                    if isinstance(val, _NoUpdate):
                        continue
                    for vali, speci in (
                        zip(val, spec) if isinstance(spec, list) else [[val, spec]]
                    ):
                        if not isinstance(vali, _NoUpdate):
                            has_update = True
                            id_str = stringify_id(speci["id"])
                            component_ids[id_str][speci["property"]] = vali

                if not has_update:
                    raise PreventUpdate

                response = {"response": component_ids, "multi": True}

                # try:
                #     jsonResponse = json.dumps(
                #         response, cls=plotly.utils.PlotlyJSONEncoder
                #     )
                # except TypeError:
                #     _validate.fail_callback_output(output_value, output)

                return output_value, response

            self.callback_map[callback_id]["callback"] = add_context

            return add_context

        return wrap_func

    def update_component(self, output, outputs_list, inputs, state, **kwargs):
        args = inputs_to_vals(inputs + state)
        try:
            func = self.callback_map[output]["callback"]
        except KeyError:
            msg = "Callback function not found for output '{}', perhaps you forgot to prepend the '@'?"
            raise KeyError(msg.format(output))

        return func(*args, outputs_list=outputs_list)

    def _add_assets_resource(self, url_path, file_path):
        res = {"asset_path": url_path, "filepath": file_path}
        if self.config.assets_external_path:
            res["external_url"] = "{}{}".format(
                self.config.assets_external_path, url_path
            )
        return res

    def _walk_assets_directory(self):
        ignore_patterns = [self.config.assets_ignore] if self.config.assets_ignore else None
        files = list(get_files(staticfiles_storage, ignore_patterns=ignore_patterns,
                               location=self.config.assets_folder))
        for f in sorted(files):
            path = staticfiles_storage.url(f)
            full = staticfiles_storage.path(f)

            if f.endswith('js'):
                self.scripts.append_script(self._add_assets_resource(path, full))
            elif f.endswith('css'):
                self.css.append_css(self._add_assets_resource(path, full))
            elif f.endswith('favicon.ico'):
                self._favicon = path

    # @staticmethod
    # def _invalid_resources_handler(err):
    #     return err.args[0], 404

    def serve_default_favicon(self, *args, **kwargs):  # pylint: disable=no-self-use
        return pkgutil.get_data('dash', 'favicon.ico')

    def csp_hashes(self, hash_algorithm="sha256"):
        """Calculates CSP hashes (sha + base64) of all inline scripts, such that
        one of the biggest benefits of CSP (disallowing general inline scripts)
        can be utilized together with Dash clientside callbacks (inline scripts).

        Calculate these hashes after all inline callbacks are defined,
        and add them to your CSP headers before starting the server, for example
        with the flask-talisman package from PyPI:

        flask_talisman.Talisman(app.server, content_security_policy={
            "default-src": "'self'",
            "script-src": ["'self'"] + app.csp_hashes()
        })

        :param hash_algorithm: One of the recognized CSP hash algorithms ('sha256', 'sha384', 'sha512').
        :return: List of CSP hash strings of all inline scripts.
        """

        HASH_ALGORITHMS = ["sha256", "sha384", "sha512"]
        if hash_algorithm not in HASH_ALGORITHMS:
            raise ValueError(
                "Possible CSP hash algorithms: " + ", ".join(HASH_ALGORITHMS)
            )

        method = getattr(hashlib, hash_algorithm)

        return [
            "'{hash_algorithm}-{base64_hash}'".format(
                hash_algorithm=hash_algorithm,
                base64_hash=base64.b64encode(
                    method(script.encode("utf-8")).digest()
                ).decode("utf-8"),
            )
            for script in self._inline_scripts + [self.renderer]
        ]

    # def get_asset_url(self, path):
    #     asset = get_asset_path(
    #         self.config.requests_pathname_prefix,
    #         path,
    #         self.config.assets_url_path.lstrip("/"),
    #     )
    #
    #     return asset
    #
    # def get_relative_path(self, path):
    #     """
    #     Return a path with `requests_pathname_prefix` prefixed before it.
    #     Use this function when specifying local URL paths that will work
    #     in environments regardless of what `requests_pathname_prefix` is.
    #     In some deployment environments, like Dash Enterprise,
    #     `requests_pathname_prefix` is set to the application name,
    #     e.g. `my-dash-app`.
    #     When working locally, `requests_pathname_prefix` might be unset and
    #     so a relative URL like `/page-2` can just be `/page-2`.
    #     However, when the app is deployed to a URL like `/my-dash-app`, then
    #     `app.get_relative_path('/page-2')` will return `/my-dash-app/page-2`.
    #     This can be used as an alternative to `get_asset_url` as well with
    #     `app.get_relative_path('/assets/logo.png')`
    #
    #     Use this function with `app.strip_relative_path` in callbacks that
    #     deal with `dcc.Location` `pathname` routing.
    #     That is, your usage may look like:
    #     ```
    #     app.layout = html.Div([
    #         dcc.Location(id='url'),
    #         html.Div(id='content')
    #     ])
    #     @app.callback(Output('content', 'children'), [Input('url', 'pathname')])
    #     def display_content(path):
    #         page_name = app.strip_relative_path(path)
    #         if not page_name:  # None or ''
    #             return html.Div([
    #                 dcc.Link(href=app.get_relative_path('/page-1')),
    #                 dcc.Link(href=app.get_relative_path('/page-2')),
    #             ])
    #         elif page_name == 'page-1':
    #             return chapters.page_1
    #         if page_name == "page-2":
    #             return chapters.page_2
    #     ```
    #     """
    #     asset = get_relative_path(self.config.requests_pathname_prefix, path)
    #
    #     return asset
    #
    # def strip_relative_path(self, path):
    #     """
    #     Return a path with `requests_pathname_prefix` and leading and trailing
    #     slashes stripped from it. Also, if None is passed in, None is returned.
    #     Use this function with `get_relative_path` in callbacks that deal
    #     with `dcc.Location` `pathname` routing.
    #     That is, your usage may look like:
    #     ```
    #     app.layout = html.Div([
    #         dcc.Location(id='url'),
    #         html.Div(id='content')
    #     ])
    #     @app.callback(Output('content', 'children'), [Input('url', 'pathname')])
    #     def display_content(path):
    #         page_name = app.strip_relative_path(path)
    #         if not page_name:  # None or ''
    #             return html.Div([
    #                 dcc.Link(href=app.get_relative_path('/page-1')),
    #                 dcc.Link(href=app.get_relative_path('/page-2')),
    #             ])
    #         elif page_name == 'page-1':
    #             return chapters.page_1
    #         if page_name == "page-2":
    #             return chapters.page_2
    #     ```
    #     Note that `chapters.page_1` will be served if the user visits `/page-1`
    #     _or_ `/page-1/` since `strip_relative_path` removes the trailing slash.
    #
    #     Also note that `strip_relative_path` is compatible with
    #     `get_relative_path` in environments where `requests_pathname_prefix` set.
    #     In some deployment environments, like Dash Enterprise,
    #     `requests_pathname_prefix` is set to the application name, e.g. `my-dash-app`.
    #     When working locally, `requests_pathname_prefix` might be unset and
    #     so a relative URL like `/page-2` can just be `/page-2`.
    #     However, when the app is deployed to a URL like `/my-dash-app`, then
    #     `app.get_relative_path('/page-2')` will return `/my-dash-app/page-2`
    #
    #     The `pathname` property of `dcc.Location` will return '`/my-dash-app/page-2`'
    #     to the callback.
    #     In this case, `app.strip_relative_path('/my-dash-app/page-2')`
    #     will return `'page-2'`
    #
    #     For nested URLs, slashes are still included:
    #     `app.strip_relative_path('/page-1/sub-page-1/')` will return
    #     `page-1/sub-page-1`
    #     ```
    #     """
    #     return strip_relative_path(self.config.requests_pathname_prefix, path)

    def _setup_dev_tools(self, **kwargs):
        debug = kwargs.get("debug", False)
        dev_tools = self._dev_tools = AttributeDict()

        for attr in (
            "ui",
            "props_check",
            "serve_dev_bundles",
            "hot_reload",
            "silence_routes_logging",
            "prune_errors",
        ):
            dev_tools[attr] = kwargs.get(attr, None) or debug

        for attr, _type, default in (
            ("hot_reload_interval", float, 3),
            ("hot_reload_watch_interval", float, 0.5),
            ("hot_reload_max_retry", int, 8),
        ):
            dev_tools[attr] = _type(kwargs.get(attr, None) or default)

        return dev_tools
