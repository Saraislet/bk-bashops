from getpass import getpass
import json
import os
import requests
import sys
import time

from pybuildkite.buildkite import Buildkite, BuildState

# Requires Python 3.6+ (because fstrings <3)
#
# Run with this command:
# python3 run_build_task.py build_task.json
#
# Create a Buildkite API token here:
# https://buildkite.com/user/api-access-tokens

def get_token():
    TOKEN = os.environ.get('BUILDKITE_TOKEN')
    if not TOKEN:
        TOKEN = getpass('Please enter your Buildkite API token.\n'
                        + 'Scope: read_builds, write_builds, read_pipelines.\n'
                        + 'https://buildkite.com/user/api-access-tokens\n> ')
    if not TOKEN:
        print('Missing token.')
        exit(1)
    return TOKEN

TOKEN = get_token()
ORG = 'pagerduty'
unblock_filename = 'local_unblock_fields.json'
bk = Buildkite()
bk.set_access_token(TOKEN)

def load_json(filename):
    data = {}
    with open(filename) as file:
        data = json.load(file)
    return data


def run_build(build_task):
    build = start_build(build_task)
    print('\nStarting build.')
    time.sleep(5)
    print('Loading and unblocking build.', end='')
    build = get_build(build)
    print(f"\nURL: {build.get('web_url')}")
    build_result = unblock_build(build, build_task)
    build_state = build_result.get('state')

    print("\nJob's done.", end='')
    if build_state == 'finished':
        print(' \\o/')
    elif build_state == 'failed':
        print(' : (')
    print(f"\nBuild state: {build_state}")
    print(f"\nURL: {build_result.get('web_url')}")


def start_build(build_task):
    message = build_task['message'] or None

    return bk.builds().create_build(organization=ORG,
                                 pipeline=build_task['pipeline'],
                                 commit=build_task['commit'],
                                 branch=build_task['branch'],
                                 message=build_task['message'],
                                 ignore_pipeline_branch_filters=True)


def get_build(build):
    return get_build_number(build['pipeline']['slug'], build['number'])

def get_build_number(pipeline, build_number):
    return bk.builds().get_build_by_number(organization=ORG,
                                           pipeline=pipeline,
                                           build_number=build_number)


def get_unblock_fields(build_task, unblock_step=0):
    unblock_fields = load_json(unblock_filename)
    fields = unblock_fields.get(build_task['pipeline'])
    if not fields:
        raise KeyError

    fields = fields[unblock_step]
    for key, value in fields.items():
        if not value:
            if (build_task.get('unblock_fields')
                and len(build_task['unblock_fields']) > unblock_step
                and build_task['unblock_fields'][unblock_step].get(key)):
                # If build_task includes this unblock_field for this step with that key, use it
                fields[key] = build_task['unblock_fields'][unblock_step][key]
            else:
                fields[key] = input('Please enter unblock value for ' + key + ': ')

    return fields


def unblock_build(build, build_task):
    while len(build['jobs']) == 1:
        time.sleep(3)
        print('.', end='', flush=True)
        build = get_build(build)

    continue_states = set(['passed', 'unblocked', 'skipped', 'broken'])
    break_states = set(['finished', 'canceled', 'failed'])

    # Initial conditions
    unblock_step = 0
    state_printed = None
    i = 0

    while i < len(build['jobs']):
        build = get_build(build)
        job = build['jobs'][i]
        job_state = str(job.get('state'))

        if not state_printed:
            label = job.get('label') or job.get('name')
            print(f"\n\nStep({i}): " + str(label)
                  + '\nState: ', end='')
        if state_printed != job_state:
            state_printed = job_state
            print(job_state + '.', end='')
        print('.', end='', flush=True)

        if job.get('state') == 'blocked' and job.get('type') == 'manual':
            print('\nAttempting to unblock')
            fields = get_unblock_fields(build_task, unblock_step)
            r = bk.jobs().unblock_job(organization=ORG,
                                      pipeline=build['pipeline']['slug'],
                                      build=build['number'],
                                      job=job['id'],
                                      fields=fields)
            if r.get('state') and r['state'] == 'unblocked':
                print('Step unblocked')
                i += 1
                state_printed = None
                unblock_step +=1
                continue

        if build['state'] in break_states:
            return build

        if job.get('type') == 'waiter' or job_state in continue_states:
            i += 1
            state_printed = None
            continue

        time.sleep(3)
    return build


if __name__ == '__main__':
    if len(sys.argv) < 2:
        job_filename = input('Please enter job json filename: ')
    else:
        job_filename = sys.argv[1]

    print(f"Loading job details from file '{job_filename}'")
    build_task = load_json(job_filename)
    run_build(build_task)
