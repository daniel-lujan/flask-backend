from flask_pymongo import PyMongo, ObjectId


class FileCollection():

    def __init__(self, flask_server):
        self.__mongo_conn = PyMongo(flask_server)

    def save(self, file) -> None:
        """Saves a file into the database.

        Args:
            file (`~werkzeug.datastructures.FileStorage`): File to be saved.
        """

        self.__mongo_conn.save_file(file.filename, file, md5="")

    def get(self, filename: str):
        """Gets a file from the database.

        Args:
            filename (`str`): filename to search for.

        Returns:
            `~flask.Flask.response_class`: Response streaming the file bytes.
        """

        return self.__mongo_conn.send_file(filename)

    def __delete_chunks(self, files_id: str):
        """Deletes all the binary data chunks linked to
        a file from the `fs.chunks` collection.

        Args:
            files_id (`str`): File ID of which chunks are set to be deleted.
        """

        self.__mongo_conn.db["fs.chunks"].delete_many(
            {"files_id": ObjectId(files_id)})

    def delete_by_filename(self, filename: str):
        """Deletes a file from the database.

        Args:
            filename (`str`): Name of file to be deleted.
        """

        files = self.__mongo_conn.db["fs.files"].find({"filename": filename})
        for doc in files:
            self.__delete_chunks(doc["_id"])
            self.__mongo_conn.db["fs.files"].delete_one(
                {"_id": ObjectId(doc["_id"])})

    def delete_by_id(self, id: str):
        """Deletes a file from the database.

        Args:
            id (`str`): ID of file to be deleted.
        """

        self.__delete_chunks(id)
        self.__mongo_conn.db["fs.files"].delete_one({"_id": ObjectId(id)})

    def file_exists(self, filename: str) -> bool:
        """Checks whether a file exists in
        the database.

        Args:
            filename (`str`): File name to search for.

        Returns:
            `bool`: `True` if it exists, `False` otherwise.
        """

        found = self.__mongo_conn.db["fs.files"].find_one({"filename":filename})

        return True if found is not None else False 

class Collection():

    def __init__(self, flask_server, name: str):
        """Direct connection to a MongoDB Collection.
        Uses `MONGO_URI` config value to
        access the database to the specified `name`
        collection. Creates the collection if it does
        not exist yet.

        Args:
            flask_server (`~flask.Flask`): Flask app
            name (str): Collection name.
        """

        self.__mongo_coll = PyMongo(flask_server).db[name]

    def get(self) -> list[dict]:
        """Gets all documents stored in the collection.

        Returns:
            `list[dict]`: List of documents.
        """

        list_ = []

        for doc in self.__mongo_coll.find():
            doc["_id"] = str(doc["_id"])
            list_.append(doc)

        return list_

    def insert(self, *args: dict) -> list:
        """Inserts documents into the collection.

        *Args:
            `dict`: Document to be inserted.

        Returns:
            `list`: Inserted IDs
        """

        return list(str(id) for id in (self.__mongo_coll.insert_many(args).inserted_ids))

    def find(self, id: str) -> dict | None:
        """Finds a document.

        Args:
            id (`str`): Document ID to be found.

        Returns:
            `dict | None`: Found document.
        """

        try:
            doc = self.__mongo_coll.find_one({"_id": ObjectId(id)})
            doc["_id"] = str(doc["_id"])
        except (TypeError, KeyError):
            doc = None

        return doc

    def search(self, key: str, value: str, strict: bool = False) -> list[dict]:
        """Searchs throughout the collection.

        Args:
            key (`str`): Key to evaluate.
            value (`str`): Value of key to search for.
            strict (`bool, optional`): If True, found and given value
            shall be exactly the same, otherwise it will include documents
            in which found value cointains the given one. Defaults to ``False``.

        Returns:
            `list[dict]`: Found documents.
        """

        if strict:
            return list(x for x in self.get() if x[key] == value)
        else:
            return list(x for x in self.get() if x[key].find(value) != -1)

    def search_one(self, key: str, value: str) -> dict | None:
        return self.__mongo_coll.find_one({key:value})

    def delete(self, id: str) -> bool:
        """Deletes a document from the collection.

        Args:
            id (`str`): ID of document to be deleted.

        Returns:
            `bool`: `True` if the document was deleted, ``False`` otherwise.
        """

        if self.__mongo_coll.delete_one({"_id": ObjectId(id)}).deleted_count > 0:
            return True
        else:
            return False

    def update(self, id: str, info: dict):
        """Updates a document.

        Args:
            id (`str`): ID of document to be updated
            info (`dict`): Document to replace with
        """

        try:
            del info["_id"]
        except KeyError:
            pass
        
        self.__mongo_coll.replace_one({"_id": ObjectId(id)}, info)
