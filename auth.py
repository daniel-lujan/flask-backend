from functools import wraps

from flask import Blueprint, request
from flask_login import LoginManager, current_user, login_user, logout_user, login_required

import database
from constants import *
from models import User
from static import response, valid_doc_datatype

def role_required(*roles:str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if current_user.is_authenticated and current_user.role in roles:
                return func(*args, **kwargs)
            else:
                return response(STATUS_ACCESS_DENIED)
        return wrapper
    return decorator

def valid_json_template(template:dict, strict: bool = True):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if valid_doc_datatype(request.json, template, strict=strict):
                return func(*args, **kwargs)
            else:
                return response(STATUS_INVALID_JSON_DATA)

        return wrapper
    return decorator

def authenticate(username:str, password:str):
    """Authenticates user.

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

authentication = Blueprint("authentication",__name__)

def init_login_manager(server):
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
def login():
    
    if not valid_doc_datatype(request.json, TEMPLATE_LOGIN):
        return response(STATUS_INVALID_JSON_DATA)

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
def logout():
    logout_user()
    return response(STATUS_SUCCESS)

@authentication.route("/auth/log")
@login_required
def log():
    return {
        "status": STATUS_SUCCESS,
        "response": {
            "user": current_user._id,
            "username": current_user.username,
            "role": current_user.role
        }
    }

@authentication.route("/auth/test")
def test():
    return "done"