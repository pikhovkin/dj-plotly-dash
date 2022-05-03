from __future__ import print_function

import os
import pkgutil
import sys
from collections import OrderedDict
from importlib import import_module

from django.apps import apps
from django.contrib.staticfiles import utils
from django.contrib.staticfiles.finders import FileSystemFinder
from django.core.files import File
from django.core.files.storage import FileSystemStorage

from dash.development.base_component import ComponentRegistry
from dash.fingerprint import build_fingerprint


def _import_module(pkg, m):
    try:
        _pkg = import_module('.' + m, package=pkg)
    except ImportError:
        return

    views_path = os.path.dirname(_pkg.__file__)
    for info in pkgutil.iter_modules([views_path]):
        _import_module(pkg + '.' + m, info[1])


class DashStorage(FileSystemStorage):
    def _open(self, name, mode='rb'):
        new_file_name, ext = name.rsplit('.', 1)
        temporary_file_path = self.path(f'{new_file_name}_.{ext}')
        f = File(open(temporary_file_path, mode))
        f.temporary_file_path = lambda: temporary_file_path
        return f


class DashComponentSuitesFinder(FileSystemFinder):
    prefix = '_dash-component-suites/'
    ignore_patterns = ['*.py', '*.pyc', '*.json']

    def __init__(self, *args, **kwargs):  # pylint: disable=super-init-not-called
        # Import all modules that Dash components were registered in ComponentRegistry
        for app in apps.app_configs.keys():
            _import_module(app, 'views')

        if 'dash_renderer' in sys.modules:
            # Add dash_renderer manually because it is not a component
            ComponentRegistry.registry.add('dash_renderer')

        self.locations = []
        self.storages = OrderedDict()

        for c in [sys.modules[c] for c in ComponentRegistry.registry if c != '__builtin__']:
            prefix = self.prefix + c.__name__
            root = c.__path__[0]

            if (prefix, root) not in self.locations:
                self.locations.append((prefix, root))

        for prefix, root in self.locations:
            filesystem_storage = DashStorage(location=root)
            filesystem_storage.prefix = prefix
            self.storages[root] = filesystem_storage

    def list(self, ignore_patterns):
        """ List static files in all locations.
        """
        for prefix, root in self.locations:  # pylint: disable=unused-variable
            storage = self.storages[root]
            temp_storage = FileSystemStorage(location=storage.location)
            version = import_module(root.split('/')[-1]).__version__
            for path in utils.get_files(storage, ignore_patterns=self.ignore_patterns + (ignore_patterns or [])):
                modified = int(os.stat(temp_storage.path(path)).st_mtime)
                new_path = build_fingerprint(path, version, modified)
                new_file_name, ext = new_path.rsplit('.', 1)
                with temp_storage.open(path) as source_file:
                    temp_storage.save(f'{new_file_name}_.{ext}', source_file)
                yield new_path, storage
