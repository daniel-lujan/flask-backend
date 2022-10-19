from functools import wraps

from flask import Blueprint, request
from flask_login import LoginManager, current_user, login_user, logout_user, login_required

import database
from constants import *
from models import User
from static import response, valid_doc_datatype


def role_required(*roles: str):
    """Function decorator. Checks whether
     current user matches with required role.

     This decorator is expected to be used
     inside a request context.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if current_user.is_authenticated and current_user.role in roles:
                return func(*args, **kwargs)
            else:
                return response(STATUS_ACCESS_DENIED)
        return wrapper
    return decorator


def valid_json_template(template: dict, strict: bool = True):
    """Function decorator. Checks current `request.json`
    validity by comparing it with a `template`.

    This decorator is expected to be used
    inside a request context.

    Args:
        template (dict): Template which `request.json` is
        compared.
        strict (bool, optional): Strict comparison. Defaults to True.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if valid_doc_datatype(request.json, template, strict=strict):
                return func(*args, **kwargs)
            else:
                return response(STATUS_INVALID_JSON_DATA)

        return wrapper
    return decorator


def authenticate(username: str, password: str) -> str | None:
    """Authenticates user's credentials.

    Args:
        username (`str`): Username
        password (`str`): Password

    Returns:
        `str` | `None`: Authenticated unique user ID, `None`
        if not authenticated.
    """

    users_ = database.users.search(
        "username",
        username,
        strict=True)

    if users_ and users_[0]["password"] == password:
        return users_[0]["_id"]
    else:
        return None


authentication = Blueprint("authentication", __name__)


def init_login_manager(server) -> None:
    """Initializes a login manager for `~flask.Flask`
    app. Also sets up `user_loader` and `unauthorized_handler`
    functions.

    Args:
        server (`~flask.Flask`): Flask app.
    """

    login_manager = LoginManager(server)

    @login_manager.user_loader
    def load_user(_id: str):

        user = database.users.find(_id)

        if user:
            return User(**user)
        else:
            return None

    @login_manager.unauthorized_handler
    def handle_unauthorized():
        return response(STATUS_ACCESS_DENIED)


@authentication.route("/auth/log", methods=["POST"])
@valid_json_template(TEMPLATE_LOGIN)
def login() -> dict:
    """Authenticates and logs a user in.

    Returns:
        `dict`: Response
    """

    auth = authenticate(request.json["username"],
                        request.json["password"])

    if auth is None:
        return response(STATUS_ACCESS_DENIED)

    user_info = database.users.find(auth)

    login_user(User(**user_info), remember=False)

    return response(STATUS_SUCCESS, {
        "role": user_info["role"]
    })


@authentication.route("/auth/log", methods=["DELETE"])
@login_required
def logout() -> dict:
    """Logs current user out.

    Returns:
        dict: Response
    """

    logout_user()

    return response(STATUS_SUCCESS)


@authentication.route("/auth/log")
@login_required
def log() -> dict:
    """Retrieves current user's data.

    Returns:
        dict: Response
    """

    return response(STATUS_SUCCESS, {
        "user": current_user._id,
        "username": current_user.username,
        "role": current_user.role
    })
