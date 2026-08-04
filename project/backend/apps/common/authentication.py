"""
Authentication against Supabase Auth.

The frontend uses supabase-js to sign users up/in directly against Supabase
(this backend never handles passwords). Every API request from an
authenticated user carries `Authorization: Bearer <supabase access token>`,
a JWT signed by Supabase Auth. We verify that signature here and trust its
`sub` claim (the Supabase auth.users.id, a UUID) as the request's user id --
no round-trip to Supabase needed per request.

Supabase now signs new projects' tokens asymmetrically (ES256) by default,
and is deprecating the old shared-secret (HS256) signing model along with
the old `anon`/`service_role` API keys -- see
https://supabase.com/docs/guides/auth/signing-keys and
https://supabase.com/docs/guides/getting-started/api-keys. This class
verifies ES256 tokens against the project's public JWKS endpoint (no secret
involved at all), and only falls back to a shared `SUPABASE_JWT_SECRET` for
HS256 tokens -- i.e. only if your project hasn't migrated to asymmetric
signing keys yet in Project Settings -> JWT Keys. Once you rotate to
asymmetric keys there, SUPABASE_JWT_SECRET can be left blank.
"""
import jwt
from django.conf import settings
from jwt import PyJWKClient
from rest_framework import authentication, exceptions

# One client per process, reused across requests. PyJWKClient caches the
# fetched JWKS in memory and only re-fetches when it sees an unrecognized
# `kid`, so this does NOT make a network call on every request -- just
# occasionally, cheaply. Supabase itself also caches this endpoint for 10
# minutes on their edge, so don't add extra caching on top that could delay
# picking up a genuine key rotation/revocation beyond that.
_jwks_client = None


def _get_jwks_client():
    global _jwks_client
    if _jwks_client is None:
        if not settings.SUPABASE_URL:
            return None
        _jwks_client = PyJWKClient(
            f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json",
            cache_keys=True,
        )
    return _jwks_client


class SupabaseUser:
    """Lightweight stand-in for django.contrib.auth's User.

    We deliberately do NOT create rows in Django's own auth_user table --
    Supabase's auth.users table (in the same Postgres database, different
    schema) is the single source of truth for accounts. This class just
    gives DRF/views the interface they expect (`request.user.id`,
    `is_authenticated`, etc.).
    """

    def __init__(self, claims: dict):
        self.claims = claims
        self.id = claims.get("sub")
        self.email = claims.get("email", "")
        self.is_authenticated = True
        self.is_anonymous = False

    def __str__(self):
        return self.email or self.id

    @property
    def pk(self):
        return self.id


class SupabaseJWTAuthentication(authentication.BaseAuthentication):
    keyword = b"bearer"

    def authenticate(self, request):
        header = authentication.get_authorization_header(request).split()
        if not header or header[0].lower() != self.keyword:
            return None  # no/foreign auth header -- let other checks (e.g. AllowAny views) proceed

        if len(header) != 2:
            raise exceptions.AuthenticationFailed("Malformed Authorization header.")

        token = header[1].decode("utf-8")

        try:
            unverified_alg = jwt.get_unverified_header(token).get("alg")
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed("Invalid authentication token.")

        try:
            if unverified_alg == "HS256":
                # Legacy symmetric signing -- only reachable if the project
                # hasn't migrated to asymmetric JWT signing keys yet.
                if not settings.SUPABASE_JWT_SECRET:
                    raise exceptions.AuthenticationFailed(
                        "Server received a legacy HS256 token but SUPABASE_JWT_SECRET "
                        "isn't set. Either configure it, or migrate the Supabase project "
                        "to asymmetric JWT signing keys (Project Settings -> JWT Keys)."
                    )
                claims = jwt.decode(
                    token,
                    settings.SUPABASE_JWT_SECRET,
                    algorithms=["HS256"],
                    audience=settings.SUPABASE_JWT_AUDIENCE,
                )
            else:
                # Asymmetric (ES256, current default for new Supabase
                # projects) -- verified against the project's public JWKS,
                # no shared secret involved.
                jwks_client = _get_jwks_client()
                if jwks_client is None:
                    raise exceptions.AuthenticationFailed(
                        "Server is missing SUPABASE_URL -- auth cannot be verified."
                    )
                signing_key = jwks_client.get_signing_key_from_jwt(token)
                claims = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=["ES256", "RS256"],
                    audience=settings.SUPABASE_JWT_AUDIENCE,
                )
        except exceptions.AuthenticationFailed:
            raise
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed("Session expired -- please sign in again.")
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed("Invalid authentication token.")
        except Exception:
            # PyJWKClient raises its own (non-jwt.InvalidTokenError) errors
            # for network/lookup failures against the JWKS endpoint.
            raise exceptions.AuthenticationFailed("Could not verify authentication token.")

        if not claims.get("sub"):
            raise exceptions.AuthenticationFailed("Token missing subject claim.")

        return (SupabaseUser(claims), token)