"""
Module that provides utilities for the ripper program.
"""
import os
import subprocess
from datetime import datetime
from shutil import which
import shutil

output_dir = ""
output_base = ""

def create_output_directory():
    """
    Function that creates the output directory.
    """
    global output_base
    if "BB_RIPPER_EXPORT_DIRECTORY" in os.environ:
        output_base = os.environ['BB_RIPPER_EXPORT_DIRECTORY']
    else:
        output_base = os.getcwd()

    # Append backslash to output base it it is not present.
    if not output_base.endswith('/'):
        output_base += '/'

    global output_dir
    datetime_str = datetime.today().strftime('%Y-%m-%d-T%H.%M.%S')
    output_dir = f"{output_base}bbr-{os.environ['BB_WORKSPACE']}-{datetime_str}"
    print(f"the output dir === {output_dir}")
    isExists = os.path.exists(output_dir)

    if not isExists:
        os.makedirs(output_dir)

    return output_dir

def delete_output_directory():
    """
    Delete output directory.
    """
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

def check_git():
    """
    Function that checks if git is installed.
    """
    return which('git')

def clone_repo(repo, output_dir):
    """
    Function that clones the repo to the output directory.
    """
    clone_dir = f"{output_dir}/{repo.name}"

    if not os.path.exists(clone_dir):
        os.makedirs(clone_dir)
    os.chdir(clone_dir)
    # make sure to suppress output when using https
    os.system(f"git clone {get_https_url(repo.https)} . >/dev/null 2>&1")

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
            clone_branch_cmd = f"git checkout {clone_branch}"
            os.system(clone_branch_cmd)

def zip_output_dir():
    """
    Function that zips the output directory into a tarball archive.
    """
    directory = output_dir.replace(output_base, "")
    print(f"Dir to zip: {directory}")
    os.chdir(output_base)
    os.system(f"tar -cvzf {directory}.tar.gz {directory}/")

def get_https_url(url):
    """
    Function that returns a https uld that contains the username and password.
    """
    search_text = f"https://{os.environ['BB_USER']}"
    replace_text = f"https://{ os.environ['BB_USER']}:{os.environ['BB_PASSWORD']}"
    return url.replace(search_text, replace_text)
