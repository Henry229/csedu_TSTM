import json

from flask import current_app

from . import httpstatus as status

"""
200 - OK	Everything worked as expected.
400 - Bad Request	The request was unacceptable, often due to missing a required parameter.
401 - Unauthorized	No valid API key provided.
402 - Request Failed	The parameters were valid but the request failed.
404 - Not Found	The requested resource doesn't exist.
409 - Conflict	The request conflicts with another request (perhaps due to using the same idempotent key).
429 - Too Many Requests	Too many requests hit the API too quickly. We recommend an exponential backoff of your requests.
500, 502, 503, 504 - Server Errors	Something went wrong on the server.
"""


class ErrorType:
    def __init__(self, error_type, message):
        self.type = error_type
        self.message = message


AUTHENTICATION_ERROR = ErrorType('authentication_error', 'Authentication error')
INVALID_REQUEST_ERROR = ErrorType('invalid_request_error', 'Invalid request error')


def success(data=None, meta=None, status_code=status.HTTP_200_OK):
    if type(data) is list:
        obj = 'list'
    else:
        obj = 'object'
    rsp = {
        'result': 'success',
        'object': obj,
        'data': data,
    }
    if meta:
        rsp['meta'] = meta

    return current_app.response_class(
        (json.dumps(rsp)),
        mimetype='application/json',
        status=status_code
    )


def fail(error_type, message, param=None, code=None, status_code=400):
    """
     :param error_type: The type of error returned. Can be: api_error, authentication_error,
          idempotency_error invalid_request_error, or rate_limit_error.
     :param message: A human-readable message providing more details about the error.
     :param param: The parameter the error relates to if the error is parameter-specific.
          You can use this to display a message near the correct form field, for example.
     :param code: (optional)A short string describing the kind of error that occurred.
     :param status_code: HTTP status code

     TYPE:
     api_error	API errors cover any other type of problem (e.g., a temporary problem with servers).
     authentication_error	Failure to properly authenticate yourself in the request.
     idempotency_error	Idempotency errors occur when an Idempotency-Key is re-used on a request that does not match the API endpoint and parameters of the first.
     invalid_request_error	Invalid request errors arise when your request has invalid parameters.
     rate_limit_error	Too many requests hit the API too quickly.

    :return:
    """
    rsp = {
        'result': 'fail',
        'type': error_type,
        'message': message
    }
    if param:
        rsp['param'] = param
    if code:
        rsp['code'] = code
    return current_app.response_class(
        (json.dumps(rsp)),
        mimetype='application/json',
        status=status_code
    )


def bad_request(param=None, response_code=None, message=None):
    """

    :param param:
    :param response_code: ResponseCodeItem
    :param message:
    :return:
    """
    code, msg = None, None
    if response_code:
        code = response_code.code
        msg = response_code.message
    if message:
        msg = message
    return fail(error_type=INVALID_REQUEST_ERROR.type, message=msg,
                param=param, code=code,
                status_code=status.HTTP_400_BAD_REQUEST)


def not_found(param=None, response_code=None, message=None):
    """

    :param param:
    :param response_code:
    :param message:
    :return:
    """
    code, msg = None, None
    if response_code:
        code = response_code.code
        msg = response_code.message
    if message:
        msg = message
    return fail(error_type=INVALID_REQUEST_ERROR.type, message=msg,
                param=param, code=code,
                status_code=status.HTTP_404_NOT_FOUND)


def unauthorized():
    return fail(error_type=AUTHENTICATION_ERROR.type, message=AUTHENTICATION_ERROR.message,
                status_code=status.HTTP_401_UNAUTHORIZED)
