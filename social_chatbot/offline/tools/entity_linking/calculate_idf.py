import codecs
import copy
import globals
import json
import logging
import multiprocessing
import os
import pickle
import re
import sys
import time

from collections import defaultdict
from commons.db.mongodb import MongoDB
from offline.tools.offline_tools import OfflineTools


class IDFPipeline(OfflineTools):

    def __init__(self, local_configure):

        super().__init__()

        self.local_configure = local_configure
        self.output_file = local_configure["output_file"]
        self.nworkers = int(local_configure["nworkers"])

        self.db_config = {
            'host': local_configure['host'],
            'port': int(local_configure['port']),
            'db_name': local_configure['db_name'],
            'input_collection_name': local_configure['input_collection_name'],
            'user': local_configure['user'],
            'pwd': local_configure['pwd'],
        }

        self.wrap_db = MongoDB(self.db_config['host'],
                               int(self.db_config['port']),
                               self.db_config['db_name'],
                               self.db_config['user'],
                               self.db_config['pwd'])
        self.input_collection = self.wrap_db.db[self.db_config['input_collection_name']]

        self.non_id_char = re.compile("([^\u4E00-\u9FD5a-zA-Z0-9])", re.U)
        self.non_char = re.compile("([^\u4E00-\u9FD5a-zA-Z0-9])")
        self.exclude_category = ["kuakua", "kuaixun"]

        self.system_logger = logging.getLogger("system_log")
        pass

    def execute(self):

        all_docs = []
        all_sources = list(self.input_collection.distinct("source"))
        for one_source in all_sources:
            all_category = list(self.input_collection.distinct("category", {"source":one_source}))
            for one_category in all_category:
                if one_category in self.exclude_category:
                    continue
                current_docs = list(self.input_collection.find({"source":one_source, "category":one_category}).distinct('_id'))
                all_docs.extend(current_docs)

        log_str = '# of docs found: %s' % len(all_docs)
        self.system_logger.info(log_str)
        print(log_str)
        if len(all_docs) == 0:
            return

        chunk_size = int(len(all_docs) / self.nworkers)
        chunks = []
        for i in range(0, len(all_docs), chunk_size):
            chunks.append(slice(i, i + chunk_size))

        log_str = '# of workers: %s' % self.nworkers
        self.system_logger.info(log_str)
        print(log_str)

        log_str = 'chunk size: %s' % len(chunks)
        self.system_logger.info(log_str)
        print(log_str)

        start = time.time()
        log_str = 'start processing'
        self.system_logger.info(log_str)
        print(log_str)

        all_term_collect = []
        all_term_dict = defaultdict(int)
        query = {}
        # Multi-processing
        pool = multiprocessing.Pool(processes=self.nworkers)
        for c in chunks:
            args = (self.db_config, query, all_docs[c],)
            res = pool.apply_async(process_chunk, args=args, )
            all_term_collect.append(res)
        pool.close()
        pool.join()

        log_str = '# of all_term_collect is %d:' % len(all_term_collect)
        self.system_logger.info(log_str)
        print(log_str)
        for index, one_collect in enumerate(all_term_collect):
            res_dict = one_collect.get()
            log_str = '# of [%d] one_collect is %d' % (index+1, len(res_dict))
            self.system_logger.info(log_str)
            print(log_str)
            for word, df_freq in res_dict.items():
                all_term_dict[word] += df_freq

        f = codecs.open(self.output_file, 'w', 'utf-8')
        f.write("%d\n" % len(all_docs))
        index = 1
        for word, df_freq in all_term_dict.items():
            f.write("%d\t%s\t%d\n" % (index, word, df_freq))
            index += 1
        f.close()

        log_str = 'processing time: ' + str(time.time() - start)
        self.system_logger.info(log_str)
        print(log_str)

        log_str = 'token size: %s' % len(all_term_dict)
        self.system_logger.info(log_str)
        print(log_str)


def process_one(data):

    try:
        text = data['title'] + '\n' + '\n'.join(data['content'])
        nlu = globals.nlp_processor.generate_query(text)
        return nlu
    except Exception:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        msg = 'unexpected error: %s | %s | %s' % \
            (exc_type, exc_obj, exc_tb.tb_lineno)
        print(msg)


def process_chunk(db_configure, query, ids):
    try:
        # MongoDB is not fork-safe:
        # http://api.mongodb.com/python/current/faq.html#is-pymongo-fork-safe
        wrap_db = MongoDB(db_configure["host"],
                          int(db_configure["port"]),
                          db_configure["db_name"],
                          db_configure['user'],
                          db_configure['pwd'])
        input_collection = wrap_db.db[db_configure["input_collection_name"]]

        df_dict = defaultdict(int)
        query['_id'] = {'$in': ids}
        response = input_collection.find(query)
        for data in response:
            word_exist = set()
            nlu = process_one(data)
            json = nlu.to_json()
            for i in json:
                ins = json[i]
                for item in ins['分词词性']:
                    elems = item.split("/")
                    word = elems[0].strip()
                    if word == "" or elems[-1] == "True" or elems[1] == "wp":
                        continue
                    word_exist.add(word)

            for word in word_exist:
                df_dict[word] += 1

        return df_dict
    except Exception:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        msg = 'unexpected error: %s | %s | %s' % (exc_type, exc_obj, exc_tb.tb_lineno)
        print(msg)
