from __future__ import print_function

import sys
from collections import OrderedDict

from django.contrib.staticfiles import utils
from django.core.files.storage import FileSystemStorage
from django.contrib.staticfiles.finders import BaseFinder

from ..development.base_component import ComponentRegistry


class DashComponentSuitesFinder(BaseFinder):
    prefix = '_dash-component-suites/'
    ignore_patterns = ['*.py', '*.pyc', '*.json']

    def __init__(self, *args, **kwargs):
        self.locations = []
        self.storages = OrderedDict()

        for c in [sys.modules[c] for c in ComponentRegistry.registry if c != '__builtin__']:
            prefix = self.prefix + c.__name__
            root = c.__path__[0]

            if (prefix, root) not in self.locations:
                self.locations.append((prefix, root))

        for prefix, root in self.locations:
            filesystem_storage = FileSystemStorage(location=root)
            filesystem_storage.prefix = prefix
            self.storages[root] = filesystem_storage

        super(DashComponentSuitesFinder, self).__init__(*args, **kwargs)

    def list(self, ignore_patterns):
        """ List static files in all locations.
        """
        for prefix, root in self.locations:
            storage = self.storages[root]
            for path in utils.get_files(storage, ignore_patterns=self.ignore_patterns + (ignore_patterns or [])):
                yield path, storage
