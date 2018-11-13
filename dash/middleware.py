from __future__ import print_function

from django.utils.deprecation import MiddlewareMixin
from django.http.response import HttpResponse, HttpResponseNotFound

from . import exceptions


class HttpResponseNoContent(HttpResponse):
    status_code = 204


class CommonMiddleware(MiddlewareMixin):  # pylint: disable=too-few-public-methods
    def process_exception(self, request, exception):  # pylint: disable=unused-argument, no-self-use,
        if isinstance(exception, exceptions.PreventUpdate):  # pylint: disable=no-else-return
            return HttpResponseNoContent()
        elif isinstance(exception, exceptions.InvalidResourceError):
            return HttpResponseNotFound(exception.args[0])

        return None
