""""Example of a CLI application using the Gab.com API client."""


import os
import json
import uuid
import codecs
import webbrowser
from http import server
from urllib.parse import parse_qsl

try:
    from rauth import OAuth2Service
except ImportError:
    raise SystemExit(
        "This example makes use of the rauth library. To install it, run "
        "`pip install rauth`"
    )

import gab


def cached_collections():
    """Return collections from a local file cache."""

    try:
        with open("collections.json", "r") as opencollections:
            return json.loads(opencollections.read())
    except Exception as error:
        print("warning: failed to read collections cache: {!r}".format(error))
        return {}


def get_auth_code(port, auth_uri, state):
    """Generate a new auth code.

    KWargs:
        port: integer port to start the callback server on
        auth_uri: uri to start the auth flow with
        state: string uuid to verify the auth response with

    Returns:
        string auth code

    Raises:
        SystemExit
    """

    webbrowser.open(auth_uri)

    auth = {}

    class Callback(server.BaseHTTPRequestHandler):
        """Oauth2 callback handler."""

        def log_message(self, *_, **__):  # pylint: disable=arguments-differ
            """Silence logging."""

            pass

        def do_GET(self):  # pylint: disable=invalid-name
            """Accept a GET request."""

            if "?" in self.path:
                query_string = dict(parse_qsl(self.path.split("?")[1]))

                if query_string.get("state") != state:
                    raise SystemExit("auth state mismatch!")

                auth["code"] = query_string.get("code", None)

                msg = "<h1>Token received</h1><h2>(you can close this)</h2>"
            else:
                msg = "<h1>malformed request</h1><h2>:(</h2>"

            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(
                codecs.encode("<html><body>{}</body></html>".format(msg))
            )

    httpd = server.HTTPServer(("localhost", port), Callback)
    httpd.handle_request()

    if not auth.get("code"):
        raise SystemExit("failed to acquire auth code")

    return auth["code"]


def get_session(scope):
    """Create a new authenticated requests.Session."""

    client_id = os.environ.get("GAB_API_CLIENT_ID")
    secret = os.environ.get("GAB_API_CLIENT_SECRET")
    if not all((client_id, secret)):
        raise RuntimeError(
            "Both GAB_API_CLIENT_ID and GAB_API_CLIENT_SECRET must be set in "
            "the environment in order to run this example."
        )

    service = OAuth2Service(
        name="gab",
        client_id=client_id,
        client_secret=secret,
        access_token_url="https://api.gab.com/oauth/token",
        authorize_url="https://api.gab.com/oauth/authorize",
        base_url="https://api.gab.com/",
    )

    state = str(uuid.uuid4())
    port = int(os.environ.get("GAB_API_CALLBACK_PORT", 8080))
    redirect_uri = "http://localhost:{}/callback".format(port)

    params = {
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "state": state,
        "scope": scope,
    }

    code = get_auth_code(port, service.get_authorize_url(**params), state)

    return service.get_auth_session(
        data={
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        },
        decoder=json.loads,
    )


def main():
    """Example of an authenticated client request."""

    client = gab.Client(gab.Options(
        api_collections=cached_collections(),
        session=get_session("read"),
    ))

    res = client.user_details.loggedin_users_details()  # pylint: disable=E1101

    try:
        print(json.dumps(res.json(), sort_keys=True, indent=4))
    except Exception:
        print("{}: {}".format(res.status_code, res.text))


if __name__ == "__main__":
    main()
