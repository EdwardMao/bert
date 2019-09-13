import codecs
import copy
import globals
import json
import logging
import math
import multiprocessing
import os
import pickle
import re
import shutil
import sys
import time

from collections import defaultdict
from commons.db.mongodb import MongoDB
from commons.utils import get_date_str, get_gb_bytes, get_files
from commons.warehouse.search_warehouse import convert_dict_to_bytes
from commons.warehouse.search_warehouse import load_bin_index_file
from commons.warehouse.search_warehouse import recover_bytes_to_dict
from commons.warehouse.search_warehouse import write_bin_index_file
from offline.tools.offline_tools import OfflineTools


class InvertedIndexPipeline(OfflineTools):

    def __init__(self, local_configure):

        super().__init__()
        self.system_logger = logging.getLogger("system_log")
        self.local_configure = local_configure

        self.db_config = {
            'host': local_configure['host'],
            'port': int(local_configure['port']),
            'processed_db_name': local_configure["processed_db_name"],
            'sentence_collection_name': local_configure["sentence_collection_name"],
            'user': local_configure['user'],
            'pwd': local_configure['pwd'],
        }

        self.wrap_processed_db = MongoDB(self.db_config["host"],
                                         self.db_config["port"],
                                         self.db_config['processed_db_name'],
                                         self.db_config['user'],
                                         self.db_config['pwd'])
        self.sentence_collection = self.wrap_processed_db.db[self.db_config['sentence_collection_name']]

        self.max_index_file_size = int(self.local_configure["max_index_file_size"])
        self.nworkers = int(self.local_configure["nworkers"])

        self.daily_update = bool(local_configure["daily_update"])
        if self.daily_update or len(local_configure['date_after']) != 8:
            instead_date = get_date_str(0)
            self.date_after = int(instead_date)
        else:
            self.date_after = int(local_configure['date_after'])
            
        self.idf_file = self.local_configure["idf_file"]
        self.tmp_dir = local_configure["tmp_dir"]
        if not os.path.exists(self.tmp_dir):
            os.mkdir(self.tmp_dir)
        else:
            shutil.rmtree(self.tmp_dir)
            os.mkdir(self.tmp_dir)

        self.output_dir = local_configure["output_dir"]
        if not os.path.exists(self.output_dir):
            os.mkdir(self.output_dir)

        pass

    def execute(self):

        all_sentence_ids = []
        sys.stdout.write("Collecting sentence ids\n")
        search_query = {"entity_len": {"$gt": 0}, "news_date": {"$gte": self.date_after}}
        log_str = 'searching query' + str(search_query)
        self.system_logger.info(log_str)
        print(log_str)
        try:
            all_sentence_ids = self.sentence_collection.find(search_query).distinct("sentence_index")
        except Exception:
            # TO-DO: fix the following error:
            # pymongo.errors.OperationFailure: distinct too big, 16mb cap
            all_sentence_count = self.sentence_collection.find(search_query).count()
            index = 1
            for one_sentence in self.sentence_collection.find(search_query, no_cursor_timeout=True):
                sys.stdout.write("%d / %d\r" % (index, all_sentence_count))
                all_sentence_ids.append(one_sentence['sentence_index'])
                index += 1

        if len(all_sentence_ids) == 0:
            return

        log_str = '# of sentences found: %s' % len(all_sentence_ids)
        self.system_logger.info(log_str)
        print(log_str)

        chunk_size = int(len(all_sentence_ids) / self.nworkers)
        if chunk_size == 0:
            chunk_size = len(all_sentence_ids)

        log_str = '# of workers: %s' % self.nworkers
        self.system_logger.info(log_str)
        print(log_str)

        log_str = 'chunk size: %s' % chunk_size
        self.system_logger.info(log_str)
        print(log_str)

        chunks = []
        for i in range(0, len(all_sentence_ids), chunk_size):
            chunks.append(slice(i, i + chunk_size))

        log_str = 'parent pid: %s\nprocessing...' % os.getpid()
        self.system_logger.info(log_str)
        print(log_str)

        # Multi-processing
        pool = multiprocessing.Pool(processes=self.nworkers)
        thread_id = 0
        for c in chunks:
            args = (self.db_config, self.idf_file, all_sentence_ids[c], self.tmp_dir, thread_id)
            thread_id += 1
            pool.apply_async(process_chunk, args=args, )
        pool.close()
        pool.join()

        current_all_index_files = get_files(self.output_dir, r'.*bin')
        if len(current_all_index_files) == 1:
            current_source_template = current_all_index_files[0].replace(".bin", "")
        else:
            files_date = {}
            for filename in current_all_index_files:
                files_date[filename] = int(os.path.basename(filename)[:8])
            sorted_filenames = sorted(files_date.items(), key=lambda x: x[1], reverse=True)
            current_source_template = sorted_filenames[0][0].replace(".bin", "")

        source_template = self.output_dir + "/" + get_date_str(0) + "_index"
        shutil.copy(current_source_template + ".bin", source_template + ".bin")
        shutil.copy(current_source_template + ".index", source_template + ".index")

        log_str = 'Soruce template is [%s]' % source_template
        self.system_logger.info(log_str)
        print(log_str)

        target_templates = []
        for tid in range(0, thread_id):
            target_templates.append(self.tmp_dir + "/thread_" + str(tid) + "_index")

        log_str = 'Target template is %s' % str(target_templates)
        self.system_logger.info(log_str)
        print(log_str)

        log_str = 'Start merging!'
        self.system_logger.info(log_str)
        print(log_str)
        merge_index_in_memory(source_template, target_templates)

        # shutil.rmtree(self.tmp_dir)


def merge_index_in_memory(target_index, source_files):

    updated_index = defaultdict()
    for one_source_file in source_files:

        log_str = 'Loading %s' % one_source_file
        logging.getLogger("system_log").info(log_str)
        print(log_str)

        source_index_file = one_source_file + ".index"
        source_index_bin = one_source_file + ".bin"
        source_index2pos = load_bin_index_file(source_index_file)
        source_bin_handle = open(source_index_bin, 'rb')

        for word_id, word_info in source_index2pos.items():

            source_file_index = word_info[0]
            source_length = word_info[1]
            source_bin_handle.seek(source_file_index)
            load_bytes = source_bin_handle.read(source_length)
            source_index_info = recover_bytes_to_dict(load_bytes)

            if word_id in updated_index:
                for sentence_id, term_freq in source_index_info.items():
                    if sentence_id in updated_index[word_id]:
                        log_str = "Warning: Sentence [%d] is already in word [%d]'s index. "
                        logging.getLogger("system_log").info(log_str)
                        print(log_str)
                    else:
                        updated_index[word_id][sentence_id] = term_freq
            else:
                updated_index[word_id] = source_index_info

    log_str = 'Merging updated index to current index %s' % target_index
    logging.getLogger("system_log").info(log_str)
    print(log_str)

    old_index_file = target_index + ".index"
    old_bin_file = target_index + ".bin"
    old_bin_handle = None
    if os.path.exists(old_bin_file):
        old_bin_handle = open(old_bin_file, 'rb')
    old_index2pos = load_bin_index_file(old_index_file)

    new_index_file = old_index_file + ".tmp"
    new_bin_file = old_bin_file + ".tmp"
    new_index2pos = defaultdict()
    new_bin_handle = open(new_bin_file, 'wb')

    for word_id, word_info in updated_index.items():
        if word_id in old_index2pos:
            old_file_index = old_index2pos[word_id][0]
            old_length = old_index2pos[word_id][1]
            old_bin_handle.seek(old_file_index)
            load_bytes = old_bin_handle.read(old_length)
            old_index_info = recover_bytes_to_dict(load_bytes)

            old_index_info.update(word_info)
            save_bytes = convert_dict_to_bytes(old_index_info)
        else:
            save_bytes = convert_dict_to_bytes(word_info)

        word_file_index = new_bin_handle.tell()
        word_info_length = len(save_bytes)
        new_bin_handle.write(save_bytes)
        new_index2pos[word_id] = (word_file_index, word_info_length)

    no_update_token = set(old_index2pos.keys()).difference(set(updated_index.keys()))
    for word_id in no_update_token:
        word_file_index = old_index2pos[word_id][0]
        word_info_length = old_index2pos[word_id][1]
        old_bin_handle.seek(word_file_index)
        load_bytes = old_bin_handle.read(word_info_length)

        new_word_file_index = new_bin_handle.tell()
        new_bin_handle.write(load_bytes)
        new_index2pos[word_id] = (new_word_file_index, word_info_length)

    new_bin_handle.close()
    write_bin_index_file(new_index2pos, new_index_file)

    shutil.move(new_bin_file, old_bin_file)
    shutil.move(new_index_file, old_index_file)


def merge_index_in_disk(target_index, source_files):

    for one_source_file in source_files:

        log_str = 'Merging %s' % one_source_file
        logging.getLogger("system_log").info(log_str)
        print(log_str)

        old_index_file = target_index + ".index"
        old_bin_file = target_index + ".bin"
        old_bin_handle = None
        if os.path.exists(old_bin_file):
            old_bin_handle = open(old_bin_file, 'rb')
        old_index2pos = load_bin_index_file(old_index_file)

        new_index_file = old_index_file + ".tmp"
        new_bin_file = old_bin_file + ".tmp"
        new_index2pos = defaultdict()
        new_bin_handle = open(new_bin_file, 'wb')

        source_index_file = one_source_file + ".index"
        source_index_bin = one_source_file + ".bin"
        source_index2pos = load_bin_index_file(source_index_file)
        source_bin_handle = open(source_index_bin, 'rb')

        for word_id, word_info in source_index2pos.items():

            source_file_index = word_info[0]
            source_length = word_info[1]
            source_bin_handle.seek(source_file_index)
            load_bytes = source_bin_handle.read(source_length)
            source_index_info = recover_bytes_to_dict(load_bytes)

            if word_id in old_index2pos:

                old_file_index = old_index2pos[word_id][0]
                old_length = old_index2pos[word_id][1]
                old_bin_handle.seek(old_file_index)
                load_bytes = old_bin_handle.read(old_length)
                old_index_info = recover_bytes_to_dict(load_bytes)

                old_index_info.update(source_index_info)
                save_bytes = convert_dict_to_bytes(old_index_info)
            else:
                save_bytes = convert_dict_to_bytes(source_index_info)

            word_file_index = new_bin_handle.tell()
            word_info_length = len(save_bytes)
            new_bin_handle.write(save_bytes)
            new_index2pos[word_id] = (word_file_index, word_info_length)

        no_update_token = set(old_index2pos.keys()).difference(set(source_index2pos.keys()))
        for word_id in no_update_token:
            word_file_index = old_index2pos[word_id][0]
            word_info_length = old_index2pos[word_id][1]
            old_bin_handle.seek(word_file_index)
            load_bytes = old_bin_handle.read(word_info_length)

            new_word_file_index = new_bin_handle.tell()
            new_bin_handle.write(load_bytes)
            new_index2pos[word_id] = (new_word_file_index, word_info_length)

        new_bin_handle.close()
        write_bin_index_file(new_index2pos, new_index_file)

        shutil.move(new_bin_file, old_bin_file)
        shutil.move(new_index_file, old_index_file)


def update_index_files(index_db_candidates, index_file, bin_file):

    old_index_file = index_file
    old_bin_file = bin_file

    new_index_file = index_file + ".tmp"
    new_bin_file = bin_file + ".tmp"

    old_bin_handle = None
    if os.path.exists(old_bin_file):
        old_bin_handle = open(old_bin_file, 'rb')
    old_index2pos = load_bin_index_file(old_index_file)

    new_bin_handle = open(new_bin_file, 'wb')
    new_index2pos = defaultdict()

    for word_id, sentence_tf_dict in index_db_candidates.items():
        if word_id in old_index2pos:
            word_file_index = old_index2pos[word_id][0]
            word_info_length = old_index2pos[word_id][1]
            old_bin_handle.seek(word_file_index)
            load_bytes = old_bin_handle.read(word_info_length)
            old_index_info = recover_bytes_to_dict(load_bytes)
            old_index_info.update(sentence_tf_dict)
            save_bytes = convert_dict_to_bytes(old_index_info)
        else:
            save_bytes = convert_dict_to_bytes(sentence_tf_dict)

        word_file_index = new_bin_handle.tell()
        word_info_length = len(save_bytes)
        new_bin_handle.write(save_bytes)
        new_index2pos[word_id] = (word_file_index, word_info_length)

    no_update_token = set(old_index2pos.keys()).difference(set(index_db_candidates.keys()))
    for word_id in no_update_token:
        word_file_index = old_index2pos[word_id][0]
        word_info_length = old_index2pos[word_id][1]
        old_bin_handle.seek(word_file_index)
        load_bytes = old_bin_handle.read(word_info_length)

        new_word_file_index = new_bin_handle.tell()
        new_bin_handle.write(load_bytes)
        new_index2pos[word_id] = (new_word_file_index, word_info_length)

    new_bin_handle.close()
    write_bin_index_file(new_index2pos, new_index_file)

    shutil.move(new_bin_file, old_bin_file)
    shutil.move(new_index_file, old_index_file)


def process_chunk(db_config, idf_file, ids, tmp_dir, thread_id):

    try:

        lines = codecs.open(idf_file, 'r', 'utf-8').read().splitlines()
        token_idf_dict = defaultdict()
        all_docs = int(lines[0].strip())
        for line in lines[1:]:
            elems = line.strip().split("\t")
            if len(elems) != 3:
                log_str = "Format error in idf file [%s]!\n" % line
                print(log_str.strip())
                continue
            df = int(elems[2])
            idf = math.log((all_docs - df + 0.5) / (0.5 + df))
            token_idf_dict[elems[1]] = (int(elems[0]), max(0.0, idf))

        wrap_processed_db = MongoDB(db_config["host"],
                                    db_config["port"],
                                    db_config['processed_db_name'],
                                    db_config['user'],
                                    db_config['pwd'])
        sentence_collection = wrap_processed_db.db[db_config['sentence_collection_name']]
        sentences = sentence_collection.find({"sentence_index": {"$in": ids}}, no_cursor_timeout=True)

        index_db_candidates = defaultdict()
        for one_sentence in sentences:
            words = []
            token_tf = defaultdict(int)
            for item in one_sentence['分词词性']:
                elems = item.split("/")
                word = elems[0]
                pos = elems[1]
                stop_word = elems[-1]
                if len(word.strip()) == 0 or pos == "wp" or stop_word == "True" or word not in token_idf_dict:
                    continue
                word_id = token_idf_dict[word][0]
                words.append(word_id)
                token_tf[word_id] += 1

            for word_id, tf in token_tf.items():
                if word_id not in index_db_candidates:
                    index_db_candidates[word_id] = {}
                index_db_candidates[word_id][one_sentence["sentence_index"]] = tf

            if get_gb_bytes(sys.getsizeof(index_db_candidates)) >= 2:
                print("Saving index due to big size at thread ", thread_id)
                current_index_file = tmp_dir + "/thread_" + str(thread_id) + "_index.index"
                current_bin_file = tmp_dir + "/thread_" + str(thread_id) + "_index.bin"
                update_index_files(index_db_candidates, current_index_file, current_bin_file)
                index_db_candidates.clear()

        if len(index_db_candidates) > 0:
            print("Finish indexing from thread ", thread_id)
            current_index_file = tmp_dir + "/thread_" + str(thread_id) + "_index.index"
            current_bin_file = tmp_dir + "/thread_" + str(thread_id) + "_index.bin"
            update_index_files(index_db_candidates, current_index_file, current_bin_file)
            index_db_candidates.clear()

    except Exception:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        msg = 'unexpected error: %s | %s | %s' % \
              (exc_type, exc_obj, exc_tb.tb_lineno)
        print(msg)
