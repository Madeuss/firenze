"""Who may start a match, and who may touch one that exists. (T-11, T-12)

The threat model called both of these blockers for publishing, and the reason
is money before it is privacy: every turn spends a real model call on somebody
else's key, and the review route hands over the accounting of a whole match.

Two different questions, answered by two different secrets:

**May you start a match at all?** A single shared key, held by whoever is meant
to play. It is the whole of the "account system", and deliberately so — a game
with no login collects no personal data, which is what keeps LGPD out of scope
(docs/00-plano-de-projeto.md §8). Handing a friend a key is an invitation, and
rotating it withdraws every invitation at once.

**May you touch *this* match?** A capability token minted when the match is
created, returned exactly once, and never stored in the clear: the database
keeps a SHA-256 of it, so a dump of the table does not hand over anybody's
game. Whoever holds the token is the owner. There is no account to attach it
to, and none is needed.

## Why an empty key means open

Local development and the test suite run with no key at all, and enforcement
switches off with it — otherwise every test would carry ceremony that proves
nothing about the game. That is a footgun in exactly one direction, so it is
nailed shut at the other end: a process that says it is `prod` refuses to start
without a key. You cannot deploy this open by forgetting something.
"""

import hashlib
import secrets
import time
from collections import deque

from fastapi import Header, HTTPException, Request, status

from firenze.config import settings

TOKEN_HEADER = "X-Firenze-Token"
KEY_HEADER = "X-Firenze-Key"


class Unprotected(RuntimeError):
    """A production process with no access key. Refuses to start. (T-12)"""


def guarded() -> bool:
    """Whether this deployment checks anything at all."""
    return bool(settings.access_key.get_secret_value())


def check_configuration() -> None:
    """Called at startup. Fails loudly rather than serving an open door."""
    if settings.environment == "prod" and not guarded():
        raise Unprotected(
            "FIRENZE_ENVIRONMENT=prod with no FIRENZE_ACCESS_KEY: "
            "every turn would spend the model key of whoever deployed this"
        )


def mint() -> tuple[str, str]:
    """A new owner token and the hash to store. The token is never stored."""
    token = secrets.token_urlsafe(32)
    return token, fingerprint(token)


def fingerprint(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def require_key(key: str | None = Header(None, alias=KEY_HEADER)) -> None:
    """The invitation. Guards the one route that creates spend out of nothing."""
    if not guarded():
        return
    expected = settings.access_key.get_secret_value()
    if key is None or not secrets.compare_digest(key, expected):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            f"this deployment needs an access key in {KEY_HEADER}",
        )


def require_owner(stored: str | None, presented: str | None) -> None:
    """The capability. Every route that takes a `match_id` goes through here.

    A match with no stored hash predates ownership. It stays reachable on an
    open deployment, where nothing was ever protected anyway, and is
    unreachable on a guarded one — refusing is the only answer that cannot be
    wrong about who it belongs to.
    """
    if not guarded():
        return
    if stored is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "this match has no owner")
    if presented is None or not secrets.compare_digest(fingerprint(presented), stored):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"this match belongs to somebody else; its token goes in {TOKEN_HEADER}",
        )


class Bucket:
    """Requests per window, per caller. In memory, on purpose.

    Phase 1 is one uvicorn process on one VM (docs/00-plano-de-projeto.md §8),
    and for that a dict of deques is the whole answer: no Redis round trip on
    the hot path, no second thing to be down. It buys exactly what its shape
    suggests — the count resets when the process does, and two workers would
    each keep their own. When either becomes true, this moves to Redis, which
    is already in the compose file and has no other use yet.

    It is not the thing standing between a stranger and the model key. That is
    the access key. This bounds what one invited player can spend in a minute.
    """

    def __init__(self, per_minute: int, window: float = 60.0) -> None:
        self._limit = per_minute
        self._window = window
        self._seen: dict[str, deque[float]] = {}

    def check(self, caller: str) -> None:
        if self._limit <= 0:
            return

        now = time.monotonic()
        recent = self._seen.setdefault(caller, deque())
        while recent and now - recent[0] > self._window:
            recent.popleft()

        if len(recent) >= self._limit:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                f"more than {self._limit} requests in a minute; wait a moment",
                headers={"Retry-After": str(int(self._window))},
            )
        recent.append(now)

    def forget(self) -> None:
        """Drop every counter. For tests, which must not inherit each other."""
        self._seen.clear()


_bucket = Bucket(settings.rate_limit_per_minute)


def rate_limit(request: Request) -> None:
    """One window per client address.

    Behind Caddy every request arrives from the proxy, so the forwarded address
    is what identifies a caller. Trusting that header is only safe because
    nothing reaches this process except through the proxy — the security group
    publishes 80 and 443 and nothing else.
    """
    forwarded = request.headers.get("X-Forwarded-For", "")
    caller = forwarded.split(",")[0].strip() or (request.client.host if request.client else "?")
    _bucket.check(caller)


def bucket() -> Bucket:
    return _bucket
