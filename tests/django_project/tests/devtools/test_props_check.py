import dash_html_components as html
import dash_core_components as dcc

from dash.dependencies import Input, Output

from tests import DashView
from tests.IntegrationTests import IntegrationTests


test_cases = {
    "not-boolean": {
        "fail": True,
        "name": 'simple "not a boolean" check',
        "component": dcc.Graph,
        "props": {"animate": 0},
    },
    "missing-required-nested-prop": {
        "fail": True,
        "name": 'missing required "value" inside options',
        "component": dcc.Checklist,
        "props": {"options": [{"label": "hello"}], "values": ["test"]},
    },
    "invalid-nested-prop": {
        "fail": True,
        "name": "invalid nested prop",
        "component": dcc.Checklist,
        "props": {
            "options": [{"label": "hello", "value": True}],
            "values": ["test"],
        },
    },
    "invalid-arrayOf": {
        "fail": True,
        "name": "invalid arrayOf",
        "component": dcc.Checklist,
        "props": {"options": "test", "values": []},
    },
    "invalid-oneOf": {
        "fail": True,
        "name": "invalid oneOf",
        "component": dcc.Input,
        "props": {"type": "test"},
    },
    "invalid-oneOfType": {
        "fail": True,
        "name": "invalid oneOfType",
        "component": dcc.Input,
        "props": {"max": True},
    },
    "invalid-shape-1": {
        "fail": True,
        "name": "invalid key within nested object",
        "component": dcc.Graph,
        "props": {"config": {"asdf": "that"}},
    },
    "invalid-shape-2": {
        "fail": True,
        "name": "nested object with bad value",
        "component": dcc.Graph,
        "props": {"config": {"edits": {"legendPosition": "asdf"}}},
    },
    "invalid-shape-3": {
        "fail": True,
        "name": "invalid oneOf within nested object",
        "component": dcc.Graph,
        "props": {"config": {"toImageButtonOptions": {"format": "asdf"}}},
    },
    "invalid-shape-4": {
        "fail": True,
        "name": "invalid key within deeply nested object",
        "component": dcc.Graph,
        "props": {"config": {"toImageButtonOptions": {"asdf": "test"}}},
    },
    "invalid-shape-5": {
        "fail": True,
        "name": "invalid not required key",
        "component": dcc.Dropdown,
        "props": {
            "options": [{"label": "new york", "value": "ny", "typo": "asdf"}]
        },
    },
    "string-not-list": {
        "fail": True,
        "name": "string-not-a-list",
        "component": dcc.Checklist,
        "props": {
            "options": [{"label": "hello", "value": "test"}],
            "values": "test",
        },
    },
    "no-properties": {
        "fail": False,
        "name": "no properties",
        "component": dcc.Graph,
        "props": {},
    },
    "nested-children": {
        "fail": True,
        "name": "nested children",
        "component": html.Div,
        "props": {"children": [[1]]},
    },
    "deeply-nested-children": {
        "fail": True,
        "name": "deeply nested children",
        "component": html.Div,
        "props": {"children": html.Div([html.Div([3, html.Div([[10]])])])},
    },
    "dict": {
        "fail": True,
        "name": "returning a dictionary",
        "component": html.Div,
        "props": {"children": {"hello": "world"}},
    },
    "nested-prop-failure": {
        "fail": True,
        "name": "nested string instead of number/null",
        "component": dcc.Graph,
        "props": {
            "figure": {"data": [{}]},
            "config": {
                "toImageButtonOptions": {"width": None, "height": "test"}
            },
        },
    },
    "allow-null": {
        "fail": False,
        "name": "nested null",
        "component": dcc.Graph,
        "props": {
            "figure": {"data": [{}]},
            "config": {"toImageButtonOptions": {"width": None, "height": None}},
        },
    },
    "allow-null-2": {
        "fail": False,
        "name": "allow null as value",
        "component": dcc.Dropdown,
        "props": {"value": None},
    },
    "allow-null-3": {
        "fail": False,
        "name": "allow null in properties",
        "component": dcc.Input,
        "props": {"value": None},
    },
    "allow-null-4": {
        "fail": False,
        "name": "allow null in oneOfType",
        "component": dcc.Store,
        "props": {"id": "store", "data": None},
    },
    "long-property-string": {
        "fail": True,
        "name": "long property string with id",
        "component": html.Div,
        "props": {"id": "pink div", "style": "color: hotpink; " * 1000},
    },
    "multiple-wrong-values": {
        "fail": True,
        "name": "multiple wrong props",
        "component": dcc.Dropdown,
        "props": {"id": "dropdown", "value": 10, "options": "asdf"},
    },
    "boolean-html-properties": {
        "fail": True,
        "name": "dont allow booleans for dom props",
        "component": html.Div,
        "props": {"contentEditable": True},
    },
    "allow-exact-with-optional-and-required-1": {
        "fail": False,
        "name": "allow exact with optional and required keys",
        "component": dcc.Dropdown,
        "props": {
            "options": [{"label": "new york", "value": "ny", "disabled": False}]
        },
    },
    "allow-exact-with-optional-and-required-2": {
        "fail": False,
        "name": "allow exact with optional and required keys 2",
        "component": dcc.Dropdown,
        "props": {"options": [{"label": "new york", "value": "ny"}]},
    },
}


class Tests(IntegrationTests):
    def test_dveh_prop_check_errors_with_path(self):
        class DashPropCheckErrorsWithPath(DashView):
            dash_name = 'dveh_prop_check_errors_with_path'
            dash_components = {html.__name__, dcc.__name__}

            def __init__(self, **kwargs):
                super(DashPropCheckErrorsWithPath, self).__init__(**kwargs)

                self.dash._dev_tools.ui = True
                self.dash._dev_tools.props_check = True
                self.dash._dev_tools.serve_dev_bundles = True

                self.dash.layout = html.Div([
                    html.Div(id="content"),
                    dcc.Location(id="location")
                ])
                self.dash.callback(Output("content", "children"),
                                   [Input("location", "hash")])(self.display_content)

            def display_content(self, hash):
                if hash is None or hash in "#/":
                    return "Initial state"

                test_case = test_cases[hash.strip("#/")]
                return html.Div(
                    id="new-component",
                    children=test_case["component"](**test_case["props"]),
                )

        for tc in test_cases:
            self.open('dash/{}#{}'.format(DashPropCheckErrorsWithPath.dash_name, tc))

            if test_cases[tc]["fail"]:
                self.find_element(".test-devtools-error-toggle").click()
            else:
                self.find_element("#new-component")
