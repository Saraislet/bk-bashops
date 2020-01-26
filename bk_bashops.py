import run_build_task

from getpass import getpass
from pprint import pprint
import os
import sys

# Requires Python 3.6+ (because fstrings <3)
#
# Create a Buildkite API token here:
# https://buildkite.com/user/api-access-tokens

JSON_PATH = '.'


def get_json_filenames(path):
    return [f for f in os.listdir(path) if f.endswith(".json")]


def pick_file(filenames):
    # Don't make me write pagination.
    # Fuck it, fine.
    offset = 0
    count = 10
    print("\nPlease select a file.\n")
    while True and offset < len(filenames):
        for i, f in enumerate(filenames[offset:offset+count]):
            print(f"({i}) {f}")
        print("(m) more\n")

        choice = input("> ")
        if choice.lower() == 'm':
            offset += count
            continue

        if choice.isnumeric() and int(choice) in range(offset, count):
            return filenames[int(choice)]

        # passive-aggressively end program
        print("I'm sorry, I didn't understand your input.")
        exit(1)


def get_task(build_tasks):
    """This function could support a picker."""
    return build_tasks[0]


if __name__ == '__main__':
    json_filenames = get_json_filenames(JSON_PATH)
    filename = pick_file(json_filenames)
    build_tasks = run_build_task.load_json(filename)
    build_task = get_task(build_tasks)
    pprint(build_task)
    run_build_task.run_build(build_task)
