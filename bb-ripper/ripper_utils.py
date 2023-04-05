from asyncio import constants, subprocess
import os 
import subprocess
from datetime import datetime
from shutil import which
import shutil

output_dir = ""
output_base = ""

# Creates the output directory
def create_output_directory():
    global output_base
    if "BB_RIPPER_EXPORT_DIRECTORY" in os.environ:
        output_base = os.environ['BB_RIPPER_EXPORT_DIRECTORY']
    else:
        output_base = os.getcwd()

    # Append backslash to output base it it is not present.
    if not output_base.endswith('/'):
        output_base += '/'
    
    global output_dir
    output_dir = '{0}bbr-{1}-{2}'.format(output_base, os.environ['BB_WORKSPACE'], datetime.today().strftime('%Y-%m-%d-T%H.%M.%S'))
    print("the output dir === {0}".format(output_dir))
    isExists = os.path.exists(output_dir)
    
    if not isExists:
        os.makedirs(output_dir)

    return output_dir

# Delete output directory
def delete_output_directory():
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

# Checks if git is installed
def check_git():
    return(which('git'))

# clones a repo and all it branches
def clone_repo(repo, output_dir):
    clone_dir = "{0}/{1}".format(output_dir, repo.name)
    
    if not os.path.exists(clone_dir):
        os.makedirs(clone_dir)
    os.chdir(clone_dir)
    # make sure to suppress output when using https
    os.system("git clone {0} . >/dev/null 2>&1".format(get_https_url(repo.https)))
        
    branches = subprocess.run(["git", "branch", "-r"], 
                                stdout=subprocess.PIPE, 
                                universal_newlines=True)
    
    branch_list = branches.stdout.split("\n")

    for b in branch_list:
        if "->" in b:
            # JUST A POINTER TO HEAD DO NOT PROCESS
            print("SKIPPING HEAD")
        else:
            clone_branch = b.replace(" ", "").replace("origin/", "")
            clone_branch_cmd = "git checkout {0}".format(clone_branch)
            os.system(clone_branch_cmd)

# zips the output directory
def zip_output_dir():
    dir = output_dir.replace(output_base, "")
    print("Dir to zip: {0}".format(dir))
    os.chdir(output_base)
    os.system("tar -cvzf {0}.tar.gz {0}/".format(dir))

# get a https url that contains the username and password
def get_https_url(url):
    search_text = "https://{0}".format(os.environ['BB_USER'])
    replace_text = "https://{0}:{1}".format(os.environ['BB_USER'], os.environ['BB_PASSWORD'])
    return url.replace(search_text, replace_text)