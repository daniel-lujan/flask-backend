from mongo_collection import *
from constants import DEFAULT_SETTINGS

def init_database(server):
    """Initializes database connections to
    app required collections.

    Args:
        server (`~flask.Flask`): Flask app.
    """

    global users, clients, bills, files, __app

    __app = server

    users = Collection(server, "users")
    clients = Collection(server, "clients")
    bills = Collection(server, "bills")
    files = FileCollection(server)

def load_app_settings() -> dict:
    """Loads app settings from the database.

    For optimization purposes, app settings are
    expected to be stored in a python variable
    instead of being constantly retrieved from
    the database i.e. use this function once per
    server run.

    Returns:
        `dict`: Settings.
    """

    cx = Collection(__app, "app")

    settings = cx.search_one("CONFIG","settings")
    
    if settings is None:
        cx.insert(dict({"CONFIG":"settings"},**DEFAULT_SETTINGS))
        return DEFAULT_SETTINGS
    
    del settings["_id"]
    del settings["CONFIG"]

    return settings

def update_app_settings(settings: dict) -> None:
    """Updates app settings from the database.

    Args:
        settings (`dict`): Settings.
    """

    cx = Collection(__app, "app")

    try:
        _id = cx.search_one("CONFIG", "settings")["_id"]
        cx.update(_id, dict({"CONFIG":"settings"},**settings))
        
    except TypeError:
        cx.insert(settings)

__app = None

users = None
clients = None
bills = None
files = None

