from json import dumps
from time import time

from flask import Flask, request
from flask_apscheduler import APScheduler
from flask_cors import CORS

from constants import *
from mongo_collection import Collection, FileCollection


def logged(remote_address: str) -> bool:
    """Checks whether an IP address is logged.

    Args:
        remote_address (`str`): IP address to check over.

    Returns:
        `bool`: `True` if logged, `False` otherwise.
    """

    try:
        return logged_ips[request.environ.get("HTTP_X_REAL_IP", remote_address)]["logged"]
    except KeyError:
        return False


def is_admin(user_id: str) -> bool:
    """Checks whether an user has admin role.

    Args:
        user_id (`str`): User unique ID to check over.

    Returns:
        `bool`: `True` if admin, `False` otherwise.
    """

    try:
        return users.find(user_id)["admin"]
    except TypeError:
        return False


def route_is_private(route: str) -> bool:
    """Checks whether a server route is private i.e. it can only
    be accessed by logged users.

    Args:
        route (`str`): Route to check over.

    Returns:
        `bool`: `True` if route is private, `False` otherwise.
    """

    for r in PRIVATE_ROUTES:
        if route.split("/")[1] == r:
            return True

    return False


def route_is_only_admin(route: str) -> bool:
    """Checks whether a route is only allowed for admin users.

    Args:
        route (`str`): Route.

    Returns:
        `bool`: _description_
    """

    return route.split("/")[1] == "admin"


def timeout_check():
    """Checks all logged users last requests and log out if they exceed log timeout.
    """

    for u in list(logged_ips.keys()):
        if time() - logged_ips[u]["lastrequest"] > LOG_TIMEOUT:
            del logged_ips[u]


def get_user_id_by_ip(ip_addr: str) -> str | None:
    """Gets user unique ID by given IP address.

    Args:
        ip_addr (`str`): IP address.

    Returns:
        `str` | `None`: User unique ID, `None` if IP address is not logged.
    """

    try:
        return logged_ips[request.environ.get("HTTP_X_REAL_IP", ip_addr)]["user"]
    except KeyError:
        return None


def has_restrict_access() -> bool:
    """Checks whether a response to the current request has to be
    restricted e.g. prevent non-admin users from taking other user's data.

    Returns:
        `bool`: `True` if it has restricted access, `False` otherwise.
    """

    u_id = get_user_id_by_ip(request.remote_addr)

    for route in USER_RESTRICTED_ROUTES:
        if request.path.split("/")[1] == route:
            return u_id and (not is_admin(u_id)) and request.method == "GET"


def valid_doc_datatype(document: dict, template: dict, strict=True) -> bool:
    """Checks document datatype validity i.e. the datatype of
    every value in `document` match the corresponding one at
    `template`.

    Args:
        document (`dict`): Document to validate.
        template (`dict`): Datatype template
        strict (`bool`, `optional`): `document` shall contain
        every key of `template`. Defaults to `True`.

    Returns:
        `bool`: Document validity.
    """

    def strict_validation():
        for field in template:
            try:
                if type(document[field]) is not template[field]:
                    return False
            except KeyError:
                return False

        return True

    def non_strict_validation():
        for field in template:
            try:
                if type(document[field]) is not template[field]:
                    return False
            except KeyError:
                pass

        return True

    return strict_validation() if strict else non_strict_validation()


def valid_new_user(info: dict) -> int:
    """Checks new user validity.

    Args:
        info (`dict`): User info.

    Returns:
        `int`: Validation result (`status code`).
    """

    if not valid_doc_datatype(info, TEMPLATE_USER):
        return STATUS_INVALID_JSON_DATA

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

    if len(users.search("username", username, strict=True)) > 0:
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

    return len(c for c in username if c not in USERNAME_ALLOWED_CHARS) == 0


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


def set_admin(id: str, value: bool = True) -> dict:
    """Sets `admin` attribute of an user to given value.

    Args:
        id (`str`): Unique user ID to operate over.
        value (`bool`, `optional`): New `admin` attribute value. Defaults to True.

    Returns:
        dict: Repsonse.
    """

    user = users.find(id)
    if not user:
        return {
            "status": STATUS_NOT_FOUND_DOCUMENT,
            "response": None
        }
    if user["_id"] == get_user_id_by_ip(request.remote_addr):
        return {
            "status": STATUS_INVALID_JSON_DATA,
            "response": None
        }

    user["admin"] = value
    users.update(id, user)

    return {
        "status": STATUS_SUCCESS,
        "response": None
    }


def authenticate(username: str, password: str) -> str | None:
    """Authenticates user.

    Args:
        username (`str`): Username
        password (`str`): Password

    Returns:
        `str` | `None`: Authenticated unique user ID, `None`
        if not authenticated.
    """
    print("username:",username)
    users_ = users.search("username", username, strict=True)
    print(users_)

    if users_ and users_[0]["password"] == password:
        return users_[0]["_id"]
    else:
        return None


def login(_id: str) -> None:
    """Logs in current request's IP address.

    Args:
        _id (`str`): User unique ID to log in.
    """

    logged_ips[request.environ.get('HTTP_X_REAL_IP', request.remote_addr)] = {
        "lastrequest": 0,
        "user": _id,
        "logged": True
    }


def get_void_response(status_code: int) -> dict:
    """Generates void response.

    Args:
        status_code (`int`): Status code.

    Returns:
        `dict`: Response.
    """

    return {
        "status": status_code,
        "response": None
    }


logged_ips = {}

server = Flask(__name__)
server.config["MONGO_URI"] = MONGO_URI
server.config["CUSTOM_ATTR_DB_NAME"] = DATABASE_NAME
CORS(server)

scheduler = APScheduler()
scheduler.add_job(id="timeout", func=timeout_check,
    trigger="interval", seconds=TIMEOUT_CHECK)

users = Collection(server, "users")
clients = Collection(server, "clients")
bills = Collection(server, "bills")
files = FileCollection(server)


@server.before_request
def before_req() -> None | dict:
    """Runs before any request. Used for allowing/denying access
    to the requested route.

    Returns:
        `None` | `dict`: `None` if access allowed, `dict` as server response otherwise.
    """

    if route_is_private(request.path) and not logged(request.remote_addr):
        return get_void_response(STATUS_ACCESS_DENIED)

    if route_is_only_admin(request.path) and not is_admin(get_user_id_by_ip(request.remote_addr)):
        return get_void_response(STATUS_ACCESS_DENIED)


@server.after_request
def after_req(res) -> str:
    """Called after any request. Used for processing server response
    before sending it to the client.

    Args:
        res (`~server.response_class`): Preliminary server response.

    Returns:
        `str`: Final response (JSON formatted).
    """

    def update_log():
        try:
            logged_ips[request.environ.get(
                'HTTP_X_REAL_IP', request.remote_addr)]["lastrequest"] = time()
        except KeyError:
            logged_ips[request.environ.get('HTTP_X_REAL_IP', request.remote_addr)] = {
                "lastrequest": time(),
                "user": None,
                "logged": False
            }

    if has_restrict_access():
        current_user = get_user_id_by_ip(
            request.environ.get('HTTP_X_REAL_IP', request.remote_addr))
        response = res.get_json()
        if type(response["response"]) is list:
            response["response"] = list(
                doc for doc in response["response"] if doc["user"] == current_user)
        else:
            if response["response"]["user"] != current_user:
                return get_void_response(STATUS_ACCESS_DENIED)
        res.data = dumps(response)

    update_log()

    return res


@server.route("/hashsalt")
def get_hash_salt() -> str:
    """Gets hashsalt constant.

    Returns:
        `str`: Hashsalt.
    """

    return HASH_SALT


@server.route("/log", methods=["POST"])
def process_login() -> dict:
    """Process login request.

    Returns:
        `dict`: Response
    """

    if not valid_doc_datatype(request.json, TEMPLATE_LOGIN):
        print(1)
        return get_void_response(STATUS_INVALID_JSON_DATA)

    auth = authenticate(request.json["username"], request.json["password"])

    if auth:
        return {
            "status": STATUS_SUCCESS,
            "response": login(auth)
        }

    else:
        print(2)
        return get_void_response(STATUS_ACCESS_DENIED)


@server.route("/log", methods=["DELETE"])
def logout() -> dict:
    """Logs out request's IP address.

    Returns:
        `dict`: Response
    """
    try:
        del logged_ips[request.environ.get(
            'HTTP_X_REAL_IP', request.remote_addr)]
        return get_void_response(STATUS_SUCCESS)

    except KeyError:
        return get_void_response(STATUS_POINTLESS_REQUEST)


@server.route("/log")
def process_logged() -> dict:
    """Retrieves request's IP address logged user's basic data.

    Returns:
        `dict`: Response
    """

    if logged(request.remote_addr):

        user = users.find(get_user_id_by_ip(request.remote_addr))

        return {
            "status": STATUS_SUCCESS,
            "response": {
                "user": user["_id"],
                "username": user["username"],
                "admin": is_admin(get_user_id_by_ip(request.remote_addr))
            }
        }
    else:
        return get_void_response(STATUS_ACCESS_DENIED)


@server.route("/clients", methods=["GET"])
def get_clients() -> dict:
    """Retrieves the whole clients collection.

    Returns:
        `dict`: Response
    """
    return {
        "status": STATUS_SUCCESS,
        "response": clients.get()
    }


@server.route("/clients/<cl_id>", methods=["GET"])
def search_clients(cl_id: str = None) -> dict:
    """Searchs over the `clients.client.id` value.

    Args:
        id (`str`): ID to search for.

    Returns:
        `dict`: Response
    """
    if cl_id:
        return {
            "status": STATUS_SUCCESS,
            "response": clients.search("id", cl_id)
        }
    else:
        return get_void_response(STATUS_POINTLESS_REQUEST)


@server.route("/client/<_id>", methods=["GET"])
def get_client(_id: str = None) -> dict:
    """Finds and retrieve a client's data.

    Args:
        _id (`str`): Unique client ID

    Returns:
        `dict`: Response
    """

    if _id:
        res = clients.find(_id)
        if res != None:
            return {
                "status": STATUS_SUCCESS,
                "response": res
            }
        else:
            return get_void_response(STATUS_NOT_FOUND_DOCUMENT)
    else:
        return get_void_response(STATUS_POINTLESS_REQUEST)


@server.route("/client", methods=["POST"])
def create_client() -> dict:
    """Inserts a client into the clients collection.

    Returns:
        `dict`: Response
    """

    if not valid_doc_datatype(request.json, TEMPLATE_INSERT_CLIENT):
        return get_void_response(STATUS_INVALID_JSON_DATA)

    res = clients.insert({
        "id": request.json["id"],
        "user": get_user_id_by_ip(request.environ.get('HTTP_X_REAL_IP', request.remote_addr)),
        "name": request.json["name"],
        "phone": request.json["phone"],
        "email": request.json["email"],
        "address": request.json["address"],
        "bills": []
    })
    return {
        "status": STATUS_SUCCESS,
        "response": str(res[0])
    }


@server.route("/client/<_id>", methods=["DELETE"])
def delete_client(_id: str = None) -> dict:
    """Deletes a client from the clients collection.

    Args:
        _id (`str`): Unique client ID.

    Returns:
        `dict`: Response
    """

    if _id:
        clients.delete(_id)
        return get_void_response(STATUS_SUCCESS)
    else:
        return get_void_response(STATUS_POINTLESS_REQUEST)


@server.route("/updateclient/<_id>", methods=["POST"])
def updateClient(_id: str = None) -> dict:
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
            return get_void_response(STATUS_SUCCESS)
        else:
            return get_void_response(STATUS_NOT_FOUND_DOCUMENT)
    else:
        return get_void_response(STATUS_POINTLESS_REQUEST)


@server.route("/file/<filename>")
def get_file(filename):
    """Retrieves a file from the database.

    Args:
        filename (`str`): filename to search for.

    Returns:
        `~flask.Flask.response_class`: Response streaming the file bytes.
    """

    return files.get(filename)


@server.route("/file", methods=["POST"])
def save_file() -> dict:
    """Saves a file into the database.

    Returns:
        `dict`: Response
    """
    files.save(request.files["File"])
    return get_void_response(STATUS_SUCCESS)


@server.route("/bill", methods=["POST"])
def add_bill():
    """Inserts a bill into the bills collection.

    Returns:
        `dict`: Response
    """

    if not valid_doc_datatype(request.json, TEMPLATE_INSERT_BILL):
        return get_void_response(STATUS_INVALID_JSON_DATA)

    for b in bills.get():
        if b["ref"] == request.json["ref"]:
            return get_void_response(STATUS_INVALID_JSON_DATA)

    client_id = request.json["client"]
    res = bills.insert({
        "ref": request.json["ref"],
        "user": get_user_id_by_ip(request.environ.get('HTTP_X_REAL_IP', request.remote_addr)),
        "date": request.json["date"],
        "type": request.json["type"],
        "description": request.json["description"],
        "file": request.json["file"],
        "client": client_id
    })
    if client_id:
        cl = clients.find(client_id)
        cl["bills"].append(res[0])
        clients.update(client_id, cl)

    return {
        "status": STATUS_SUCCESS,
        "response": res[0]
    }


@server.route("/bills")
def get_bills() -> dict:
    """Retrieves te whole `bills` collection.

    Returns:
        `dict`: Response
    """

    return {
        "status": STATUS_SUCCESS,
        "response": bills.get()
    }


@server.route("/bills/<ref>")
def search_bills(ref: str = None) -> dict:
    """Searchs over the `bills.bill.ref` value.

    Args:
        ref (`str`): Bill's `ref` to search for.

    Returns:
        `dict`: Response
    """

    if ref:
        return {
            "status": STATUS_SUCCESS,
            "response": bills.search("ref", ref)
        }
    else:
        return get_void_response(STATUS_POINTLESS_REQUEST)


@server.route("/bill/<id>", methods=["DELETE"])
def delete_bill(id: str = None) -> dict:
    """Deletes a bill from the `bills` collection.

    Args:
        id (`str`): Bill's unique ID.

    Returns:
        `dict`: Response
    """

    if not id:
        return get_void_response(STATUS_POINTLESS_REQUEST)

    doc = bills.find(id)

    if not doc:
        return get_void_response(STATUS_NOT_FOUND_DOCUMENT)

    files.delete_by_filename(doc["file"])
    bills.delete(id)

    return get_void_response(STATUS_SUCCESS)


@server.route("/admin/users")
def get_users() -> dict:
    """Retrieves the whole `users` collection. 

    Returns:
        dict: Response
    """

    return {
        "status": STATUS_SUCCESS,
        "response": users.get()
    }


@server.route("/admin/users", methods=["POST"])
def create_user() -> dict:
    """Inserts an user into the `users` collection.

    Returns:
        `dict`: Response
    """

    code = valid_new_user(request.json)

    if code != STATUS_SUCCESS:
        return get_void_response(code)
    res = users.insert({
        "username": request.json["username"],
        "password": request.json["password"],
        "admin": request.json["admin"]
    })
    if len(res) == 0:
        return get_void_response(STATUS_INVALID_JSON_DATA)

    return {
        "status": STATUS_SUCCESS,
        "response": res[0]
    }


@server.route("/admin/resetpassword", methods=["POST"])
def change_password() -> dict:
    """Updates an user's password.

    Returns:
        `dict`: Response
    """

    if not (valid_doc_datatype(request.json, TEMPLATE_CHANGE_PASSWORD)) and (valid_password(request.json["password"])):
        return get_void_response(STATUS_INVALID_JSON_DATA)

    docs = users.search("username", request.json["username"], strict=True)
    if len(docs) == 0:
        return get_void_response(STATUS_NOT_FOUND_DOCUMENT)

    new_doc = docs[0]
    _id = new_doc["_id"]
    new_doc["password"] = request.json["password"]
    users.update(_id, new_doc)
    return get_void_response(STATUS_SUCCESS)


@server.route("/admin/changepassword", methods=["POST"])
def change_self_password() -> dict:
    """Changes the current request IP address logged
    user's password.

    Returns:
        `dict`: Response
    """

    user = users.find(get_user_id_by_ip(request.remote_addr))

    if request.json["current"] != user["password"]:
        return get_void_response(STATUS_ACCESS_DENIED)

    if not valid_password(request.json["new"]):
        return get_void_response(STATUS_INVALID_JSON_DATA)

    user["password"] = request.json["new"]
    users.update(user["_id"], user)

    return get_void_response(STATUS_SUCCESS)


@server.route("/admin/addadmin/<_id>")
def add_admin(_id: str = None) -> dict:
    """Sets to true the `users.user.admin` value.

    Args:
        _id (`str`): User unique ID.

    Returns:
        `dict`: Response
    """

    if not _id:
        return get_void_response(STATUS_POINTLESS_REQUEST)

    return set_admin(_id)


@server.route("/admin/removeadmin/<_id>")
def remove_admin(_id: str = None) -> dict:
    """Sets to `False` the `users.user.admin` value.

    Args:
        _id (`str`): User unique ID

    Returns:
        `dict`: Response
    """

    if not _id:
        return get_void_response(STATUS_POINTLESS_REQUEST)

    return set_admin(id, False)


@server.route("/test")
def test():
    return "done"


def test_add_clients(n: int):
    names = ["Aarón",
             "Abdón", "Abel", "Abelardo", "Abrahán", "Absalón", "Acacio", "Adalberto", "Adán", "Adela", "Adelaida", "Adolfo", "Adón", "Adrián", "Agustín", "Aitor", "Alba", "Albert", "Alberto", "Albina", "Alejandra", "Alejandro", "Alejo", "Alfonso", "Alfredo", "Alicia", "Alipio", "Almudena", "Alonso", "Álvaro", "Amadeo", "Amaro", "Ambrosio", "Amelia", "Amparo", "Ana", "Ananías", "Anastasia", "Anatolio", "Andrea", "Andrés", "Ángel", "Ángela", "Ángeles", "Aniano", "Anna", "Anselmo", "Antero", "Antonia", "Antonio", "Aquiles", "Araceli", "Aránzazu", "Arcadio", "Aresio", "Ariadna", "Aristides", "Arnaldo", "Artemio", "Arturo", "Ascensión", "Asunción", "Atanasio", "Augusto", "Áurea", "Aurelia", "Aureliano", "Aurelio", "Aurora", "Baldomero", "Balduino", "Baltasar", "Bárbara", "Bartolomé", "Basileo", "Beatriz", "Begoña", "Belén", "Beltrán", "Benedicto", "Benigno", "Benito", "Benjamín", "Bernabé", "Bernarda", "Bernardo", "Blanca", "Blas", "Bonifacio", "Borja", "Bruno", "Calixto", "Camilo", "Cándida", "Carina", "Carlos", "Carmelo", "Carmen", "Carolina", "Casiano", "Casimiro", "Casio", "Catalina", "Cayetano", "Cayo", "Cecilia", "Ceferino", "Celia", "Celina", "Celso", "César", "Cesáreo", "Cipriano", "Cirilo", "Cirino", "Ciro", "Clara", "Claudia", "Claudio", "Cleofás", "Clotilde", "Colombo", "Columba", "Columbano", "Concepción", "Conrado", "Constancio", "Constantino", "Consuelo", "Cosme", "Cristian", "Cristina", "Cristóbal", "Daciano", "Dacio", "Dámaso", "Damián", "Daniel", "Dario", "David", "Demócrito", "Diego", "Dimas", "Dolores", "Domingo", "Donato", "Dorotea", "Edgar", "Edmundo", "Eduardo", "Eduvigis", "Efrén", "Elena", "Elías", "Elisa", "Eliseo", "Elvira", "Emilia", "Emiliano", "Emilio", "Encarnación", "Enrique", "Epifanía", "Erico", "Ernesto", "Esdras", "Esiquio", "Esperanza", "Esteban", "Ester", "Esther", "Eugenia", "Eugenio", "Eulalia", "Eusebio", "Eva", "Evaristo", "Ezequiel", "Fabián", "Fabio", "Fabiola", "Facundo", "Fátima", "Faustino", "Fausto", "Federico", "Feliciano", "Felipe", "Félix", "Fermín", "Fernando", "Fidel", "Fortunato", "Francesc", "Francisca", "Francisco", "Fulgencio", "Gabriel", "Gema", "Genoveva", "Gerardo", "Germán", "Gertrudis", "Gisela", "Gloria", "Godofredo", "Gonzalo", "Gregorio", "Guadalupe", "Guido", "Guillermo", "Gustavo", "Guzmán", "Héctor", "Heliodoro", "Heraclio", "Heriberto", "Hilarión", "Hildegarda", "Homero", "Honorato", "Honorio", "Hugo",
             "Humberto", "Ifigenia", "Ignacio", "Ildefonso", "Inés", "Inmaculada", "Inocencio", "Irene", "Ireneo", "Isaac", "Isabel", "Isaías", "Isidro", "Ismael", "Iván", "Jacinto", "Jacob", "Jacobo", "Jaime", "Jaume", "Javier", "Jeremías", "Jerónimo", "Jesús", "Joan", "Joaquím", "Joaquín", "Joel", "Jonás", "Jonathan", "Jordi", "Jorge", "Josafat", "José", "Josefa", "Josefina", "Josep", "Josué", "Juan", "Juana", "Julia", "Julián", "Julio", "Justino", "Juvenal", "Ladislao", "Laura", "Laureano", "Lázaro", "Leandro", "Leocadia", "León", "Leonardo", "Leoncio", "Leonor", "Leopoldo", "Lidia", "Liduvina", "Lino", "Lorena", "Lorenzo", "Lourdes", "Lucano", "Lucas", "Lucía", "Luciano", "Lucrecia", "Luis", "Luisa", "Luz", "Macario", "Magdalena", "Manuel", "Manuela", "Mar", "Marc", "Marcelino", "Marcelo", "Marcial", "Marciano", "Marcos", "Margarita", "María", "Mariano", "Marina", "Mario", "Marta", "Martín", "Mateo", "Matías", "Matilde", "Mauricio", "Maximiliano", "Melchor", "Mercedes", "Miguel", "Milagros", "Miqueas", "Míriam", "Mohamed", "Moisés", "Mónica", "Montserrat", "Narciso", "Natalia", "Natividad", "Nazario", "Nemesio", "Nicanor", "Nicodemo", "Nicolás", "Nicomedes", "Nieves", "Noé", "Noelia", "Norberto", "Nuria", "Octavio", "Odón", "Olga", "Onésimo", "Orestes", "Oriol", "Oscar", "Óscar", "Oseas", "Oswaldo", "Otilia", "Oto", "Pablo", "Pancracio", "Pascual", "Patricia", "Patricio", "Paula", "Pedro", "Petronila", "Pilar", "Pío", "Poncio", "Porfirio", "Primo", "Priscila", "Probo", "Purificación", "Rafael", "Raimundo", "Ramiro", "Ramón", "Raquel", "Raúl", "Rebeca", "Reinaldo", "Remedios", "Renato", "Ricardo", "Rigoberto", "Rita", "Roberto", "Rocío", "Rodrigo", "Rogelio", "Román", "Romualdo", "Roque", "Rosa", "Rosalia", "Rosario", "Rosendo", "Rubén", "Rufo", "Ruperto", "Salomé", "Salomón", "Salvador", "Salvio", "Samuel", "Sandra", "Sansón", "Santiago", "Sara", "Sebastián", "Segismundo", "Sergio", "Severino", "Silvia", "Simeón", "Simón", "Siro", "Sixto", "Sofía", "Soledad", "Sonia", "Susana", "Tadeo", "Tarsicio", "Teodora", "Teodosia", "Teófanes", "Teófila", "Teresa", "Timoteo", "Tito", "Tobías", "Tomas", "Tomás", "Toribio", "Trinidad", "Ubaldo", "Urbano", "Úrsula", "Valentín", "Valeriano", "Vanesa", "Velerio", "Venancio", "Verónica", "Vicenta", "Vicente", "Víctor", "Victoria", "Victorino", "Victorio", "Vidal", "Virgilio", "Virginia", "Vladimiro", "Wilfredo", "Xavier", "Yolanda", "Zacarías", "Zaqueo"]

    docs = []

    from random import randint

    for i in range(n):
        doc = {}
        name = names[randint(0, 400)]
        doc["id"] = str(i)
        doc["name"] = name
        doc["user"] = "633d7afbc78557eed1fa40ea"
        doc["email"] = f"{name}@mail.com"
        doc["phone"] = "000000"
        doc["address"] = "Calle XX"
        doc["bills"] = []
        docs.append(doc)

    clients.insert(*docs)


if __name__ == "__main__":
    scheduler.start()
    server.run(port=PORT)