"""The main module"""
import time
import sys
import os
from ripper_utils import create_output_directory
from ripper_utils import check_git
from ripper_utils import clone_repo
from ripper_utils import zip_output_dir
from ripper_utils import delete_output_directory
from bbhelper import BBRepo

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/bb-ripper'
sys.path.insert(0, BASE)

start_time = time.time()

if check_git() is not None:
    output_dir = create_output_directory()
    print(output_dir)

    # # Get all repos in workspace
    workspace_repos = BBRepo.GetWorkspaceRepos(os.environ['BB_WORKSPACE'])

    COUNTER = 0
    test_counter = os.environ.get('BB_TEST_COUNTER')

    for repo in workspace_repos:
        print('================')
        print(repo.https)
        print('================')

        clone_repo(repo, output_dir)

        COUNTER += 1

        # test that test_counter is present
        if test_counter is not None:
            # test test_counter is a valid integer
            if test_counter.isdigit():
                # test for valid test_counter > 0 and counter is equal to test_counter
                if (int(test_counter) == COUNTER) and (int(test_counter) > 0):
                    break

    zip_output_dir()
    delete_output_directory()

else:
    print('git is not installed...Exiting')

print("--- COMPLETE ---")
print(f"--- {(time.time() - start_time)} seconds ---")
print("You have been ripped by the fist")
