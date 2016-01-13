# acronym bot

Controls [@acronymlister](https://twitter.com/acronymlister), a Twitter bot that posts the meanings of three letter acronyms, as found on Wikipedia.

The command line tool requires a `bots.yaml` file, as described in [`twitter_bot_utils`](https://github.com/fitnr/twitter_bot_utils).

Requires Python 3.5, sqlite3. Initialize the database with `make`, install the package with `make install`.

````
usage: acrobot [-h] [-c PATH] [-u SCREEN_NAME] [-n] [-v] [-q] [-V] database

positional arguments:
  database

optional arguments:
  -h, --help            show this help message and exit
  -c PATH, --config PATH
                        bots config file (json or yaml)
  -u SCREEN_NAME, --user SCREEN_NAME
                        Twitter screen name
  -n, --dry-run         Don't actually do anything
  -v, --verbose         Run talkatively
  -q, --quiet           Run quietly
  -V, --version         show program's version number and exit
````
