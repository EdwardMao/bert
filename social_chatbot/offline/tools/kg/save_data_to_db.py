import bs4
import codecs
import json
import logging
import os
import re
import sys

from bs4 import BeautifulSoup
from collections import defaultdict
from commons.db.mongodb import MongoDB
from commons.utils import get_files
from offline.tools.offline_tools import OfflineTools


def update_time_pattern(time_str):
    new_elems = []
    for elem in time_str.split("-"):
        if len(elem) == 1:
            new_elems.append("0" + elem)
        else:
            new_elems.append(elem)
    return "-".join(new_elems)


def convert_date_to_int(date_str):

    date_str = date_str.replace("-", "")
    if len(date_str) != 8:
        sys.stderr.write("Data pattern error [%s]\n"%date_str)
        return "19700101"
    else:
        return int(date_str)


class SaveEntity2DB(OfflineTools):

    def __init__(self, local_configure, global_configure):
        super().__init__()
        self.global_configure = global_configure
        self.local_configure = local_configure
        self.db_name = local_configure["db_name"]
        self.collection_name = local_configure["collection_name"]
        self.data_dir = local_configure["data_dir"]
        self.db_interface = MongoDB(db_server_ip="10.93.128.143", db_server_port=27017, database_name=self.db_name)
        self.non_id_char = re.compile("([^\u4E00-\u9FD5a-zA-Z0-9])", re.U)
        self.system_logger = logging.getLogger("system_log")
        pass

    def execute(self):
        for source, data_path in self.data_dir.items():
            if source == "douban_movie":
                self.process_douban_movie(data_path)
            elif source == "qq_music":
                self.process_qq_music(data_path)
            else:
                sys.stdout.write("[%s] is not supported at this moment!"%source)
                continue

    def is_han(self, text):
        return any('\u4e00' <= char <= '\u9fff' for char in text)

    def process_douban_movie(self, data_path):

        current_category_dirs = os.listdir(data_path)

        for category in current_category_dirs:
            if category in ["configures", "errors", "category_list_json"]:
                continue

            category_dir = os.path.join(data_path, category) + "/"

            log_str = "\nProcessing: %s\n" % category_dir
            sys.stdout.write(log_str)
            self.system_logger.info(log_str)

            all_json_file = get_files(category_dir, r'.*json')
            for index, filename in enumerate(all_json_file):

                sys.stdout.write("%d / %d\r" % (index, len(all_json_file)))

                json_str = codecs.open(filename, 'r', 'utf-8').read()
                json_obj = json.loads(json_str)
                json_obj["_id"] = "douban_" + json_obj["id"]
                json_obj["web_category"] = category
                json_obj["entity_type"] = "Movie"

                try:
                    self.db_interface.save_to_mongodb(self.collection_name, json_obj)
                except:
                    output_str = json.dumps(json_obj)
                    self.system_logger.info("Errors writing following object into DB: \n" + output_str + "\n")
                    sys.stderr.write("Error writing object into DB\n")
                    sys.exit()

    def process_qq_music(self, data_path):

        current_category_dirs = os.listdir(data_path)

        for category in current_category_dirs:
            if category not in ["内地","台湾","日本","新加坡","泰国","韩国","香港","马来西亚"]:
                continue

            category_dir = os.path.join(data_path, category) + "/"
            sys.stdout.write("\nProcessing: %s\n" % category_dir)
            all_json_file = get_files(category_dir, r'.*_albums.json')

            for index, filename in enumerate(all_json_file):

                sys.stdout.write("%d / %d\r" % (index, len(all_json_file)))

                singer_filename = filename.replace("_albums", "")
                if not os.path.exists(singer_filename):
                    sys.stdout.write("\n[%s] does not exist in directory [%s]\n"%(singer_filename, category_dir))
                    continue
                json_str = codecs.open(singer_filename, 'r', 'utf-8').read()
                json_obj = json.loads(json_str)
                json_obj["_id"] = "qq_music_singer_" + json_obj["singer_mid"]
                json_obj["entity_type"] = "singer"

                try:
                    self.db_interface.save_to_mongodb(self.collection_name, json_obj)
                except:
                    output_str = json.dumps(json_obj)
                    self.system_logger.info("Errors writing following object into DB: \n" + output_str + "\n")
                    sys.stderr.write("Error writing object into DB\n")
                    sys.exit()

