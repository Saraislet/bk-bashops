import run_build_task

from pprint import pprint
import os
import sys

# Requires Python 3.6+ (because fstrings <3)
#
# Create a Buildkite API token here:
# https://buildkite.com/user/api-access-tokens

JSON_PATH = '.'


def get_json_filenames(path):
    return [f for f in os.listdir(path) if f.endswith('.json')]


def pick_file(filenames):
    # Don't make me write pagination.
    # Okay, fine.
    offset = 0
    count = 10
    print('\nPlease select a file.\n')
    while True and offset < len(filenames):
        for i, f in enumerate(filenames[offset:offset+count]):
            print(f"({i}) {f}")
        print("(m) more\n")

        choice = input('> ')
        print('\n', end='')
        if choice.lower() == 'm':
            offset += count
            continue

        if choice.isnumeric() and int(choice) in range(offset, count):
            return filenames[int(choice)]

        # passive-aggressively end program
        print("I'm sorry, I didn't understand your input.")
        exit(1)


def run_tasks(task_queue):
    for task in task_queue:
        print('\n Starting task: ')
        pprint(task)
        run_build_task.run_build(task)
    print('Finished with all tasks in the queue.')


def choose_tasks(task_queue):
    json_filenames = get_json_filenames(JSON_PATH)
    while True:
        f = pick_file(json_filenames)
        task_queue.extend(run_build_task.load_json(f))
        print(task_queue)
        print('Would you like to add another task to the queue?')
        choice = input('y/n > ')
        if choice.lower() != 'y':
            break
    return task_queue


def enqueue_tasks(task_queue):
    # Could load task queue from file.
    if len(sys.argv) > 1:
        filenames = sys.argv[1:]
        for f in filenames:
            task_queue.extend(run_build_task.load_json(f))
    else:
        task_queue.extend(choose_tasks(task_queue))
    return task_queue


def print_task_queue(task_queue):
    print('Task Queue:\n')
    for task in task_queue:
        pprint(task)
    print('\n')

def confirm_lock():
    '''Confirm that user holds the lock'''
    # Could include command-line arguments to bypass
    # Could check BK user and lock holder for auto-bypass
    # e.g., https://github.com/PagerDuty/chef/blob/master/.buildkite/lock_check.sh#L13-L17
    print('Are you the person holding the lock'
          + ' OR do you have their explicit approval to do this build?')
    if input('y/n > ').lower() != 'y':
        exit('\nPlease get the lock before running build tasks.')

if __name__ == '__main__':
    task_queue = []
    task_queue = enqueue_tasks(task_queue)
    print_task_queue(task_queue)
    confirm_lock()
    run_tasks(task_queue)
