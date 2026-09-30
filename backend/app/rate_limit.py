from slowapi import Limiter
from slowapi.util import get_remote_address

# Keyed by client IP. Individual routes opt into a limit with
# @limiter.limit("N/period") — nothing is rate-limited by default, it's
# explicit per endpoint (see routers/admin_auth.py for login).
limiter = Limiter(key_func=get_remote_address)
