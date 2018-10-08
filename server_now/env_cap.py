import subprocess
import json
from hashlib import md5

OPENEO_API_VERSION = "0.0.2"

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
                           "left":652000,
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

SERVER_VERSION = 1

JOB_ID = 1

OS_ENV_CMD = "dpkg -l"
HW_ENV_CMD = "lspci -nnk"

def create_context_model(job_id):

   CODE_ENV_CMD = 'now show --dir={}'.format(str(job_id))

   context_model = {}

   # Retrieving data

   process = subprocess.Popen(OS_ENV_CMD.split(), stdout=subprocess.PIPE)
   output, error = process.communicate()

   os_hash = md5(output).hexdigest()

   process = subprocess.Popen(HW_ENV_CMD.split(), stdout=subprocess.PIPE)
   output, error = process.communicate()

   hw_hash = md5(output).hexdigest()

   process = subprocess.Popen(CODE_ENV_CMD.split(), stdout=subprocess.PIPE)
   output, error = process.communicate()

   output = str(output).split('\\n')

   trial = output[1].split(':')[1].strip()
   code_hash = output[5].split(':')[1].strip()

   # save to json

   context_model['backend_version'] = SERVER_VERSION
   context_model['openeo_api'] = OPENEO_API_VERSION
   context_model['process_graph'] = PROCESS_GRAPH
   context_model['job_id'] = JOB_ID
   context_model['os'] = os_hash
   context_model['hw'] = hw_hash
   context_model['code'] = {trial: code_hash}

   # context_model = json.loads(str(context_model))

   with open('context_model.json', 'w') as outfile:
      json.dump(context_model, outfile)

   print(context_model)
   return context_model
