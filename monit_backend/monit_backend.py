# Tool to monitor OpenEO backend
import os, sys
import hashlib
import subprocess
import json

config_dir = "backend_monit.conf"


INOTIFY_CALL = "{0} -d -e modify -e attrib -e moved_to -e create -e delete {1} -o {2}"


def load_config(file):
    json1_file = open(file)
    json1_str = json1_file.read()
    config = json.loads(json1_str)
    return config


def init(config):
    for dir in config["monit_dirs"]:
        inotify_cmd = INOTIFY_CALL.format(config["inotifywait_path"], dir, config["inotify_tmpfile"])
        print("Call: {}".format(inotify_cmd))
        os.system(inotify_cmd)


def md5(file):
    hash_md5 = hashlib.md5()
    with open(file, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def run_cmd(command):
    result = subprocess.run(command.split(), stdout=subprocess.PIPE)
    return result.stdout.decode("utf-8")


def get_git(path, config):

    git_cmd = config["git_path"]

    CMD_GIT_URL = "{0} -C {1} config --get remote.origin.url".format(git_cmd, path)
    CMD_GIT_BRANCH = "{0} -C {1} branch".format(git_cmd, path)
    CMD_GIT_COMMIT = "{0} -C {1} log".format(git_cmd, path) # first line
    CMD_GIT_DIFF = "{0} -C {1} diff".format(git_cmd, path) # Should do that ?

    # print("Get Git Info")

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


def generate_context_model(config):
    working_dir_hash = None

    backend_verion = 1

    cm_old = {}

    cm = {}

    CM_OUT = config["cm_outputfile"]
    INOTIFY_FILE = config["inotify_tmpfile"]
    GIT_REPOS = config["git_repos"]

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
        cm_git = get_git(repo, config)
        cm['git_repos'].append(cm_git)

    cm['backend_version'] = backend_verion
    cm['working_dir_changes'] = working_dir_hash

    if cm != cm_old:
        cm["backend_version"] += 1

        with open(CM_OUT, 'w') as outfile:
            json.dump(cm, outfile, sort_keys=True, indent=4, separators=(',', ': '))

    return cm


def usage(argv):
    return "{}  [-i | --init] [-c | --check] <config_file> \n" \
           "--init: Initialize Monittool, by starting the monitor daemons.\n" \
           "--check: Checks on system context model and updates it.\n" \
           "configfile: Backend monitoring config file.\n" \
           "Only one of the options can be set at once.\n" \
           "But one has to be set.".format(argv[0])


if __name__ == "__main__":
    initial = False
    monit = False

    config = {}
    if not os.path.isfile(sys.argv[-1]) or len(sys.argv) < 2:
        print(usage(sys.argv))
        if len(sys.argv) >= 2:
            print("Error, {} is not a valid config file.".format(sys.argv[-1]))
        sys.exit(-1)
    else:
        config = load_config(sys.argv[-1])

    if "--init" in sys.argv or "-i" in sys.argv:
        initial = True

    if "--check" in sys.argv or "-c" in sys.argv:
        monit = True


    if monit and initial:
        print(usage(sys.argv))
    elif not monit and not initial:
        print(usage(sys.argv))
    else:
        if monit:
            print("Checking on new System Context Model...")
            generate_context_model(config)
        if init:
            print("Initialize Monitoring Daemons...")
            init(config)
