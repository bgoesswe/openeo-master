# Tool to monitor OpenEO backend
import os
import hashlib
import subprocess
import json

MONIT_DIR = ['/data/MASTER/REPO/openeo-master/', '/data/products']

GIT_REPOS = ['/data/MASTER/REPO/openeo-master/']

CM_OUT = '/data/system_context_model.json'

INOTIFY_FILE = '/data/inotify.log'

INOTIFY_CALL = "inotifywait -d -e modify -e attrib -e moved_to -e create -e delete {0} -o {1}"

initialized = False


def init():
    for dir in MONIT_DIR:
        inotify_cmd = INOTIFY_CALL.format(dir, INOTIFY_FILE)
        print("Call: {}".format(inotify_cmd))
        # os.system(inotify_cmd)


def md5(file):
    hash_md5 = hashlib.md5()
    with open(file, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def run_cmd(command):
    result = subprocess.run(command.split(), stdout=subprocess.PIPE)
    return result.stdout.decode("utf-8")

def get_git(path):

    CMD_GIT_URL = "git -C {} config --get remote.origin.url".format(path)
    CMD_GIT_BRANCH = "git -C {} branch".format(path)
    CMD_GIT_COMMIT = "git -C {} log".format(path) # first line
    CMD_GIT_DIFF = "git -C {} diff".format(path) # Should do that ?

    print("Get Git Info")

    git_url = run_cmd(CMD_GIT_URL).split("\n")[0]
    git_commit = run_cmd(CMD_GIT_COMMIT).split("\n")[0].replace("commit", "").strip()
    git_diff = run_cmd(CMD_GIT_DIFF)

    git_diff = hashlib.md5(git_diff.encode("utf-8"))
    git_diff = git_diff.hexdigest()

    git_branch = run_cmd(CMD_GIT_BRANCH).replace("*", "").strip()

    cm_git = {'url': git_url,
              'branch': git_branch,
              'commit': git_commit,
              'diff': git_diff}

    return cm_git


def generate_context_model():
    working_dir_hash = None

    backend_verion = 1

    cm_old = {}

    cm = {}

    if os.path.isfile(CM_OUT):
        json1_file = open(CM_OUT)
        json1_str = json1_file.read()
        cm_old = json.loads(json1_str)
        if "backend_version" in cm_old:
            backend_verion = cm_old["backend_version"]

    if os.path.isfile(INOTIFY_FILE):
        working_dir_hash = md5(INOTIFY_FILE)

    cm['git_repos'] = []
    for repo in GIT_REPOS:
        cm_git = get_git(repo)
        cm['git_repos'].append(cm_git)

    cm['backend_version'] = backend_verion
    cm['working_dir_changes'] = working_dir_hash

    if cm != cm_old:
        cm["backend_version"] += 1

    with open(CM_OUT, 'w') as outfile:
        json.dump(cm, outfile, sort_keys=True, indent=4, separators=(',', ': '))

    return cm
   # if not os.path.isdir(INOTIFY_FILE):

#init()
print(generate_context_model())
