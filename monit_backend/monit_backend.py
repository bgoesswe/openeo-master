# Tool to monitor OpenEO backend
import os
import hashlib

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

#def check_on_monitor():

   # if not os.path.isdir(INOTIFY_FILE):

init()
