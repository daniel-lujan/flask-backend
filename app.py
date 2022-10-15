from json import dumps
from datetime import timedelta

from flask import Flask, request, session
from flask_cors import CORS
from flask_login import login_required, current_user

from constants import *
import database
from auth import authentication, init_login_manager, role_required, valid_json_template
from static import valid_doc_datatype, response


def has_restrict_access() -> bool:
    """Checks whether a response to the current request has to be
    restricted e.g. prevent non-admin users from taking other user's data.

    Returns:
        `bool`: `True` if it has restricted access, `False` otherwise.
    """

    for route in USER_RESTRICTED_ROUTES:
        if request.path.split("/")[1] == route:
            return current_user._id and (current_user.role != "admin") and request.method == "GET"


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
    """Sets `admin` attribute of an user to given value.

    Args:
        id (`str`): Unique user ID to operate over.
        value (`bool`, `optional`): New `admin` attribute
        value. Defaults to True.

    Returns:
        dict: Repsonse.
    """

    user = users.find(_id)
    if not user:
        return {
            "status": STATUS_NOT_FOUND_DOCUMENT,
            "response": None
        }
    if user["_id"] == current_user._id:
        return {
            "status": STATUS_INVALID_JSON_DATA,
            "response": None
        }

    user["role"] = "admin" if value else "normal"
    users.update(_id, user)

    return {
        "status": STATUS_SUCCESS,
        "response": None
    }

server = Flask(__name__)

server.register_blueprint(authentication)

server.config["MONGO_URI"] = DATABASE_URI
server.config['SECRET_KEY'] = SECRET_KEY
CORS(server, supports_credentials=True)

database.init_database(server)

users = database.users
clients = database.clients
bills = database.bills
files = database.files

init_login_manager(server)


@server.before_request
def before_req():
    session.permanent = True
    server.permanent_session_lifetime = timedelta(minutes=LOG_TIMEOUT)
    session.modified = True

@server.after_request
def after_req(res) -> str:
    """Called after any request. Used for processing server response
    before sending it to the client.

    Args:
        res (`~server.response_class`): Preliminary server response.

    Returns:
        `str`: Final response (JSON formatted).
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
    return {
        "status": STATUS_SUCCESS,
        "response": clients.get()
    }


@server.route("/clients/<cl_id>", methods=["GET"])
@login_required
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
        return response(STATUS_POINTLESS_REQUEST)


@server.route("/client/<_id>", methods=["GET"])
@login_required
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
            return response(STATUS_NOT_FOUND_DOCUMENT)
    else:
        return response(STATUS_POINTLESS_REQUEST)


@server.route("/client", methods=["POST"])
@login_required
def create_client() -> dict:
    """Inserts a client into the clients collection.

    Returns:
        `dict`: Response
    """

    if not valid_doc_datatype(request.json, TEMPLATE_INSERT_CLIENT):
        return response(STATUS_INVALID_JSON_DATA)

    res = clients.insert({
        "id": request.json["id"],
        "user": current_user._id,
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
            return response(STATUS_NOT_FOUND_DOCUMENT)
    else:
        return response(STATUS_POINTLESS_REQUEST)


@server.route("/file/<filename>")
@login_required
def get_file(filename):
    """Retrieves a file from the database.

    Args:
        filename (`str`): filename to search for.

    Returns:
        `~flask.Flask.response_class`: Response streaming the file bytes.
    """

    return files.get(filename)


@server.route("/file", methods=["POST"])
@login_required
def save_file() -> dict:
    """Saves a file into the database.

    Returns:
        `dict`: Response
    """
    files.save(request.files["File"])
    return response(STATUS_SUCCESS)


@server.route("/bill", methods=["POST"])
@login_required
def add_bill():
    """Inserts a bill into the bills collection.

    Returns:
        `dict`: Response
    """

    if not valid_doc_datatype(request.json, TEMPLATE_INSERT_BILL):
        return response(STATUS_INVALID_JSON_DATA)

    for b in bills.get():
        if b["ref"] == request.json["ref"]:
            return response(STATUS_INVALID_JSON_DATA)

    client_id = request.json["client"]
    res = bills.insert({
        "ref": request.json["ref"],
        "user": current_user._id,
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
@login_required
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
@login_required
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
        return response(STATUS_POINTLESS_REQUEST)


@server.route("/bill/<id>", methods=["DELETE"])
@login_required
def delete_bill(id: str = None) -> dict:
    """Deletes a bill from the `bills` collection.

    Args:
        id (`str`): Bill's unique ID.

    Returns:
        `dict`: Response
    """

    if not id:
        return response(STATUS_POINTLESS_REQUEST)

    doc = bills.find(id)

    if not doc:
        return response(STATUS_NOT_FOUND_DOCUMENT)

    files.delete_by_filename(doc["file"])
    bills.delete(id)

    return response(STATUS_SUCCESS)


@server.route("/admin/users")
@role_required("admin")
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

    return {
        "status": STATUS_SUCCESS,
        "response": res[0]
    }


@server.route("/admin/resetpassword", methods=["POST"])
@role_required("admin")
def change_password() -> dict:
    """Updates an user's password.

    Returns:
        `dict`: Response
    """

    if not (valid_doc_datatype(request.json, TEMPLATE_CHANGE_PASSWORD)) and (valid_password(request.json["password"])):
        return response(STATUS_INVALID_JSON_DATA)

    docs = users.search("username", request.json["username"], strict=True)
    if len(docs) == 0:
        return response(STATUS_NOT_FOUND_DOCUMENT)

    new_doc = docs[0]
    _id = new_doc["_id"]
    new_doc["password"] = request.json["password"]
    users.update(_id, new_doc)
    return response(STATUS_SUCCESS)


@server.route("/admin/changepassword", methods=["POST"])
@role_required("admin")
def change_self_password() -> dict:
    """Changes the current request IP address logged
    user's password.

    Returns:
        `dict`: Response
    """

    user = users.find(current_user._id)

    if request.json["current"] != user["password"]:
        return response(STATUS_ACCESS_DENIED)

    if not valid_password(request.json["new"]):
        return response(STATUS_INVALID_JSON_DATA)

    user["password"] = request.json["new"]
    users.update(user["_id"], user)

    return response(STATUS_SUCCESS)


@server.route("/admin/addadmin/<_id>")
@role_required("admin")
def add_admin(_id: str = None) -> dict:
    """Sets to true the `users.user.admin` value.

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
    """Sets to `False` the `users.user.admin` value.

    Args:
        _id (`str`): User unique ID

    Returns:
        `dict`: Response
    """

    if not _id:
        return response(STATUS_POINTLESS_REQUEST)

    return set_admin(_id, False)


@server.route("/test")
@login_required
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
    server.run(debug=True,port=PORT)