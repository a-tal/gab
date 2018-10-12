"""Gab.com API client."""


import re
from dataclasses import field
from dataclasses import dataclass

import bs4
from requests import Session
from requests import Response

try:
    # lxml offers faster parsing, not a hard requirement though
    import lxml  # pylint: disable=unused-import; # noqa: F401
    PARSER = "lxml"
except ImportError:
    PARSER = "html.parser"


# client library version
__version__ = "0.0.1"

# default/fallback user agent
__user_agent__ = "gab-python-client/{} (https://github.com/a-tal/gab)".format(
    __version__,
)

# regex for pulling the scope name out of the description
# no other way to get the scope name at present :/
RESCOPE = re.compile(r".*Requires <code>(?P<scopes>.*)</code> scope.*")


@dataclass(frozen=True)
class Options:
    """Options for the Gab.com API Client."""

    # base uri for the Gab.com API discovery
    base_uri: str = "https://developers.gab.com/"

    # api_root isn't defined in spec anywhere?
    api_root: str = "https://api.gab.com/"

    # customizable user agent string
    user_agent: str = __user_agent__

    # customizable requests.Session object
    session: Session = field(default_factory=Session)

    # if you want to pre-load the collections object instead of discovery
    api_collections: object = None


class Helper:
    """Add a help method to print our dynamically assigned docstring."""

    def help(self):
        """Print a helpful string describing this object."""

        print(self.__doc__)


class Client(Helper):
    """Create a new Gab.com API Client.

    Initialized with an optional gab.Options instance.

    If Options are not passed in, the Client will only populate
    routes which do not require authentication.
    """

    def __init__(self, options: Options = None):
        """Initialize the options client and run discovery."""

        if options is None:
            options = Options()

        if options.user_agent:
            options.session.headers["User-Agent"] = options.user_agent

        options.session.headers["Accept"] = "application/json"
        self._options = options

        self._discovery()

    def _discovery(self):
        """Discover all API endpoints to configure the rest of the Client."""

        collections = self._parse_api_collections(
            self._options.api_collections or self._get_api_collections()
        )

        for name, collection in collections.items():
            setattr(self, name, collection)

        # ensures these methods are only called once for this instance
        self._discovery = null
        self._parse_api_collections = null
        # pylint: disable=attribute-defined-outside-init
        self.__doc__ = "Gab.com API Client {}.{}".format(
            __version__,
            "\n\nThe following collections are known:\n  {}".format(
                "\n  ".join(sorted(collections)),
            ) if collections else "",
        )

    def _request(self, uri: str, method: str = "get", **kwargs) -> (Response):
        """DRY, internal method to perform a HTTP request.

        Returns:
            requests.Response object
        """

        res = getattr(self._options.session, method)(uri, **kwargs)
        res.raise_for_status()
        return res

    def _get_api_collections(self) -> (dict):
        """Discovery the Gab.com API collection.

        Returns:
            the API collections response object (dict)

        Raises:
            gab.Error
        """

        res = self._request(self._options.base_uri)
        soup = bs4.BeautifulSoup(res.text, PARSER)
        return self._request("{}api/collections/{}/{}".format(
            self._options.base_uri,
            soup.find("meta", attrs={"name": "ownerId"}).attrs["content"],
            soup.find("meta", attrs={"name": "publishedId"}).attrs["content"],
        )).json()

    def _parse_api_collections(self, collections: dict) -> (dict):
        """Parse the discovered API collections.

        Args:
            collections: the API collections response object (dict)

        Returns:
            dictionary of {name: Collection} for all API operations
        """

        methods = {}
        for collection in collections["item"]:
            col = Collection(collection["name"], collection.get("description"))
            for operation in collection["item"]:
                oper = Operation(self, operation, collection["name"])
                col._add(oper)
            col._finish()
            methods[col._name] = col
        return methods


class Operation(Helper):  # pylint: disable=too-many-instance-attributes
    """Operation describes a singular API call."""

    def __init__(self, client: Client, operation: dict, parent: str):
        """Create a new Operation item.

        Args:
            client: a Client object
            operation: dictionary schema describing this operation
            parent: string referencing our parent attribute in client
        """

        self._name = _clean_name(operation["name"])
        self._parent = _clean_name(parent)
        self._client = client
        self._method = operation["request"]["method"].lower()
        self._uri = _operation_uri(client, operation["request"]["url"])
        self._description = _clean_description(
            operation["request"]["description"]
        )

        self._path_args = []  # order matters here
        for arg in operation["request"]["urlObject"].get("path", []):
            if arg.startswith("{") and arg.endswith("}"):
                self._path_args.append(arg[1:-1])

        self._query_args = {}  # name: (default, help)
        for arg in operation["request"]["urlObject"].get("query", []):
            self._query_args[arg["key"]] = (
                arg["value"],
                _clean_description(arg.get("description", {}).get("content")),
            )

        self._headers = {}  # name: format-friendly value
        for arg in operation["request"].get("header", []):
            self._headers[arg["key"].lower()] = arg["value"].replace(
                "{{", "{").replace("}}", "}")

        match = re.match(RESCOPE, operation["request"]["description"])
        if match:
            self._scopes = match.groupdict()["scopes"].split(" ")
        else:
            self._scopes = []

        # set a hopefully useful help docstring
        self.__doc__ = "Gab.com API collection {} method {}.{}{}{}{}".format(
            parent,
            operation["name"],
            "\n\n{}".format(self._description) if self._description else "",
            "\n\nRequires the following path parameters:\n  {}".format(
                "\n  ".join(self._path_args),
            ) if self._path_args else "",
            "\n\nThe following headers are defined:\n  {}".format(
                "\n  ".join([x.title() for x in self._headers]),
            ) if self._headers else "",
            "\n\nAdditional optional parameters defined:\n  {}".format(
                "\n  ".join("{}: {}{}{}".format(
                    name,
                    self._query_args[name][1],
                    " " * int(all(self._query_args[name])),
                    "(example: {})".format(self._query_args[name][0]),
                ) for name in sorted(self._query_args)),
            ) if self._query_args else "",
        )

    def __call__(self, *args, **kwargs) -> (Response):
        """Request this API operation.

        Args:
            any path parameters can be supplied via args or as kwargs

        Kwargs:
            headers: dictionary of additional headers to add
            body: string or object which can be JSON dumped
            *: any other query string arguments

        Returns:
            requests.Response object
        """

        args = self._validate_path_args(*args, **kwargs)
        return self._client._request(
            self._uri.format(**dict(zip(self._path_args, args))),
            self._method,
            headers=kwargs.get("headers", {}),
            json=kwargs.get("body", None),
            params={
                qs_arg: kwargs[qs_arg] for
                qs_arg in self._query_args if qs_arg in kwargs
            },
        )

    def _validate_path_args(self, *args, **kwargs) -> (tuple):
        """Validate the path arguments passed.

        Returns:
            tuple of path arguments

        Raises:
            TypeError on invalid call arguments
        """

        mutable_args = list(args)

        if len(args) < len(self._path_args):
            to_insert = {}
            for key, value in kwargs.items():
                if key in self._path_args:
                    to_insert[self._path_args.index(key)] = value

            for index in sorted(to_insert):
                mutable_args.insert(index, to_insert[index])

        missing_args = len(self._path_args) - len(mutable_args)
        if missing_args > 0:
            missing_arg_names = [
                repr(self._path_args[i]) for
                i in range(missing_args - 1, len(self._path_args))
            ]
            raise TypeError((
                "gab.Client.{}.{}.__call__() missing {} required positional "
                "argument{}: {}{}{}"
            ).format(
                self._parent,
                self._name,
                missing_args,
                "s" * int(missing_args > 1),
                ", ".join(missing_arg_names[:-1]),
                " and " * int(missing_args > 1),
                missing_arg_names[-1],
            ))
        elif missing_args < 0:
            raise TypeError((
                "gab.Client.{}.{}.__call__() takes {} positional argument{} "
                "but {} were given"
            ).format(
                self._parent,
                self._name,
                len(self._path_args),
                "s" * int(len(self._path_args) > 1),
                len(mutable_args),
            ))

        return tuple(mutable_args)


class Collection(Helper):
    """Collection describes a single API collection."""

    def __init__(self, name: str, description: str):
        """Create a new Collection object."""

        self._name = _clean_name(name)
        # help/display purposes only
        self._description = _clean_description(description)
        self._display_name = name
        self._operations = []

    def _add(self, operation: Operation):
        """Add an operation item."""

        setattr(self, operation._name, operation)
        self._operations.append(operation)

    def _finish(self):
        """Signal that we have finished discovery."""

        self._add = null
        self._finish = null
        # pylint: disable=attribute-defined-outside-init
        self.__doc__ = "Gab.com API collection {}.{}{}".format(
            self._display_name,
            "\n\n{}".format(self._description) if self._description else "",
            "\n\nThe following operations are defined:\n  {}".format(
                "\n  ".join(sorted([x._name for x in self._operations])),
            ) if self._operations else "",
        )
        delattr(self, "_operations")


def null(*_, **__):
    """Callable to replace run-once methods with."""

    return None


def _operation_uri(client: Client, uri: str) -> (str):
    """Parse the operation URI into a format-friendly version."""

    return uri.split("?")[0].replace("{{base_url}}", client._options.api_root)


def _clean_description(description: str) -> (str):
    """Clean the description of any HTML."""

    return bs4.BeautifulSoup(description or "", PARSER).text.strip()


def _clean_name(name: str) -> (str):
    """Clean a name up for consistency and usability (as a python attr)."""

    replacements = {
        " ": "_",
        "-": "",
        "'": "",
        '"': "",
    }
    for find, replace in replacements.items():
        name = name.replace(find, replace)
    return name.lower()
