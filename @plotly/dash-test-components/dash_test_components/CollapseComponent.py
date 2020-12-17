# AUTO GENERATED FILE - DO NOT EDIT

from dash.development.base_component import Component, _explicitize_args


class CollapseComponent(Component):
    """A CollapseComponent component.


Keyword arguments:
- children (a list of or a singular dash component, string or number; optional)
- display (boolean; default False)
- id (string; optional)"""
    @_explicitize_args
    def __init__(self, children=None, display=Component.UNDEFINED, id=Component.UNDEFINED, **kwargs):
        self._prop_names = ['children', 'display', 'id']
        self._type = 'CollapseComponent'
        self._namespace = 'dash_test_components'
        self._valid_wildcard_attributes =            []
        self.available_properties = ['children', 'display', 'id']
        self.available_wildcard_properties =            []

        _explicit_args = kwargs.pop('_explicit_args')
        _locals = locals()
        _locals.update(kwargs)  # For wildcard attrs
        args = {k: _locals[k] for k in _explicit_args if k != 'children'}

        for k in []:
            if k not in args:
                raise TypeError(
                    'Required argument `' + k + '` was not specified.')
        super(CollapseComponent, self).__init__(children=children, **args)
