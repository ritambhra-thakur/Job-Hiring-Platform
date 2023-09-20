from rest_framework.response import Response


class ResponseOk(Response):

    status_code = 200

    def __init__(self, data=None):
        if data is None:
            data = {"success": 1, "message": "OK", "status": 200}
        if isinstance(data, str):
            data = {"success": 1, "message": data, "status": 200}
        elif isinstance(data, dict):
            if "success" not in data.keys():
                data["success"] = 1
            if "status" not in data.keys():
                data["status"] = 200
            if "message" not in data.keys():
                data["message"] = "OK"
        super(ResponseOk, self).__init__(data, status=200)


class ResponseNotFound(Response):

    status_code = 404

    def __init__(self, data=None):
        if data is None:
            data = {"success": 0, "error": "Not found", "status": 404}
        if isinstance(data, str):
            data = {"success": 0, "error": data, "status": 404}
        elif isinstance(data, dict):
            if "success" not in data.keys():
                data["success"] = 0
            if "status" not in data.keys():
                data["status"] = 404
            if "error" not in data.keys():
                data["error"] = "Not found"
        super(ResponseNotFound, self).__init__(data, status=404)


class ResponseInternalServerError(Response):

    status_code = 500

    def __init__(self, data=None):
        if data is None:
            data = {
                "success": 0,
                "error": "Internal Server Error",
                "status": 500,
            }
        if isinstance(data, str):
            data = {"success": 0, "error": data, "status": 500}
        elif isinstance(data, dict):
            if "success" not in data.keys():
                data["success"] = 0
            if "status" not in data.keys():
                data["status"] = 500
            if "error" not in data.keys():
                data["error"] = "Internal Server Error"
        super(ResponseInternalServerError, self).__init__(data, status=500)


class ResponseForbidden(Response):

    status_code = 403

    def __init__(self, data=None):
        if data is None:
            data = {"success": 0, "error": "Forbidden", "status": 403}
        if isinstance(data, str):
            data = {"success": 0, "error": data, "status": 403}
        elif isinstance(data, dict):
            if "success" not in data.keys():
                data["success"] = 0
            if "status" not in data.keys():
                data["status"] = 403
            if "error" not in data.keys():
                data["error"] = "Forbidden"
        super(ResponseForbidden, self).__init__(data, status=403)


class ResponseNotAllowed(Response):

    status_code = 405

    def __init__(self, data=None):
        if data is None:
            data = {"success": 0, "error": "Not Allowed", "status": 405}
        if isinstance(data, str):
            data = {"success": 0, "error": data, "status": 405}
        elif isinstance(data, dict):
            if "success" not in data.keys():
                data["success"] = 0
            if "status" not in data.keys():
                data["status"] = 405
            if "error" not in data.keys():
                data["error"] = "Not Allowed"
        super(ResponseNotAllowed, self).__init__(data, status=405)


class ResponseBadRequest(Response):

    status_code = 400

    def __init__(self, data=None):
        if data is None:
            data = {"success": 0, "error": "Bad Request", "status": 400}
        if isinstance(data, str):
            data = {"success": 0, "error": data, "status": 400}
        elif isinstance(data, dict):
            if "success" not in data.keys():
                data["success"] = 0
            if "status" not in data.keys():
                data["status"] = 400
            if "error" not in data.keys():
                data["error"] = "Bad Request"
        super(ResponseBadRequest, self).__init__(data, status=400)


class ResponseUnauthorized(Response):

    status_code = 401

    def __init__(self, data=None):
        if data is None:
            data = {"success": 0, "error": "Unauthorized", "status": 401}
        if isinstance(data, str):
            data = {"success": 0, "error": data, "status": 401}
        elif isinstance(data, dict):
            if "success" not in data.keys():
                data["success"] = 0
            if "status" not in data.keys():
                data["status"] = 401
            if "error" not in data.keys():
                data["error"] = "Unauthorized"
        super(ResponseUnauthorized, self).__init__(data, status=401)
