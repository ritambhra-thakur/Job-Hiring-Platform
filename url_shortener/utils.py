import secrets
from random import choice
from string import ascii_letters, digits

SIZE = 8

AVAIABLE_CHARS = ascii_letters + digits


def short_url(chars=AVAIABLE_CHARS):
    return "".join([secrets.choice(chars) for _ in range(SIZE)])
