from __future__ import print_function

import json
import time
import types

from django.http.response import HttpResponse, HttpResponseNotFound
from django import VERSION
if VERSION[:2] == (1, 9):
    MiddlewareMixin = object
else:
    from django.utils.deprecation import MiddlewareMixin

from . import exceptions  # noqa: F402 pylint: disable=wrong-import-position
from ._utils import inputs_to_dict, split_callback_id


class HttpResponseNoContent(HttpResponse):
    status_code = 204


class CommonMiddleware(MiddlewareMixin):  # pylint: disable=too-few-public-methods
    def process_exception(self, request, exception):  # pylint: disable=unused-argument, no-self-use,
        if isinstance(exception, exceptions.PreventUpdate):
            return HttpResponseNoContent()
        elif isinstance(exception, exceptions.InvalidResourceError):
            return HttpResponseNotFound(exception.args[0])

        return None

    def _set_record_timing(self, request):
        def record_timing(self, name, duration=None, description=None):
            """Records timing information for a server resource.

            :param name: The name of the resource.
            :type name: string

            :param duration: The time in seconds to report. Internally, this
                is rounded to the nearest millisecond.
            :type duration: float or None

            :param description: A description of the resource.
            :type description: string or None
            """
            timing_information = getattr(self, "timing_information", {})
            if name in timing_information:
                raise KeyError('Duplicate resource name "{}" found.'.format(name))

            timing_information[name] = {"dur": round(duration * 1000), "desc": description}

            setattr(self, "timing_information", timing_information)

        request.record_timing = types.MethodType(record_timing, request)
        # request.record_timing = record_timing.__get__(request.__class__, request)

        request.timing_information = {
            "__dash_server": {"dur": time.time(), "desc": None}
        }

    def process_request(self, request):
        if '/_dash-update-component' not in request.path:
            return None

        body = json.loads(request.body)
        request.inputs_list = body.get('inputs', [])
        request.states_list = body.get('state', [])
        request.output = body['output']
        request.outputs_list = body.get('outputs', []) or split_callback_id(request.output)

        request.input_values = inputs_to_dict(request.inputs_list)
        request.state_values = inputs_to_dict(request.states_list)
        changed_props = body.get('changedPropIds', [])
        request.triggered_inputs = [
            {'prop_id': x, 'value': request.input_values.get(x)} for x in changed_props
        ]
        # self._set_record_timing(request)

    # def process_response(self, request, response):
    #     if '/_dash-update-component' not in request.path:
    #         return response
    #
    #     dash_total = request.timing_information["__dash_server"]
    #     dash_total["dur"] = round((time.time() - dash_total["dur"]) * 1000)
    #
    #     values = []
    #     for name, info in request.timing_information.items():
    #         value = name
    #         if info.get("desc") is not None:
    #             value += ';desc="{}"'.format(info["desc"])
    #
    #         if info.get("dur") is not None:
    #             value += ";dur={}".format(info["dur"])
    #
    #         values.append(value)
    #
    #     response["Server-Timing"] = ', '.join(values)
    #     return response
