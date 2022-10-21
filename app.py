from json import dumps
from datetime import timedelta
from os.path import splitext

from flask import Flask, request, session, abort
from flask_cors import CORS
from flask_login import login_required, current_user

import database
from constants import *
from auth import authentication, init_login_manager, role_required, valid_json_template
from static import response


def has_restrict_access() -> bool:
    """Checks whether a response to the current
    request has to be restricted e.g. prevent
    non-admin users from taking other user's data.

    Returns:
        `bool`: `True` if it has restricted access, `False` otherwise.
    """

    for route in USER_RESTRICTED_ROUTES:
        if request.path.split("/")[1] == route:
            return current_user._id and (current_user.role != "admin") and request.method == "GET"


@valid_json_template(TEMPLATE_USER)
def valid_new_user(info: dict) -> int:
    """Checks new user data validity.

    Args:
        info (`dict`): User info.

    Returns:
        `int`: Validation result (`status code`).
    """

    v_username = available_username(info["username"])

    if v_username != STATUS_SUCCESS:
        return v_username

    if not valid_password(info["password"]):
        return STATUS_INVALID_JSON_DATA

    return STATUS_SUCCESS


def available_username(username: str) -> int:
    """Checks username availability.

    Args:
        username (`str`): Username to be checked.

    Returns:
        `int`: Availability result (`status code`).
    """

    if users.search("username", username, strict=True):
        return STATUS_DOCUMENT_ALREADY_EXISTS

    if not valid_username(username):
        return STATUS_INVALID_JSON_DATA

    return STATUS_SUCCESS


def valid_username(username: str) -> bool:
    """Checks username validity.

    Args:
        username (`str`): Username to be checked.

    Returns:
        `bool`: `True` if valid, `False` otherwise.
    """

    if len(username) not in range(*USERNAME_LENGTH):
        return False

    return len(list(c for c in username if c not in USERNAME_ALLOWED_CHARS)) == 0


def valid_password(password: str) -> bool:
    """Checks password validity.

    Args:
        password (`str`): Password to be checked.

    Returns:
        `bool`: `True` if valid, `False` otherwise.
    """

    # if len(password) not in range(*PASSWORD_LENGTH):
    #    return False

    return True


def set_admin(_id: str, value: bool = True) -> dict:
    """Sets `role` attribute of an user.

    Args:
        id (`str`): Unique user ID to operate over.
        value (`bool`, `optional`): `True` for `admin`, `False`
        for user role. Defaults to True.

    Returns:
        dict: Repsonse.
    """

    user = users.find(_id)
    if not user:
        return response(STATUS_DOCUMENT_NOT_FOUND)
    if user["_id"] == current_user._id:
        return response(STATUS_INVALID_JSON_DATA)

    user["role"] = "admin" if value else "normal"
    users.update(_id, user)

    return response(STATUS_SUCCESS)


def valid_file_extension(filename: str) -> bool:
    """Checks whether file extension is allowed. 

    Args:
        filename (str): _description_

    Returns:
        bool: _description_
    """

    if splitext(filename)[1] not in settings["ALLOWED_FILE_EXTENSIONS"]:
        return False

    return True


def valid_file_size(file) -> bool:
    """Checks whether file size is allowed.

    Args:
        size (`werkzeug.datastructures.FileStorage`): File

    Returns:
        `bool`: `True` if valid, `False` otherwise.
    """

    size = len(file.read())
    file.seek(0, 0)

    if not size or size > settings["MAX_FILE_SIZE"]:
        return False

    return True


def valid_file(file) -> bool:
    """Checks file validity.

    Args:
        file (`~werkzeug.datastructures.FileStorage`): File

    Returns:
        `bool`: `True` if valid, `False` otherwise.
    """

    return valid_file_extension(file.filename) and valid_file_size(file)


def valid_settings(settings: dict) -> bool:
    """Checks settings validity based on
    the settings constraints.

    Args:
        settings (`dict`): Settings

    Returns:
        `bool`: `True` if valid, `False` otherwise.
    """

    def valid_max_file_size(size: int) -> bool:
        if size > MAX_FILE_SIZE or size <= 0:
            return False
        
        return True

    def valid_allowed_file_extensions(file_exts: list) -> bool:
        for ext in settings["ALLOWED_FILE_EXTENSIONS"]:
            if ext not in FILE_EXTENSIONS:
                return False
        
        return True

    if "MAX_FILE_SIZE" in settings.keys() and not valid_max_file_size(settings["MAX_FILE_SIZE"]):
        return False

    
    if "ALLOWED_FILE_EXTENSIONS" in settings.keys() and not valid_allowed_file_extensions(settings["ALLOWED_FILE_EXTENSIONS"]):
        return False

    return True


server = Flask(__name__)

server.register_blueprint(authentication)

server.config["MONGO_URI"] = DATABASE_URI
server.config['SECRET_KEY'] = SECRET_KEY
server.config["SESSION_COOKIE_SAMESITE"] = "None"
server.config["SESSION_COOKIE_SECURE"] = True

CORS(server, supports_credentials=True)

database.init_database(server)

users = database.users
clients = database.clients
bills = database.bills
files = database.files

settings = database.load_app_settings()

init_login_manager(server)


@server.before_request
def update_timeout() -> None:
    """Resets current session's timeout timer.
    """

    session.permanent = True
    server.permanent_session_lifetime = timedelta(minutes=LOG_TIMEOUT)
    session.modified = True


@server.after_request
def restrict_response(res):
    """Removes sensitive data from the server response.

    Args:
        res (`~server.response_class`): Preliminary server response.

    Returns:
        `~server.response_class`: Processed response (JSON formatted).
    """

    if current_user.is_authenticated and has_restrict_access():
        response = res.get_json()
        if type(response["response"]) is list:
            response["response"] = list(
                doc for doc in response["response"] if doc["user"] == current_user._id)
        else:
            if response["response"]["user"] != current_user._id:
                return response(STATUS_ACCESS_DENIED)
        res.data = dumps(response)

    return res


@server.route("/clients", methods=["GET"])
@login_required
def get_clients() -> dict:
    """Retrieves the whole clients collection.

    Returns:
        `dict`: Response
    """

    return response(STATUS_SUCCESS, clients.get())


@server.route("/clients/<cl_id>", methods=["GET"])
@login_required
def search_clients(cl_id: str = None) -> dict:
    """Searchs over the `clients.client.id` value.

    Args:
        id (`str`): `clients.client.id` to search for.

    Returns:
        `dict`: Response
    """

    if cl_id:
        return response(STATUS_SUCCESS, clients.search("id", cl_id))
    else:
        return response(STATUS_POINTLESS_REQUEST)


@server.route("/client/<_id>", methods=["GET"])
@login_required
def get_client(_id: str = None) -> dict:
    """Finds and retrieves a client's data.

    Args:
        _id (`str`): Unique client ID

    Returns:
        `dict`: Response
    """

    if _id:
        res = clients.find(_id)
        if res != None:
            return response(STATUS_SUCCESS, res)
        else:
            return response(STATUS_DOCUMENT_NOT_FOUND)
    else:
        return response(STATUS_POINTLESS_REQUEST)


@server.route("/client", methods=["POST"])
@valid_json_template(TEMPLATE_INSERT_CLIENT)
@login_required
def create_client() -> dict:
    """Inserts a client into the clients collection.

    Returns:
        `dict`: Response
    """

    res = clients.insert({
        "id": request.json["id"],
        "user": current_user._id,
        "name": request.json["name"],
        "phone": request.json["phone"],
        "email": request.json["email"],
        "address": request.json["address"],
        "bills": []
    })
    return response(STATUS_SUCCESS, str(res[0]))


@server.route("/client/<_id>", methods=["DELETE"])
@login_required
def delete_client(_id: str = None) -> dict:
    """Deletes a client from the clients collection.

    Args:
        _id (`str`): Unique client ID.

    Returns:
        `dict`: Response
    """

    if _id:
        clients.delete(_id)
        return response(STATUS_SUCCESS)
    else:
        return response(STATUS_POINTLESS_REQUEST)


@server.route("/updateclient/<_id>", methods=["POST"])
@valid_json_template(TEMPLATE_UPDATE_CLIENT)
@login_required
def update_client(_id: str = None) -> dict:
    """Updates a client from the database.

    Args:
        _id (`str`): Unique client ID

    Returns:
        `dict`: Response
    """

    if _id:
        doc = clients.find(_id)
        if doc != None:
            doc["phone"] = request.json["phone"]
            doc["email"] = request.json["email"]
            doc["address"] = request.json["address"]
            clients.update(_id, doc)
            return response(STATUS_SUCCESS)
        else:
            return response(STATUS_DOCUMENT_NOT_FOUND)
    else:
        return response(STATUS_POINTLESS_REQUEST)


@server.route("/file/<filename>")
@login_required
def get_file(filename: str = None):
    """Retrieves a file from the database.

    Args:
        filename (`str`): Filename to search for.

    Returns:
        `~flask.Flask.response_class`: Response streaming the file bytes.
    """

    print(filename)

    if filename:
        if files.file_exists(filename):
            return files.get(filename)
        else:
            abort(404)
    else:
        abort(400)


@server.route("/file", methods=["POST"])
@login_required
def save_file() -> dict:
    """Saves a file into the database.

    Returns:
        `dict`: Response
    """

    try:
        if not valid_file(request.files["File"]):
            return response(STATUS_INVALID_FILE)

        return response(STATUS_SUCCESS, files.save(request.files["File"]))

    except (TypeError, KeyError):
        return response(STATUS_INVALID_REQUEST)


@server.route("/bill", methods=["POST"])
@valid_json_template(TEMPLATE_INSERT_BILL)
@login_required
def add_bill():
    """Inserts a bill into the bills collection.

    Returns:
        `dict`: Response
    """

    if bills.search("ref", request.json["ref"], strict=True):
        return response(STATUS_DOCUMENT_ALREADY_EXISTS)

    client_id = request.json["client"]

    res = bills.insert({
        "ref": request.json["ref"],
        "user": current_user._id,
        "date": request.json["date"],
        "type": request.json["type"],
        "description": request.json["description"],
        "file": request.json["file"] if files.file_exists(request.json["file"]) else "",
        "client": client_id
    })

    if client_id:
        cl = clients.find(client_id)
        cl["bills"].append(res[0])
        clients.update(client_id, cl)

    return response(STATUS_SUCCESS, res[0])


@server.route("/bills")
@login_required
def get_bills() -> dict:
    """Retrieves te whole `bills` collection.

    Returns:
        `dict`: Response
    """

    return response(STATUS_SUCCESS, bills.get())


@server.route("/bills/<ref>")
@login_required
def search_bills(ref: str = None) -> dict:
    """Searchs over the `bills.bill.ref` value.

    Args:
        ref (`str`): Bill's `ref` to search for.

    Returns:
        `dict`: Response
    """

    if ref:
        return response(STATUS_SUCCESS, bills.search("ref", ref))
    else:
        return response(STATUS_POINTLESS_REQUEST)


@server.route("/bill/<_id>", methods=["DELETE"])
@login_required
def delete_bill(_id: str = None) -> dict:
    """Deletes a bill from the `bills` collection.

    Args:
        _id (`str`): Bill's unique ID.

    Returns:
        `dict`: Response
    """

    if not _id:
        return response(STATUS_POINTLESS_REQUEST)

    doc = bills.find(_id)

    if not doc:
        return response(STATUS_DOCUMENT_NOT_FOUND)

    files.delete_by_filename(doc["file"])
    bills.delete(_id)

    return response(STATUS_SUCCESS)


@server.route("/admin/users")
@role_required("admin")
def get_users() -> dict:
    """Retrieves the whole `users` collection. 

    Returns:
        dict: Response
    """

    return response(STATUS_SUCCESS, users.get())


@server.route("/admin/users", methods=["POST"])
@valid_json_template(TEMPLATE_USER)
@role_required("admin")
def create_user() -> dict:
    """Inserts an user into the `users` collection.

    Returns:
        `dict`: Response
    """

    code = valid_new_user(request.json)

    if code != STATUS_SUCCESS:
        return response(code)

    res = users.insert({
        "username": request.json["username"],
        "password": request.json["password"],
        "role": request.json["role"]
    })
    if len(res) == 0:
        return response(STATUS_INVALID_JSON_DATA)

    return response(STATUS_SUCCESS, res[0])


@server.route("/admin/resetpassword", methods=["POST"])
@valid_json_template(TEMPLATE_CHANGE_PASSWORD)
@role_required("admin")
def change_password() -> dict:
    """Updates an user's password.

    Returns:
        `dict`: Response
    """

    docs = users.search("username", request.json["username"], strict=True)

    if len(docs) == 0:
        return response(STATUS_DOCUMENT_NOT_FOUND)

    new_doc = docs[0]
    new_doc["password"] = request.json["password"]
    users.update(new_doc["_id"], new_doc)

    return response(STATUS_SUCCESS)


@server.route("/admin/changepassword", methods=["POST"])
@valid_json_template(TEMPLATE_CHANGE_SELF_PASSWORD)
@role_required("admin")
def change_self_password() -> dict:
    """Changes the current user's password.

    Returns:
        `dict`: Response
    """

    user = users.find(current_user._id)

    data = request.json

    if data["current"] != user["password"]:
        return response(STATUS_ACCESS_DENIED)

    if not valid_password(request.json["new"]):
        return response(STATUS_INVALID_JSON_DATA)

    user["password"] = request.json["new"]
    users.update(user["_id"], user)

    return response(STATUS_SUCCESS)


@server.route("/admin/addadmin/<_id>")
@role_required("admin")
def add_admin(_id: str = None) -> dict:
    """Sets `users.user.role` value to `admin`.

    Args:
        _id (`str`): User unique ID.

    Returns:
        `dict`: Response
    """

    if not _id:
        return response(STATUS_POINTLESS_REQUEST)

    return set_admin(_id)


@server.route("/admin/removeadmin/<_id>")
@role_required("admin")
def remove_admin(_id: str = None) -> dict:
    """Sets `users.user.role` value to default user role.

    Args:
        _id (`str`): User unique ID

    Returns:
        `dict`: Response
    """

    if not _id:
        return response(STATUS_POINTLESS_REQUEST)

    return set_admin(_id, False)


@server.route("/settings")
@login_required
def get_settings() -> dict:
    """Retrieves the public app settings.

    Returns:
        `dict`: Response
    """

    return response(STATUS_SUCCESS, settings)


@server.route("/settings", methods=["POST"])
@valid_json_template(TEMPLATE_UPDATE_SETTINGS, strict=False)
@role_required("admin")
def update_settings() -> dict:
    """Updates app settings from `request.json`
    data.

    Returns:
        `dict`: Response
    """

    data = request.json

    if not valid_settings(data):
        return response(STATUS_INVALID_JSON_DATA)

    settings.update(data)
    
    database.update_app_settings(settings)

    return response(STATUS_SUCCESS)

if __name__ == "__main__":
    server.run()
