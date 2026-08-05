"""Per-profile authentication, identical philosophy to erpnext-bridge:
every Hermes profile calls this bridge with a bearer token equal to its
own shared_secret. There is no master token and no way for a profile to
borrow another profile's identity.
"""

from fastapi import Header, HTTPException

from .config import ProfileConfig, settings


def resolve_profile(authorization: str = Header(default="")) -> ProfileConfig:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    token = authorization.removeprefix("Bearer ").strip()
    for profile in settings.profiles.values():
        if _constant_time_eq(token, profile.shared_secret):
            return profile
    raise HTTPException(status_code=401, detail="Unknown or invalid profile token")


def _constant_time_eq(a: str, b: str) -> bool:
    if len(a) != len(b):
        return False
    result = 0
    for x, y in zip(a, b):
        result |= ord(x) ^ ord(y)
    return result == 0
