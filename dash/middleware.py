from __future__ import print_function

from django.http.response import HttpResponse, HttpResponseNotFound
from django import VERSION
if VERSION[:2] == (1, 9):
    MiddlewareMixin = object
else:
    from django.utils.deprecation import MiddlewareMixin

from . import exceptions  # noqa: F402 pylint: disable=wrong-import-position


class HttpResponseNoContent(HttpResponse):
    status_code = 204


class CommonMiddleware(MiddlewareMixin):  # pylint: disable=too-few-public-methods
    def process_exception(self, request, exception):  # pylint: disable=unused-argument, no-self-use,
        if isinstance(exception, exceptions.PreventUpdate):  # pylint: disable=no-else-return
            return HttpResponseNoContent()
        elif isinstance(exception, exceptions.InvalidResourceError):
            return HttpResponseNotFound(exception.args[0])

        return None
