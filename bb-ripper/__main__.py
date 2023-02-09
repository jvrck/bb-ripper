from bbhelper import bbhelper
import sys,os
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/bb-ripper'
sys.path.insert(0, BASE)
from ripper_utils import *
import time

start_time = time.time()

if check_git() is not None:
    output_dir = create_output_directory()
    print(output_dir)

    # # Get all repos in workspace
    workspace_repos = bbhelper.BBRepo.GetWorkspaceRepos(os.environ['BB_WORKSPACE'])

    counter = 0
    for repo in workspace_repos:
        print('================')
        print(repo.https)
        print('================')

        clone_repo(repo, output_dir)

        counter += 1
        # if counter > 0:
        #     break

    zip_output_dir()

else:
    print('git is not installed...Exiting')

print("--- COMPLETE ---")
print("--- %s seconds ---" % (time.time() - start_time))
print("You have been ripped by the fist")