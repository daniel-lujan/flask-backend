# STATUS CODES
STATUS_SUCCESS = 0
STATUS_POINTLESS_REQUEST = 1
STATUS_NOT_FOUND_DOCUMENT = 2
STATUS_ACCESS_DENIED = 3
STATUS_INVALID_JSON_DATA = 4
STATUS_DOCUMENT_ALREADY_EXISTS = 5

#DATABSE CONFIG
DATABASE_NAME = "app_database"
DATABASE_USER = "mongoclusteradmin"
DATABASE_PASSWORD = "lBOZuVc42sMTcpvd"
MONGO_URI = f"mongodb+srv://{DATABASE_USER}:{DATABASE_PASSWORD}@mongocluster.ojsl9i5.mongodb.net/{DATABASE_NAME}?retryWrites=true&w=majority"
#MONGO_URI = "mongodb://localhost:27017"

# SERVER CONFIG
PORT = 3001


# LOG CONFIG
HASH_SALT = "$2a$10$azQKaZl0cgxsYrPZewNJmu"
LOG_TIMEOUT = 1800
TIMEOUT_CHECK = 300


# ROUTE GROUPS
PRIVATE_ROUTES = [
    "clients",
    "client",
    "updateclient",
    "file",
    "bill",
    "bills"]
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
    "admin": bool
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