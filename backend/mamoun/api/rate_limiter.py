"""
M-5: Shared rate limiter instance for the Mamoun API.
Import this module instead of referencing mamoun.main to avoid circular imports.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
