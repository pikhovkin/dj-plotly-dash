# AUTO GENERATED FILE - DO NOT EDIT

from dash.development.base_component import Component, _explicitize_args


class MyNestedComponent(Component):
    """A MyNestedComponent component.
MyNestedComponent description

Keyword arguments:
- id (string; optional): The id of the component
- value (string; default ''): The value to display"""
    @_explicitize_args
    def __init__(self, id=Component.UNDEFINED, value=Component.UNDEFINED, **kwargs):
        self._prop_names = ['id', 'value']
        self._type = 'MyNestedComponent'
        self._namespace = 'dash_generator_test_component_nested'
        self._valid_wildcard_attributes =            []
        self.available_properties = ['id', 'value']
        self.available_wildcard_properties =            []

        _explicit_args = kwargs.pop('_explicit_args')
        _locals = locals()
        _locals.update(kwargs)  # For wildcard attrs
        args = {k: _locals[k] for k in _explicit_args if k != 'children'}

        for k in []:
            if k not in args:
                raise TypeError(
                    'Required argument `' + k + '` was not specified.')
        super(MyNestedComponent, self).__init__(**args)
