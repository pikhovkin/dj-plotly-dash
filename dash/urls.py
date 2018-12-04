from django.conf.urls import include, url

from .views import BaseDashView


urlpatterns = [
    url(r'^(?P<dash_name>[\-\w_0-9]+)/', include([
        url(r'^$', BaseDashView.serve_dash_index),
        url(r'^(?P<path>[\-\w_.@0-9]+)/$', BaseDashView.serve_dash_index),
        url(r'^_dash-dependencies', BaseDashView.serve_dash_dependencies),
        url(r'^_dash-layout', BaseDashView.serve_dash_layout),
        url(r'^_dash-update-component', BaseDashView.serve_dash_upd_component),
        url(r'^_dash-component-suites/(?P<package_name>[\-\w_@0-9]+)/'
            r'(?P<path_in_package_dist>[\-\w_.@0-9]+)',
            BaseDashView.serve_dash_component_suites),
        url(r'^_dash-routes', BaseDashView.serve_dash_routes),
        url(r'^_reload-hash', BaseDashView.serve_reload_hash)
    ]))
]
