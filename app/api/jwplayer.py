import hashlib
import math
import time
import urllib.parse

from jose import jwt


def signed_url(path, expires, secret='', host="https://cdn.jwplayer.com"):
    """
    returns a signed url, can be used for any "non-JWT" endpoint
    Args:
      path(str): the jw player route
      expires(int): the expiration time for the URL
      secret(str): JW account secret
      host:(str): url host
    """
    s = "{path}:{exp}:{secret}".format(path=path, exp=str(expires), secret=secret)
    signature = hashlib.md5(s.encode("utf-8")).hexdigest()
    signed_params = dict(exp=expires, sig=signature)
    return "{host}/{path}?{params}".format(
        host=host, path=path, params=urllib.parse.urlencode(signed_params)
    )


def get_signed_player(player_id, secret):
    """
    Return signed url for the single line embed javascript.

    Args:
      player_id (str): the player id (also referred to as player key)
      secret (str): api secret
    """
    path = "libraries/{player_id}.js".format(player_id=player_id)

    # Link is valid for 1 hour but normalized to 5 minutes to promote better caching
    expires = math.ceil((time.time() + 3600) / 300) * 300

    # Generate signature
    return signed_url(path, expires, secret)


def jwt_signed_url(path, secret='', host="https://cdn.jwplayer.com"):
    """
    Generate url with signature.
    Args:
      path (str): url path
      secret (str): API secret
      host (str): url host
    """

    # Link is valid for 1 hour but normalized to 6 minutes to promote better caching
    exp = math.ceil((time.time() + 3600) / 300) * 300

    params = {"resource": path, "exp": exp}

    # Generate token
    # note that all parameters must be included here
    token = jwt.encode(params, secret, algorithm="HS256")
    url = "{host}{path}?token={token}".format(host=host, path=path, token=token)

    return url
