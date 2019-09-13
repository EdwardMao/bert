import codecs
import datetime
import logging
import multiprocessing
import os
import pymongo
import sys
import globals

from collections import defaultdict
from commons.db.mongodb import MongoDB
from offline.tools.offline_tools import OfflineTools


class EntityLinkingStatistic(OfflineTools):

    def __init__(self, local_configure):

        super().__init__()
        self.system_logger = logging.getLogger("system_log")
        self.nworkers = int(local_configure['nworkers'])
        self.db_config = {
            'host': local_configure['host'],
            'port': int(local_configure['port']),
            'user': local_configure['user'],
            'pwd': local_configure['pwd'],
            'input_db_name': local_configure['input_db_name'],
            'sentence_collection_name': local_configure['sentence_collection_name']
        }

        self.wrap_processed_db = MongoDB(self.db_config["host"],
                                         self.db_config["port"],
                                         self.db_config['input_db_name'],
                                         self.db_config['user'],
                                         self.db_config['pwd'])
        self.sentence_collection = self.wrap_processed_db.db[self.db_config['sentence_collection_name']]
        self.output_file = local_configure['output_file']

        pass

    def execute(self):

        all_sentence_ids = []
        sys.stdout.write("Collecting sentence ids\n")
        try:
            all_sentence_ids = self.sentence_collection.find({"entity_len": {"$gt": 0}}).distinct("_id")
        except Exception:
            # TO-DO: fix the following error:
            # pymongo.errors.OperationFailure: distinct too big, 16mb cap
            all_sentence_count = self.sentence_collection.find({"entity_len": {"$gt": 0}}).count()
            index = 1
            for i in self.sentence_collection.find({"entity_len": {"$gt": 0}}):
                sys.stdout.write("%d / %d\r" % (index, all_sentence_count))
                all_sentence_ids.append(i['_id'])
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
        self.system_logger.info('parent pid: %s' % os.getpid())
        self.system_logger.info('processing...')

        # Multi-processing
        entity_info_from_different_thread = []
        pool = multiprocessing.Pool(processes=self.nworkers)
        for c in chunks:
            args = (self.db_config, all_sentence_ids[c])
            res = pool.apply_async(process_chunk, args=args, )
            entity_info_from_different_thread.append(res)
        pool.close()
        pool.join()

        log_str = 'Start merging!'
        self.system_logger.info(log_str)
        print(log_str)

        final_entity_info = defaultdict()
        for one_res in entity_info_from_different_thread:
            token_info = one_res.get()
            for entity_key, sentence_list in token_info.items():
                if entity_key not in final_entity_info:
                    final_entity_info[entity_key] = set()
                final_entity_info[entity_key].update(set(sentence_list))

        sorted_entity_info = sorted(final_entity_info.items(), key=lambda x:len(x[1]), reverse=True)
        g = codecs.open(self.output_file + ".details", 'w', 'utf-8')
        f = codecs.open(self.output_file, 'w', 'utf-8')
        for entity_key, sentence_list in sorted_entity_info:
            f.write("%s\t%d\n" % (entity_key, len(sentence_list)))
            g.write(entity_key + "\n")
            for sentence_id in sentence_list:
                g.write(sentence_id + "\n")
            g.write("\n")
        f.close()
        g.close()


def process_chunk(db_config, ids):

    try:
        wrap_processed_db = MongoDB(db_config["host"],
                                    db_config["port"],
                                    db_config['input_db_name'],
                                    db_config['user'],
                                    db_config['pwd'])
        sentence_collection = wrap_processed_db.db[db_config['sentence_collection_name']]
        sentences = sentence_collection.find({"_id": {"$in": ids}})

        entity2sentence_candidates = defaultdict()
        for one_sentence in sentences:

            sentence_entity = {}
            for entity_mention in one_sentence["实体链接"]:
                entity_text = entity_mention["entity_mention"]
                entity_id = None
                if "entity" in entity_mention and entity_mention["entity"] is not None:
                    entity_id = entity_mention["entity"]["kbid"]
                if entity_id is None:
                    continue
                sentence_entity[entity_id] = entity_text

            for id, text in sentence_entity.items():
                entity_key = id + "_" + text
                if entity_key not in entity2sentence_candidates:
                    entity2sentence_candidates[entity_key] = []
                entity2sentence_candidates[entity_key].append(one_sentence["_id"])

        return entity2sentence_candidates
    except Exception:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        msg = 'unexpected error: %s | %s | %s' % \
              (exc_type, exc_obj, exc_tb.tb_lineno)
        print(msg)
