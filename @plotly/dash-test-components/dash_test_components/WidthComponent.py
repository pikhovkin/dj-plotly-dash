# AUTO GENERATED FILE - DO NOT EDIT

from dash.development.base_component import Component, _explicitize_args


class WidthComponent(Component):
    """A WidthComponent component.


Keyword arguments:
- id (string; optional)
- width (number; default 0)"""
    @_explicitize_args
    def __init__(self, id=Component.UNDEFINED, width=Component.UNDEFINED, **kwargs):
        self._prop_names = ['id', 'width']
        self._type = 'WidthComponent'
        self._namespace = 'dash_test_components'
        self._valid_wildcard_attributes =            []
        self.available_properties = ['id', 'width']
        self.available_wildcard_properties =            []

        _explicit_args = kwargs.pop('_explicit_args')
        _locals = locals()
        _locals.update(kwargs)  # For wildcard attrs
        args = {k: _locals[k] for k in _explicit_args if k != 'children'}

        for k in []:
            if k not in args:
                raise TypeError(
                    'Required argument `' + k + '` was not specified.')
        super(WidthComponent, self).__init__(**args)
