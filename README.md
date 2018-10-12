# Gab.com API Client

[![Build
Status](https://travis-ci.org/a-tal/gab.svg?branch=master)](https://travis-ci.org/a-tal/gab)
[![Coverage Status](https://coveralls.io/repos/github/a-tal/gab/badge.svg?branch=master)](https://coveralls.io/github/a-tal/gab?branch=master)

Based on the popular requests module, this is a minimal Gab.com API client.

There is a `help` method available on all created objects, which can
be used to discover API methods and their call arguments.

The client object is dynamically created during init time. To speed things
up, you can create a Client object with a cached copy of the collections.json
object. Please see the [example.py](example.py) for one such example. To prime
a new cache, save the response of `gab.Client()._get_api_collections()`.

Basic usage example:

```python
>>> import gab
>>> client = gab.Client(gab.Options(
...   ...
... ))
>>>
>>> client.help()
Gab.com API Client 0.0.1.

The following collections are known:
  creating_posts
  engaging_with_other_users
  feeds
  groups
  notifications
  popular
  reacting_to_posts
  user_details
>>>
>>> client.groups.help()
Gab.com API collection Groups.

These are the endpoints to access groups.

The following operations are defined:
  group_details
  group_moderation_logs
  group_users
  popular_groups
>>>
>>> client.groups.group_users.help()
Gab.com API collection Groups method Group Users.

Returns a list of given group's members. Requires read scope.

Requires the following path parameters:
  group-id

The following headers are defined:
  Authorization

Additional optional parameters defined:
  before: (example: 0)
>>>
>>> client.groups.group_users(1234)
Traceback (most recent call last):
  File "<console>", line 1, in <module>
<snipped>
requests.exceptions.HTTPError: 401 Client Error: Unauthorized for url: <snip>
>>>
```

Wow! The example ran into an auth error? What the heck?

Yeah, this client library doesn't do auth, never write your own auth.
Instead, use someone else's auth, and pass in a session object.

Please see [example.py](example.py) for a full working CLI example with authentication.
