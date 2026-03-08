import bcrypt
from sqlalchemy import Column, Integer, String

from src.core.database import BaseModel


class Authentication(BaseModel):
    __tablename__ = "authentications"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)
    _password = Column(String(255))

    def set_password(self, password: str) -> None:
        self._password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def check_password(self, password: str) -> bool:
        return bcrypt.checkpw(password.encode(), self._password.encode())

    @property
    def password(self) -> str:
        raise AttributeError("password is not a readable attribute")

    @password.setter
    def password(self, password: str) -> None:
        self.set_password(password)
