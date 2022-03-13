from dash.testing.browser import Browser


class DashComposite(Browser):
    def __init__(self, server, **kwargs):
        super(DashComposite, self).__init__(**kwargs)
        self.server = server

    def start_server(self, app, **kwargs):
        """Start the local server with app."""

        # # start server with app and pass Dash arguments
        # self.server(app, **kwargs)

        # set the default server_url, it implicitly call wait_for_page
        self.server_url = '{}/dash/{}'.format(self.server.url, app.dash_name)


class DashRComposite(Browser):
    def __init__(self, server, **kwargs):
        super(DashRComposite, self).__init__(**kwargs)
        self.server = server

    def start_server(self, app, cwd=None):

        # # start server with dashR app. The app sets its own run_server args
        # # on the R side, but we support overriding the automatic cwd
        # self.server(app, cwd=cwd)

        # set the default server_url, it implicitly call wait_for_page
        self.server_url = '{}/dash/{}'.format(self.server.url, app.dash_name)


class DashJuliaComposite(Browser):
    def __init__(self, server, **kwargs):
        super(DashJuliaComposite, self).__init__(**kwargs)
        self.server = server

    def start_server(self, app, cwd=None):
        # start server with Dash.jl app. The app sets its own run_server args
        # on the Julia side, but we support overriding the automatic cwd
        self.server(app, cwd=cwd)

        # set the default server_url, it implicitly call wait_for_page
        self.server_url = self.server.url
