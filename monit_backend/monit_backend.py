# Tool to monitor OpenEO backend
import os
import hashlib
import subprocess

MONIT_DIR = ['/home/berni/Master/REPO/openeo-master/', '/data/products']

GIT_REPOS = ['/home/berni/Master/REPO/openeo-master/']

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

    cm_git = {}

    CMD_GIT_URL = "git -C {} config --get remote.origin.url".format(path)
    CMD_GIT_COMMIT = "git -C {} log".format(path) # first line
    CMD_GIT_DIFF = "git -C {} diff".format(path) # Should do that ?
    print("Get Git Info")

    git_url = run_cmd(CMD_GIT_URL)
    git_commit = run_cmd(CMD_GIT_COMMIT).split("\n")[0]

    git_diff = run_cmd(CMD_GIT_DIFF)

    if git_diff == "":
        git_diff = False
    else:
        git_diff = True

    cm_git = {'url' }

    print(git_diff)



def generate_context_model():
    working_dir_hash = None

    cm = {}

    if os.path.isdir(CM_OUT):
        print("read context model")
        #TODO: Read JSON
    if os.path.isdir(INOTIFY_FILE):
        working_dir_hash = md5(INOTIFY_FILE)

    #TODO get git info


    cm['working_dir'] = working_dir_hash

    #TODO Write JSON

   # if not os.path.isdir(INOTIFY_FILE):

#init()
get_git(GIT_REPOS[0])