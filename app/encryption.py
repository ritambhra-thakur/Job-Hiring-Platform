from cryptography.fernet import Fernet
from django.conf import settings
from hashids import Hashids


def encrypt(message):
    key = settings.ENCRY_KEY
    cypher = Hashids(salt=key, min_length=8)
    return cypher.encode(message)


def decrypt(message):
    key = settings.ENCRY_KEY
    cypher = Hashids(salt=key, min_length=8)
    return cypher.decode(message)[0]
