"""Per-profile authentication for the bridge itself.

Every Hermes profile calls the bridge with a bearer token equal to its own
`shared_secret` (mục 9.5: request must always resolve to one user). The
bridge looks up which profile that secret belongs to and uses *that*
profile's ERPNext API key/secret for the downstream call — a profile can
never borrow another profile's ERPNext identity, even if it tried to pass
one in.
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
