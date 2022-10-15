from dataclasses import dataclass
from flask_login import UserMixin

@dataclass
class User(UserMixin):
    _id : str
    username: str
    password: str
    role: str

    def get_id(self):
        return self._id

    @staticmethod
    def get_template():
        return {
            "_id": str,
            "username": str,
            "password": str,
            "admin": str
        }