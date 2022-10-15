from os import getenv
from urllib.parse import unquote

# STATUS CODES
STATUS_SUCCESS = 0
STATUS_POINTLESS_REQUEST = 1
STATUS_NOT_FOUND_DOCUMENT = 2
STATUS_ACCESS_DENIED = 3
STATUS_INVALID_JSON_DATA = 4
STATUS_DOCUMENT_ALREADY_EXISTS = 5

# CONFIG
DATABASE_URI = unquote(getenv("APP_DATABASE_URI"))
PORT = 3001
SECRET_KEY = getenv("APP_SECRET_KEY")
LOG_TIMEOUT = 30 # minutes

# ROUTE GROUPS
USER_RESTRICTED_ROUTES = [
    "clients",
    "client",
    "bills"
]

# DOC RESTRICTIONS
USERNAME_LENGTH = (4,37)
USERNAME_ALLOWED_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
PASSWORD_LENGTH = (8,37)
PASSWORD_ALLOWED_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!#$%&/"

# DOC TEMPLATES
TEMPLATE_USER = {
    "username": str,
    "password": str,
    "role": str
}

# REQUEST TEMPLATES
TEMPLATE_LOGIN = {
    "username": str,
    "password": str
}

TEMPLATE_INSERT_CLIENT = {
    "id": str,
    "name": str,
    "phone": str,
    "email": str,
    "address": str
}

TEMPLATE_UPDATE_CLIENT = {
    "phone": str,
    "email": str,
    "address": str
}

TEMPLATE_INSERT_BILL = {
    "ref": str,
    "date": str,
    "type": str,
    "description": str,
    "file": str,
    "client": str
}

TEMPLATE_CHANGE_PASSWORD = {
    "username": str,
    "password": str
}

TEMPLATE_CHANGE_SELF_PASSWORD = {
    "current": str,
    "new": str
}