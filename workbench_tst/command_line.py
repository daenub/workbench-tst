import configparser
import datetime as dt
import json
import pathlib
import re
import sys
from collections import deque
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen


def fetch_json(url, data=None):
    try:
        result = urlopen(url, data).read()
    except HTTPError as exc:
        sys.stderr.write(red("FAILURE: {}\n".format(exc)))
        sys.exit(1)
    else:
        return json.loads(result.decode("utf-8"))


def ansi(code):
    return lambda s: "\033[{}m{}\033[0m".format(code, s)


underline = ansi("4")
red = ansi("31")
green = ansi("32")


def show_help():
    sys.stderr.write(
        """\
Workbench timestamps command-line interface

Stopping a task right now:

    tst stop                    # Bare stop
    tst stop one two three      # Including notes

Stopping some other time:

    tst stop -5                 # 5 Minutes ago
    tst stop 13:30              # At 13:30 exactly
    tst stop -10 one two three  # Splitting 10 minutes ago with notes
    tst stop +15                # Split in 15 minutes

Submitting starts:

    tst start
    tst start -5                # I started 5 minutes ago
    tst start -5 one two three  # I started 5 minutes ago with notes

Show today's timestamps:

    tst list

Show help:

    tst
    tst help

"""
    )
    sys.exit(1)


def show_unknown_command_message(command):
    time = dt.datetime.now().time().isoformat("minutes")

    sys.stderr.write(
        """\
'{command}' is an unknown command. See 'tst help'.
Current time: {time}
""".format(
            time=time, command=command
        )
    )
    sys.exit(1)


def list_timestamps(*, url, user):
    url = url.replace("create-timestamp", "list-timestamps")
    data = fetch_json(url + "?user={}".format(user), None)
    sys.stdout.write(green("Timestamps\n"))
    sys.stdout.write(
        "\n".join(
            "{} {}".format(
                row["timestamp"],
                underline(row["comment"]) if row["comment"] else "",
            )
            for row in data["timestamps"]
        )
    )
    sys.stdout.write("\n{}\n".format(green("Logged: {}h".format(data["hours"]))))


def create_timestamp(*, url, user):
    args = deque(sys.argv[1:])
    data = {
        "type": args.popleft(),
        "user": user,
    }
    while True:
        if not args:
            break
        if re.match(r"^[0-9]{1,2}:[0-9]{2}$", args[0]):
            data["time"] = args.popleft()
        elif re.match(r"^[-+][0-9]+$", args[0]):
            time = dt.datetime.now() + dt.timedelta(minutes=int(args.popleft()))
            data["time"] = time.replace(microsecond=0).time().isoformat()
        else:
            break

    data["notes"] = " ".join(args)

    data = fetch_json(url, urlencode(data).encode("utf-8"))
    sys.stdout.write(green(data["success"]))
    sys.stdout.write("\n")


def main():
    config = configparser.ConfigParser()
    try:
        config.read_string(pathlib.Path("~/.workbench").expanduser().read_text())
    except FileNotFoundError:
        sys.stderr.write(red("Config file ~/.workbench is missing\n"))
        sys.exit(1)

    user = config.get("workbench", "user")
    url = config.get("workbench", "url")

    if len(sys.argv) < 2 or sys.argv[1] == "help":
        show_help()
    elif sys.argv[1] == "list":
        list_timestamps(url=url, user=user)
    elif sys.argv[1] in {"start", "stop"}:
        create_timestamp(url=url, user=user)
    elif sys.argv[1]:
        show_unknown_command_message(sys.argv[1])
    else:
        show_help()


if __name__ == "__main__":
    main()
