"""
Rate limiting using slowapi.
Limits are per IP address.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

# 60 requests per minute per IP — generous for a mobile app
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["60/minute"],
)