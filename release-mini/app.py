from filter.filter import unzip_data, extract_sentinel_2_data, combine_bands, combine_same_utm, reproject, \
    merge_reprojected, transform_to_geotiff, write_output, clean_up, create_folder, read_parameters
from ndvi.ndvi import perform_ndvi, write_output as write_ndvi_output
from mintime.mintime import perform_min_time, write_output as write_min_time_output

import os, shutil
import datetime

import logging

LOG_FILE = "job.log"

logging.basicConfig(filename=LOG_FILE,
                            filemode='w',
                            format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                            datefmt=':%Y-%m-%d %H:%M:%S',
                            level=logging.INFO)

def clean_dir(folder):
    for the_file in os.listdir(folder):
        file_path = os.path.join(folder, the_file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(e)


def log(text):
    print(text)
    logging.info(text)


# convert
IN_VOLUME = "/data/job_data"
# OUT_VOLUME = "data/job_results"

CONFIG_FILE = "config/config.json"

process_graph = {
    "process_graph": {
        "process_id": "min_time",
        "args": {
            "imagery": {
                "process_id": "NDVI",
                "args": {
                    "imagery": {
                        "process_id": "filter_daterange",
                        "args": {
                            "imagery": {
                                "process_id": "filter_bbox",
                                "args": {
                                    "imagery": {
                                        "product_id": "s2a_prd_msil1c"
                                    },
                                    "left": 652000,
                                    "right": 672000,
                                    "top": 5161000,
                                    "bottom": 5181000,
                                    "srs": "EPSG:32632"
                                }
                            },
                            "from": "2017 -01 -01",
                            "to": "2017 -01 -08"
                        }
                    },
                    "red": "B04",
                    "nir": "B08"
                }
            }
        }
    }
}

TEMP_FOLDERS = {}  # tmp folder: tmp folder path -> deleted in the end
OUT_VOLUME = "/data/job_data"

OUT_FOLDER = create_folder(OUT_VOLUME, "template_id")
PARAMS = read_parameters(CONFIG_FILE)
ARGS = PARAMS["process_graph"]["args"]
OUT_EPSG = "4326"

NDVI_OUT_VOLUME = "/data"
NDVI_OUT_FOLDER = create_folder(OUT_VOLUME, "template_id_ndvi")

MINTIME_OUT_FOLDER = create_folder(OUT_VOLUME, "template_id_mintime")


def create_timestamp():
    return '{:%Y-%m-%d %H:%M:%S}'.format(datetime.datetime.now())


def run_graph():
    # Clean dir
    print("Start cleaning directory...")

    clean_dir(OUT_VOLUME)

    print("Finshed cleaning directory...")
    # Run filter

    print("Start Sentinel 2 data extraction process...")
    log("IN:filter_bbox:{}".format(create_timestamp()))
    log("IN:filter_daterange:{}".format(create_timestamp()))
    unzip_data(TEMP_FOLDERS, OUT_FOLDER, ARGS)
    extract_sentinel_2_data(TEMP_FOLDERS, OUT_FOLDER, ARGS, PARAMS)
    combine_bands(TEMP_FOLDERS, OUT_FOLDER)
    combine_same_utm(TEMP_FOLDERS, OUT_FOLDER)
    reproject(TEMP_FOLDERS, OUT_FOLDER, OUT_EPSG)
    merge_reprojected(TEMP_FOLDERS, OUT_FOLDER, PARAMS, OUT_EPSG)
    transform_to_geotiff(TEMP_FOLDERS, OUT_FOLDER, PARAMS)
    write_output(ARGS, OUT_EPSG, OUT_FOLDER)
    clean_up(TEMP_FOLDERS, OUT_FOLDER)
    log("OUT:filter_bbox:{}".format(create_timestamp()))
    log("OUT:filter_daterange:{}".format(create_timestamp()))

    print("Finished Sentinel 2 data extraction process.")

    # Run ndvi
    print("Start processing 'NDVI' ...")
    log("IN:NDVI:{}".format(create_timestamp()))
    NDVI_CONFIG_FILE = "/data/job_data/template_id/files.json"
    NDVI_PARAMS = read_parameters(NDVI_CONFIG_FILE)

    perform_ndvi(NDVI_PARAMS, NDVI_OUT_VOLUME, NDVI_OUT_FOLDER)
    write_ndvi_output(NDVI_PARAMS, NDVI_OUT_FOLDER)
    log("OUT:NDVI:{}".format(create_timestamp()))

    print("Finished 'NDVI' processing.")
    # Run min_time

    print("Start processing 'min_time' ...")
    log("IN:min_time:{}".format(create_timestamp()))
    MINTIME_CONFIG_FILE = "/data/job_data/template_id_ndvi/files.json"
    MINTIME_PARAMS = read_parameters(MINTIME_CONFIG_FILE)

    perform_min_time(MINTIME_OUT_FOLDER, NDVI_OUT_VOLUME, MINTIME_PARAMS)
    write_min_time_output(MINTIME_PARAMS, MINTIME_OUT_FOLDER)
    log("OUT:min_time:{}".format(create_timestamp()))
    print("Finished 'min_time' processing.")

    # Run convert
    # print("Start result data copy process...")
    # copy_data(CONFIG_FILE, IN_VOLUME, OUT_VOLUME)
    # print("Finish result data copy process.")


if __name__ == "__main__":
    run_graph()
