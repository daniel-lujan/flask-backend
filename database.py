from mongo_collection import *

def init_database(server):
    
    global users, clients, bills, files

    users = Collection(server, "users")
    clients = Collection(server, "clients")
    bills = Collection(server, "bills")
    files = FileCollection(server)

users = None
clients = None
bills = None
files = None

