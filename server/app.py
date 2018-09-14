from flask import Flask, render_template, request, jsonify
import os, subprocess
import uuid
import cpuinfo
import json
from hashlib import md5
import collections
#from PIL import Image # Python Imaging Library

BACKEND_VERSION = "1"
OPENEO_API_VERSION = "0.0.3"

DOCKER_BASE_IMAGE = "python:3.6.4"
DOCKER_VERSION = "docker -v"

HW_ENV_CMD = "lspci -nnk"
OS_ENV_CMD = "dpkg -l"

SYSTEM_CM_OUT = '/data/system_context_model.json'

app = Flask(__name__)

SUDO_PASS = ""

# DOCKER_NOW_OUT_DIR = "/sdcard/docker/volumes/masterbackendvol/_data/app/.noworkflow"
LOCAL_NOW_OUT_DIR = "../release-0.0.2/.noworkflow"
JOB_LOCATION = "/sdcard/Master/JOBS"

IMAGE_DIR = "../release-mini/*"

PROCESS_GRAPH = {
   "process_graph":{
      "process_id":"min_time",
      "args":{
         "imagery":{
            "process_id":"NDVI",
            "args":{
               "imagery":{
                  "process_id":"filter_daterange",
                  "args":{
                     "imagery":{
                        "process_id":"filter_bbox",
                        "args":{
                           "imagery":{
                              "product_id":"s2a_prd_msil1c"
                           },
                           "left":652001,
                           "right":672000,
                           "top":5161000,
                           "bottom":5181000,
                           "srs":"EPSG:32632"
                        }
                     },
                     "from":"2017 -01 -01",
                     "to":"2017 -01 -08"
                  }
               },
               "red":"B04",
               "nir":"B08"
            }
         }
      }
   }
}

# def gen_dict_extract(key, var):
#     if hasattr(var,'iteritems'):
#         for k, v in var.iteritems():
#             if k == key:
#                 yield v
#             if isinstance(v, dict):
#                 for result in gen_dict_extract(key, v):
#                     yield result
#             elif isinstance(v, list):
#                 for d in v:
#                     for result in gen_dict_extract(key, d):
#                         yield result


def get_job_cm(job_id):
    location = JOB_LOCATION + "/" + str(job_id) + "/"
    # if there is already a cm
    if os.path.isfile(location + "context_model.json"):
        json1_file = open(location + "context_model.json")
        json1_str = json1_file.read()
        cm = json.loads(json1_str)
    else:
        cm = {}

    return cm


def get_system_cm():
    cm = {}

    if os.path.isfile(SYSTEM_CM_OUT):
        json1_file = open(SYSTEM_CM_OUT)
        json1_str = json1_file.read()
        cm = json.loads(json1_str)

    return cm


def get_filehash(jsonfile):
    data_dir = "/data/"
    hasher = md5()
    with open(jsonfile) as json_data:
        d = json.load(json_data)
        outdir = data_dir + d['file_paths'][0]
        with open(outdir, 'rb') as afile:
            buf = afile.read()
            hasher.update(buf)
        return hasher.hexdigest()


def processgraph_add_hashes(graph):

    outdir_dict = {
        "min_time": "/data/job_data/template_id_mintime/files.json",
        "NDVI": "/data/job_data/template_id_ndvi/files.json",
        "filter_bbox": "/data/job_data/template_id/files.json",
        "filter_daterange": "/data/job_data/template_id/files.json"
    }
    buffer = {}
    for key, value in graph.items():
        if isinstance(value, dict):
            buf = processgraph_add_hashes(value)
            if buf:
                buffer = {**buffer, **processgraph_add_hashes(value)}
            for key2, value2 in graph.items():
                if not isinstance(value2, dict):
                    if value2 in outdir_dict.keys():
                        buffer[str(len(buffer.items()))+"_"+value2] = get_filehash(outdir_dict[value2])
            return buffer
    return buffer


def create_context_model(job_id):
   location = JOB_LOCATION+"/"+str(job_id)+"/"

   output_location = "/data/job_data/template_id_mintime/min-time_epsg-4326.tif"

   CODE_CMD = 'now show --dir={}'.format(location)

   CODE_ENV = 'now show -m --dir={}'.format(location)

   INPUT_FILE_CMD = 'now show -f --dir={}'.format(location)

   process_graph_file = location+"process_graph.json"

   context_model = {}

   # file_hashes
   process_graph = open(process_graph_file).read()
   file_hashes = processgraph_add_hashes(json.loads(process_graph))

   # read process graph

   process_graph = open(process_graph_file).read()
   process_graph = json.loads(process_graph)

   # Retrieving data

   process = subprocess.Popen(OS_ENV_CMD.split(), stdout=subprocess.PIPE)
   output, error = process.communicate()

   os_hash = md5(output).hexdigest()

   process = subprocess.Popen(HW_ENV_CMD.split(), stdout=subprocess.PIPE)
   output, error = process.communicate()

   hw_hash = md5(output).hexdigest()

   # Code hash
   process = subprocess.Popen(CODE_CMD.split(), stdout=subprocess.PIPE)
   output, error = process.communicate()

   output = str(output).split('\\n')

   trial = output[1].split(':')[1].strip()
   code_hash = output[5].split(':')[1].strip()

   # Code environment hash
   process = subprocess.Popen(CODE_ENV.split(), stdout=subprocess.PIPE)
   output, error = process.communicate()
   output = str(output).replace('\\n', '').split('Name:')

   python_modules = []

   for line in output:
       lines = line.strip().split(' ')
       if '.' in lines[0] or '[now]' in lines[0]:
           continue

       module = {'name': lines[0],
                 'version': lines[5],
                 'hash': lines[16]
                 }
       python_modules.append(module)

   # Input Hash

   process = subprocess.Popen(INPUT_FILE_CMD.split(), stdout=subprocess.PIPE)
   # output, error = process.communicate()

   process = subprocess.Popen('grep -A 6 02_extracted'.split(), stdin=process.stdout,
                            stdout=subprocess.PIPE)

   process = subprocess.Popen('grep after'.split(), stdin=process.stdout,
                              stdout=subprocess.PIPE)

   output, error = process.communicate()

   output = str(output).split('\\n')

   input_hashes = []
   for entry in output:
       entries = entry.split(':')
       if len(entries) > 1:
         input_hashes.append(entries[1])

   input_hashes = sorted(input_hashes)
   input_hashes = str(input_hashes)
   input_hash = md5(input_hashes.encode()).hexdigest()

   # output hash

   hasher = md5()
   with open(output_location, 'rb') as afile:
       buf = afile.read()
       hasher.update(buf)
   output_hash = hasher.hexdigest()

   # save to json

   context_model['output_data'] = output_hash
   context_model['input_data'] = input_hash
   #context_model['backend_version'] = BACKEND_VERSION
   context_model['openeo_api'] = OPENEO_API_VERSION
   context_model['process_graph'] = process_graph
   context_model['inter_output'] = file_hashes
   context_model['job_id'] = job_id
   #context_model['os'] = os_hash
   #context_model['hw'] = hw_hash
   context_model['code'] = code_hash
   context_model['code_env'] = python_modules
   context_model['backend_env'] = get_system_cm()

   cm = get_job_cm(job_id)

   cm[trial] = context_model
   # context_model = json.loads(str(context_model))

   with open('context_model.json', 'w') as outfile:
      json.dump(cm, outfile, sort_keys=True, indent=4, separators=(',', ': '))

   command = 'cp context_model.json {}'.format(location)

   os.system('echo %s|sudo -S %s' % (SUDO_PASS, command))

   print(cm)
   return cm


def compare_previous(job_id):
    print("compare_previous")

    location = JOB_LOCATION + "/" + str(job_id) + "/"

    if os.path.isfile(location + "context_model.json"):
        json1_file = open(location + "context_model.json")
        json1_str = json1_file.read()
        cm = json.loads(json1_str)

    orderer_cm = collections.OrderedDict(sorted(cm.items(), reverse=True))

    orderer_cm = list(orderer_cm)

    if len(orderer_cm) < 2:
        return None

    current = cm[orderer_cm[0]]
    before = cm[orderer_cm[1]]

    cmp_dict = {}

    for key in current:
        if key in ["hw"]:
            continue
        if current[key] == before[key]:
            cmp_dict[key] = "EQUAL"
        else:
            cmp_dict[key] = "DIFFERENT"

    return cmp_dict


def compare_jobs(job1_id, job2_id):
    print("compare_jobs")

    location_job1 = JOB_LOCATION + "/" + str(job1_id) + "/"
    location_job2 = JOB_LOCATION + "/" + str(job2_id) + "/"

    if os.path.isfile(location_job1 + "context_model.json"):
        json1_file = open(location_job1 + "context_model.json")
        json1_str = json1_file.read()
        cm1 = json.loads(json1_str)
    else:
        return None

    orderer_cm1 = collections.OrderedDict(sorted(cm1.items(), reverse=True))

    orderer_cm1 = list(orderer_cm1)

    if os.path.isfile(location_job2 + "context_model.json"):
        json2_file = open(location_job2 + "context_model.json")
        json2_str = json2_file.read()
        cm2 = json.loads(json2_str)
    else:
        return None

    orderer_cm2 = collections.OrderedDict(sorted(cm2.items(), reverse=True))

    orderer_cm2 = list(orderer_cm2)

    cm1 = cm1[orderer_cm1[0]]
    cm2 = cm2[orderer_cm2[0]]

    cmp_dict = {}
    for key in cm1:
        try:
            # skip hw for the comparison
            if key in ["hw"]:
                continue
            if cm1[key] == cm2[key]:
                cmp_dict[key] = "EQUAL"
            else:
                cmp_dict[key] = "DIFFERENT"
                print("DIFF {} != {}".format(cm1[key], cm2[key]))
            if key in ["inter_output"]:
                cmp_dict[key] = {}
                for k in cm1[key]:
                    if k in cm2[key]:
                        if cm1[key][k] == cm2[key][k]:
                            cmp_dict[key][k] = "EQUAL"
                        else:
                            if cm1[key][k] == cm2[key][k]:
                                cmp_dict[key][k] = "EQUAL"
                            else:
                                cmp_dict[key][k] = "DIFFERENT"
                                # print("DIFF {} != {}".format(cm1[key], cm2[key]))
                    else:
                        cmp_dict[key][k] = "MISSING"
                        # print("MISS {} != {}".format(cm1[key], cm2[key]))
        except KeyError as e:
            continue
    return cmp_dict


def replace_item(obj, key, replace_value):
    for k, v in obj.items():
        if isinstance(v, dict):
            obj[k] = replace_item(v, key, replace_value)
    if key in obj:
        obj[key] = replace_value
    return obj


def find_item(obj, key):
    returner = None
    for k, v in obj.items():
        if isinstance(v, dict):
            returner = find_item(v, key)
            if returner:
                return returner
    if key in obj:
        returner = obj[key]
        if returner:
            return returner
    if returner:
        return returner


def update_conf(content):
    config_dirs = ["../release-mini/config/config.json", "../release-mini/config/config_ndvi.json"]

    interesting_keys = ["red", "nir", "left", "right", "top", "bottom", "from", "to", "srs"]

    # content = str(content)

    content_dict = {}

    for interest in interesting_keys:

        val = find_item(content, interest)
        if val:
            content_dict[interest] = val


    for config_file in config_dirs:

        with open(config_file) as json_data:
            d = json.load(json_data)

            for key, val in content_dict.items():
                replace_item(d, key, val)

            print("Updated Config to "+str(d))

            with open(config_file, 'w+') as outfile:
                json.dump(d, outfile)


def cp_job(content, job_id):

    job_id =str(job_id)

    job_whole_path = JOB_LOCATION + "/" + job_id

    process_graph_file = job_whole_path+'/process_graph.json'

    # if not os.path.isfile(process_graph_file):
    #     os.system("touch {}".format(process_graph_file))

    if not os.path.isdir(job_whole_path):
        print("create job dir")
        os.mkdir(job_whole_path)
        print("change owner")
        command = 'chown berni:berni -R {}'.format(job_whole_path)
        print("run copy command: {} ".format('cp -r {} {}/'.format(IMAGE_DIR, job_whole_path)))
        os.system('echo %s|sudo -S %s' % (SUDO_PASS, command))
    os.system('cp -r {} {}/'.format(IMAGE_DIR, job_whole_path))
    print("finished copy command")

    with open(process_graph_file, 'w+') as outfile:
        json.dump(content, outfile)


def run_job(content, job_id):

    job_whole_path = JOB_LOCATION + "/" + job_id

    if content:
        cp_job(content, job_id)

    command = './runlocal.sh {}'.format(job_whole_path)

    #if os.path.isdir(job_whole_path):
    #    os.system('cp -r {} {}'.format(job_whole_path + "/", LOCAL_NOW_OUT_DIR))

    # command = 'now run app.py --dir={}'.format(job_whole_path)
    print("run now command: {}".format(command))
    # os.system('echo %s|sudo -S %s' % (sudo_pass, command))
    os.system(command)

    print("after run now command")

    create_context_model(job_id)

        # os.mkdir(job_whole_path+"/.noworkflow")



    # command = 'cp -r {} {}'.format(LOCAL_NOW_OUT_DIR, job_whole_path+"/")

    # test = os.system('echo %s|sudo -S %s' % (sudo_pass, command))

    # command = 'rm -r {}'.format(LOCAL_NOW_OUT_DIR)

    # test = os.system('echo %s|sudo -S %s' % (sudo_pass, command))

    # print (test)
    # shutil.move(DOCKER_NOW_OUT_DIR, job_id+"/")



    # print (cm)


def get_python_detail(job_id):

    job_whole_path = JOB_LOCATION + "/" + job_id+"/now_modules"

    if not os.path.isfile(job_whole_path):
        return None
    else:
        file = open(job_whole_path, "r")
        modules = file.read()
        modules = modules.split('Name:')[1:]
        formated_modules = []
        for module in modules:
            module = module.split('Path:')[0].replace('\n', '').strip()
            formated_modules.append(module)
        return formated_modules



def get_env_info():
    # result = os.system('echo %s|sudo -S %s' % (sudoPassword, cmd))

    env_dir = {}

    #process = subprocess.Popen(DOCKER_VERSION.split(), stdout=subprocess.PIPE)
    #output, error = process.communicate()
    #output = str(output).split('\\n')[0].split("b'")[1]

    #env_dir["docker"] = {"docker_version": output,
    #                     "docker_base": DOCKER_BASE_IMAGE}

    out = cpuinfo.get_cpu_info()

    env_dir["hardware"] = {"cpu": out['brand']+" "+out["raw_arch_string"]}

    cmd = "lsb_release -a"

    process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    output = str(output).split('\\n')

    env_dir["os"] = {"os": output[1].split('\\t')[1]}

    return env_dir

@app.route('/')
def main():
    return render_template('index.html')


@app.route('/version')
def version():

    cm = get_system_cm()

    return jsonify(cm)


@app.route('/jobs', methods=["POST"])
def job():
    job_id = uuid.uuid4()

    content = request.get_json()
    print(content)
    cp_job(content, job_id)
    answer = {
        "job_id": str(job_id),
        "status": "submitted"
    }
    return jsonify(answer)


@app.route('/jobs/<job_id>/queue', methods=["PATCH"])
def job_queue(job_id):
    content = request.get_json()
    print(content)

    run_job(content, job_id)

    # cmp = compare_previous(job_id)

    answer ={
        "job_id": str(job_id),
        "status": "finished"
    }

    # if cmp:
    #    answer["validation"] = cmp

    return jsonify(answer)

@app.route('/jobs/<job_id>/diff', methods=["POST"])
def job_diff(job_id):
    content = request.get_json()
    print(content)

    compare_ids = []

    if 'job_ids' in content:
        compare_ids = content['job_ids']

    if 'job_id' in content:
        compare_ids = [content['job_id']]

    answer = {
        "job_id": str(job_id),
        "status": "finished",
        "validation": {}
    }

    for cmp_job_id in compare_ids:
        cmp = compare_jobs(job_id, cmp_job_id)

        if cmp:
            answer["validation"][cmp_job_id] = cmp
        else:
            answer["validation"][cmp_job_id] = None

    return jsonify(answer)

@app.route('/users/<username>/jobs', methods=["GET"])
def get_jobs(username):

    dirlist = [item for item in os.listdir(JOB_LOCATION) if
               os.path.isdir(os.path.join(JOB_LOCATION, item))]
    print(dirlist)

    return jsonify({'jobs': dirlist})


@app.route('/jobs/<job_id>', methods=["GET"])
def job_detail(job_id):
    job_whole_path = JOB_LOCATION + "/" + job_id

    if not os.path.isdir(job_whole_path):
        answer = {
            "job_id": str(job_id),
            "status": "submitted"
        }
        return jsonify(answer)

    # cmp = compare_previous(job_id)

    answer = {
        "cm": get_job_cm(job_id),
        "job_id": str(job_id),
        "status": "finished"
    }

    # if cmp:
    #     answer["validation"] = cmp

    # py_modules = get_python_detail(job_id)

    # if py_modules:
    #     answer["z_python-modules"] = py_modules

    return jsonify(answer)


if __name__ == '__main__':
    # compare_jobs("mynewjob", "mynewid")
    # create_context_model("testjob1")
    # print(get_python_detail("test"))
    # print(compare_previous("test"))
    # job_queue("test")
    # print(processgraph_add_hashes(PROCESS_GRAPH))
    # update_conf(PROCESS_GRAPH)
    # print(find_item(PROCESS_GRAPH, "left"))
    # get_jobs('asd')
    app.run(debug=True, port=5957)
