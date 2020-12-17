from multiprocessing import Value

from dash.dependencies import Input, Output, State, MATCH, ALL, ALLSMALLER
import dash_html_components as html
import dash_core_components as dcc

from ..integration import BaseDashView


def todo_app(content_callback=False):
    class DashView(BaseDashView):
        content = html.Div(
            [
                html.Div("Dash To-Do list"),
                dcc.Input(id="new-item"),
                html.Button("Add", id="add"),
                html.Button("Clear Done", id="clear-done"),
                html.Div(id="list-container"),
                html.Hr(),
                html.Div(id="totals"),
            ]
        )

        style_todo = {"display": "inline", "margin": "10px"}
        style_done = {"textDecoration": "line-through", "color": "#888"}
        style_done.update(style_todo)

        list_calls = Value("i", 0)
        style_calls = Value("i", 0)
        preceding_calls = Value("i", 0)
        total_calls = Value("i", 0)

        def __init__(self, **kwargs):
            super(DashView, self).__init__(**kwargs)

            if content_callback:
                self.dash.layout = html.Div([html.Div(id="content"), dcc.Location(id="url")])

                self.dash.callback(Output("content", "children"), [Input("url", "pathname")])(self.display_content)
            else:
                self.dash.layout = self.content

            self.dash.callback(
                Output("list-container", "children"),
                Output("new-item", "value"),
                Input("add", "n_clicks"),
                Input("new-item", "n_submit"),
                Input("clear-done", "n_clicks"),
                State("new-item", "value"),
                State({"item": ALL}, "children"),
                State({"item": ALL, "action": "done"}, "value"),
            )(self.edit_list)
            self.dash.callback(
                Output({"item": MATCH}, "style"),
                Input({"item": MATCH, "action": "done"}, "value"),
            )(self.mark_done)
            self.dash.callback(
                Output({"item": MATCH, "preceding": True}, "children"),
                Input({"item": ALLSMALLER, "action": "done"}, "value"),
                Input({"item": MATCH, "action": "done"}, "value"),
            )(self.show_preceding)
            self.dash.callback(
                Output("totals", "children"), Input({"item": ALL, "action": "done"}, "value")
            )(self.show_totals)

        def display_content(self, _):
            return self.content

        def edit_list(self, add, add2, clear, new_item, items, items_done):
            self.list_calls.value += 1
            triggered = [t["prop_id"] for t in self.request.triggered_inputs]
            adding = len(
                [1 for i in triggered if i in ("add.n_clicks", "new-item.n_submit")]
            )
            clearing = len([1 for i in triggered if i == "clear-done.n_clicks"])
            new_spec = [
                (text, done)
                for text, done in zip(items, items_done)
                if not (clearing and done)
            ]
            if adding:
                new_spec.append((new_item, []))
            new_list = [
                html.Div(
                    [
                        dcc.Checklist(
                            id={"item": i, "action": "done"},
                            options=[{"label": "", "value": "done"}],
                            value=done,
                            style={"display": "inline"},
                        ),
                        html.Div(
                            text, id={"item": i}, style=self.style_done if done else self.style_todo
                        ),
                        html.Div(id={"item": i, "preceding": True}, style=self.style_todo),
                    ],
                    style={"clear": "both"},
                )
                for i, (text, done) in enumerate(new_spec)
            ]
            return [new_list, "" if adding else new_item]

        def mark_done(self, done):
            self.style_calls.value += 1
            return self.style_done if done else self.style_todo

        def show_preceding(self, done_before, this_done):
            self.preceding_calls.value += 1
            if this_done:
                return ""
            all_before = len(done_before)
            done_before = len([1 for d in done_before if d])
            out = "{} of {} preceding items are done".format(done_before, all_before)
            if all_before == done_before:
                out += " DO THIS NEXT!"
            return out

        def show_totals(self, done):
            self.total_calls.value += 1
            count_all = len(done)
            count_done = len([d for d in done if d])
            result = "{} of {} items completed".format(count_done, count_all)
            if count_all:
                result += " - {}%".format(int(100 * count_done / count_all))
            return result

    return DashView
