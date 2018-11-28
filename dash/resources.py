import json
import warnings
import os

from .development.base_component import ComponentRegistry


class Resources(object):
    def __init__(self, resource_name, layout):
        self._resources = []
        self.resource_name = resource_name
        self.layout = layout

    def append_resource(self, resource):
        self._resources.append(resource)

    def _filter_resources(self, all_resources, dev_bundles=False):
        filtered_resources = []
        for s in all_resources:
            filtered_resource = {}
            if 'namespace' in s:
                filtered_resource['namespace'] = s['namespace']
            if 'external_url' in s and not self.config.serve_locally:
                filtered_resource['external_url'] = s['external_url']
            elif 'dev_package_path' in s and dev_bundles:
                filtered_resource['relative_package_path'] = (
                    s['dev_package_path']
                )
            elif 'relative_package_path' in s:
                filtered_resource['relative_package_path'] = (
                    s['relative_package_path']
                )
            elif 'absolute_path' in s:
                filtered_resource['absolute_path'] = s['absolute_path']
            elif 'asset_path' in s:
                info = os.stat(s['filepath'])
                filtered_resource['asset_path'] = s['asset_path']
                filtered_resource['ts'] = info.st_mtime
            elif self.config.serve_locally:
                warnings.warn(
                    'A local version of {} is not available'.format(
                        s['external_url']
                    )
                )
                continue
            else:
                raise Exception(
                    '{} does not have a '
                    'relative_package_path, absolute_path, or an '
                    'external_url.'.format(
                        json.dumps(filtered_resource)
                    )
                )

            filtered_resources.append(filtered_resource)

        return filtered_resources

    def get_all_resources(self, affix='', module_names=None, dev_bundles=False):
        all_resources = ComponentRegistry.get_resources(self.resource_name, affix=affix, module_names=module_names)
        all_resources.extend(self._resources)

        return self._filter_resources(all_resources, dev_bundles)


class Css(object):
    def __init__(self, layout=None):
        self._resources = Resources('_css_dist', layout)
        self._resources.config = self.config

    def _update_layout(self, layout):
        self._resources.layout = layout

    def append_css(self, stylesheet):
        self._resources.append_resource(stylesheet)

    def get_all_css(self, affix='', module_names=None):
        return self._resources.get_all_resources(affix=affix, module_names=module_names)

    # pylint: disable=no-init, too-few-public-methods
    class config(object):
        infer_from_layout = True
        serve_locally = False


class Scripts(object):
    def __init__(self, layout=None):
        self._resources = Resources('_js_dist', layout)
        self._resources.config = self.config

    def _update_layout(self, layout):
        self._resources.layout = layout

    def append_script(self, script):
        self._resources.append_resource(script)

    def get_all_scripts(self, affix='', module_names=None, dev_bundles=False):
        return self._resources.get_all_resources(affix=affix, module_names=module_names, dev_bundles=dev_bundles)

    # pylint: disable=no-init, too-few-public-methods
    class config(object):
        infer_from_layout = True
        serve_locally = False
