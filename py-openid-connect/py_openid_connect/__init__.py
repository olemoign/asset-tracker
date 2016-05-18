from random import SystemRandom
from string import ascii_lowercase, ascii_uppercase, digits


def session_id(length=24, chars=ascii_lowercase + ascii_uppercase + digits):
    return ''.join(SystemRandom().choice(chars) for _ in range(length))
