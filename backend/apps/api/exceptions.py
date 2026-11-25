from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler


def _plain(value):
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return str(value)


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, APIException) and response.status_code == 403:
        detail = str(exc.detail)
        if detail.startswith("CSRF Failed:"):
            code = "csrf_failed"
        elif getattr(exc, "default_code", "") == "not_authenticated":
            code = "not_authenticated"
        else:
            code = "permission_denied"
    elif response.status_code == 400:
        code = "validation_error"
    elif response.status_code == 404:
        code = "not_found"
    else:
        code = getattr(exc, "default_code", "api_error")

    if isinstance(response.data, dict) and "detail" in response.data:
        detail = str(response.data["detail"])
        errors = {}
    else:
        detail = "Hay campos que deben corregirse."
        errors = _plain(response.data)

    response.data = {
        "detail": detail,
        "code": code,
        "errors": errors,
    }
    return response
