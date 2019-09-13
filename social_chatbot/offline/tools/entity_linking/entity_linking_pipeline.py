import codecs
import json
import logging
import multiprocessing
import os
import pymongo
import shutil
import sys
import globals

from commons.db.mongodb import MongoDB
from commons.utils import get_date_str, get_files
from offline.tools.kg.document_category_classifier import SportNewsCategoryClassifier
from offline.tools.offline_tools import OfflineTools


class EntityLinkingPipeline(OfflineTools):

    def __init__(self, local_configure):

        super().__init__()
        self.system_logger = logging.getLogger("system_log")

        self.nworkers = int(local_configure['nworkers'])

        self.save_batch_size = int(local_configure["save_batch_size"])
        self.insert_batch_size = int(local_configure["insert_batch_size"])

        self.db_config = {
            'host': local_configure['host'],
            'port': int(local_configure['port']),
            'input_db_name': local_configure['input_db_name'],
            'article_collection_name': local_configure['article_collection_name'],
            'output_db_name': local_configure['output_db_name'],
            'sentence_collection_name': local_configure['sentence_collection_name'],
            'user': local_configure['user'],
            'pwd': local_configure['pwd'],
        }
        self.input_source_category = local_configure['input_source_category']

        self.daily_update = bool(local_configure["daily_update"])
        if self.daily_update or len(local_configure['date_after']) != 8:
            instead_date = get_date_str(0)
            self.date_after = int(instead_date)
        else:
            self.date_after = int(local_configure['date_after'])

        self.tmp_dir = local_configure["tmp_dir"]
        if not os.path.exists(self.tmp_dir):
            os.mkdir(self.tmp_dir)
        else:
            shutil.rmtree(self.tmp_dir)
            os.mkdir(self.tmp_dir)

        self.sport_category_filename = globals.data_root + local_configure["sport_category_file"]

        pass

    def execute(self):
        self.process()
        pass

    def process(self):

        log_str = 'searching...'
        self.system_logger.info(log_str)
        print(log_str)

        input_db = MongoDB(self.db_config['host'],
                           self.db_config['port'],
                           self.db_config['input_db_name'],
                           self.db_config['user'],
                           self.db_config['pwd'])

        input_collection = input_db.db[self.db_config['article_collection_name']]

        all_docs = []
        for source_category in self.input_source_category:
            elems = source_category.split("_")
            source = elems[0]
            category = elems[1]
            if category == "all":
                query = {"source": source, "date": {"$gte": self.date_after}}
            else:
                query = {"source": source, "category": category, "date": {"$gte": self.date_after}}

            log_str = 'searching query' + str(query)
            self.system_logger.info(log_str)
            print(log_str)

            try:
                ids = input_collection.find(query).distinct('_id')
            except pymongo.errors.OperationFailure:
                # TO-DO: fix the following error:
                # pymongo.errors.OperationFailure: distinct too big, 16mb cap
                ids = [i['_id'] for i in input_collection.find(query)]

            all_docs.extend(ids)

        log_str = '# of docs found: %s' % len(all_docs)
        self.system_logger.info(log_str)
        print(log_str)

        if len(all_docs) == 0:
            return

        chunk_size = int(len(all_docs) / self.nworkers)
        if chunk_size == 0:
            chunk_size = len(all_docs)

        output_db = MongoDB(self.db_config['host'],
                            self.db_config['port'],
                            self.db_config['output_db_name'],
                            self.db_config['user'],
                            self.db_config['pwd']
                            )
        sentence_collection = output_db.db[self.db_config['sentence_collection_name']]
        current_count = sentence_collection.count()
        if current_count > 0:
            current_count -= 1

        log_str = '# of workers: %s\n chunk size: %s \n' % (self.nworkers, chunk_size)
        self.system_logger.info(log_str)
        print(log_str)

        chunks = []
        for i in range(0, len(all_docs), chunk_size):
            chunks.append(slice(i, i+chunk_size))

        log_str = '# parent pid: %s\n processing...\n' % os.getpid()
        self.system_logger.info(log_str)
        print(log_str)

        # Multi-processing
        pool = multiprocessing.Pool(processes=self.nworkers)
        thread_id = 0
        for c in chunks:
            args = (self.db_config,
                    self.sport_category_filename,
                    {},
                    all_docs[c],
                    self.save_batch_size,
                    self.tmp_dir,
                    thread_id)
            thread_id += 1
            pool.apply_async(process_chunk, args=args,)
        pool.close()
        pool.join()

        log_str = 'start merging...'
        self.system_logger.info('start merging...')
        print(log_str)

        # merge some information
        current_index = current_count + 1
        current_sentence_length = 0
        current_sentence_number = 0
        all_tmp_files = get_files(self.tmp_dir, r".*json")

        group_insert = []
        for index, one_file in enumerate(all_tmp_files):
            sys.stdout.write("%d / %d\r" % (index, len(all_tmp_files)))
            json_str = codecs.open(one_file, 'r', 'utf-8').read()
            insert_sentences = json.loads(json_str)
            for one_sentence in insert_sentences:
                _length = int(one_sentence["sentence_length"])
                one_sentence["sentence_index"] = current_index
                group_insert.append(one_sentence)
                current_index += 1
                current_sentence_length += _length
            current_sentence_number += len(insert_sentences)
            if len(group_insert) == self.insert_batch_size:
                sentence_collection.insert(group_insert)
                group_insert.clear()

        if len(group_insert) > 0:
            sentence_collection.insert(group_insert)
            group_insert.clear()

        avg_length_entry = list(sentence_collection.find({"_id": "avg_length"}))
        if len(avg_length_entry) == 1:
            saved_sentence_length = avg_length_entry[0]["current_sentence_length"]
            saved_sentence_number = avg_length_entry[0]["current_sentence_number"]
            current_sentence_length += saved_sentence_length
            current_sentence_number += saved_sentence_number
            avg_length = float(current_sentence_length / current_sentence_number)
            find_query = {"_id": "avg_length"}
            update_query = {"$set": {"current_sentence_length": current_sentence_length,
                                     "current_sentence_number": current_sentence_number,
                                     "avg_length": avg_length}}
            sentence_collection.update_one(find_query, update_query)
        else:
            avg_length = float(current_sentence_length / current_sentence_number)
            sentence_collection.insert({"_id": "avg_length",
                                        "current_sentence_length": current_sentence_length,
                                        "current_sentence_number": current_sentence_number,
                                        "avg_length": avg_length})

        if current_index != sentence_collection.count():
            self.system_logger.error('sentence index is not equal to the number of sentence.\n')
            self.system_logger.error('current max sentence index is [%d], but current all sentence number is [%d].\n' %
                                     (current_index - 1, sentence_collection.count() - 1))

        log_str = 'start indexing...'
        self.system_logger.info('start indexing...')
        print("\n", log_str)

        sentence_collection.create_index('docid')
        sentence_collection.create_index('import_date')
        sentence_collection.create_index('news_date')
        sentence_collection.create_index('entity_len')
        sentence_collection.create_index('sentence_index')
        sentence_collection.create_index('sentence_length')
        sentence_collection.create_index('sentence_position')
        key = [('entity_set', 1)]
        pfe = {'entity_set': {'$exists': True}}
        sentence_collection.create_index(key, partialFilterExpression=pfe)
        key = [('category_set', 1)]
        pfe = {'category_set': {'$exists': True}}
        sentence_collection.create_index(key, partialFilterExpression=pfe)

        log_str = 'all done'
        self.system_logger.info('all done')
        print(log_str)

        shutil.rmtree(self.tmp_dir)


def process_document_body(one_document_content):
    try:
        text = '\n'.join(one_document_content)
        document_query = globals.nlp_processor.generate_query(text)
        return document_query
    except Exception:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        msg = 'unexpected error: %s | %s | %s' % \
            (exc_type, exc_obj, exc_tb.tb_lineno)
        print(msg)
        print(one_document_content)
        return None


def process_title(title_text):

    try:
        return globals.nlp_processor.generate_query(title_text)
    except Exception:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        msg = 'unexpected error: %s | %s | %s' % \
            (exc_type, exc_obj, exc_tb.tb_lineno)
        print(msg)


def process_chunk(db_config, sport_category_filename, query, doc_ids, batch_size, tmp_dir, thread_id):
    try:

        sport_category_classifier = SportNewsCategoryClassifier(sport_category_filename)

        # MongoDB is not fork-safe:
        # http://api.mongodb.com/python/current/faq.html#is-pymongo-fork-safe
        input_db = MongoDB(db_config['host'],
                           db_config['port'],
                           db_config['input_db_name'],
                           db_config['user'],
                           db_config['pwd']
                           )
        article_collection = input_db.db[db_config['article_collection_name']]

        output_db = MongoDB(db_config['host'],
                            db_config['port'],
                            db_config['output_db_name'],
                            db_config['user'],
                            db_config['pwd'])

        sentence_collection = output_db.db[db_config['sentence_collection_name']]

        query['_id'] = {'$in': doc_ids}
        response = article_collection.find(query, no_cursor_timeout=True)

        batch_number = 0
        to_insert = []
        all_inserted_sentence = 0
        for one_document in response:

            if len(one_document['content']) == 0:
                continue

            one_document_content = []
            for line in one_document['content']:
                if len(line.strip()) > 0:
                    one_document_content.append(line.strip())
            if len(one_document_content) == 0:
                continue

            docid = one_document['_id']
            search_query = {"docid": docid}
            if len(list(sentence_collection.find(search_query))) > 0:
                continue

            # process title
            title = one_document['title']
            title_query = process_title(title)

            # process document body
            body_query = process_document_body(one_document_content)

            category_result = sport_category_classifier.get_category(title_query.full_entity_ids,
                                                                     body_query,
                                                                     one_document['source'],
                                                                     one_document['category'])

            # generate a sentence from query
            sentence_to_insert = {"_id": '%s_%s' % (docid, 1)}
            search_query = {"_id": sentence_to_insert["_id"]}
            if len(list(sentence_collection.find(search_query))) > 0:
                continue

            entity_set = set(title_query.full_entity_ids)
            if len(entity_set) == 0:
                continue

            sentence_length = 0
            sentence_tokens = []
            for sentence in title_query.sentence_list:
                sentence_length += sentence.sentence_length
                for token in sentence.token_list:
                    sentence_tokens.append(token.original_text + "/" +
                                           str(token.pos) + "/" +
                                           str(token.ner) + "/" +
                                           str(token.is_stop_word))

            sentence_to_insert['分词词性'] = sentence_tokens
            sentence_to_insert['docid'] = docid
            sentence_to_insert['source'] = one_document['source']
            sentence_to_insert['category'] = one_document['category']
            sentence_to_insert['news_date'] = int(one_document['date'])
            sentence_to_insert['import_date'] = int(one_document['import_date'])
            sentence_to_insert['raw_sentence'] = title
            sentence_to_insert['sentence_length'] = sentence_length
            sentence_to_insert['sentence_position'] = 1
            sentence_to_insert['token_number'] = len(sentence_tokens)
            sentence_to_insert['entity_set'] = list(entity_set)
            sentence_to_insert['entity_len'] = len(entity_set)
            sentence_to_insert["topic_category"] = category_result.res

            to_insert.append(sentence_to_insert)

            if body_query is None:
                continue
            # generate sentences from body
            for sentence_index, sentence in enumerate(body_query.sentence_list):

                sentence_to_insert = {"_id": '%s_%s' % (docid, sentence_index + 2)}
                search_query = {"_id": sentence_to_insert["_id"]}
                if len(list(sentence_collection.find(search_query))) > 0:
                    continue

                entity_set = set(sentence.full_entity_ids)
                if len(entity_set) == 0:
                    continue

                sentence_tokens = []
                for token in sentence.token_list:
                    sentence_tokens.append(token.original_text + "/" +
                                           str(token.pos) + "/" +
                                           str(token.ner) + "/" +
                                           str(token.is_stop_word))

                sentence_to_insert['分词词性'] = sentence_tokens
                sentence_to_insert['docid'] = docid
                sentence_to_insert['source'] = one_document['source']
                sentence_to_insert['category'] = one_document['category']
                sentence_to_insert['news_date'] = int(one_document['date'])
                sentence_to_insert['import_date'] = int(one_document['import_date'])
                sentence_to_insert['raw_sentence'] = sentence.raw_sentence
                sentence_to_insert['sentence_length'] = sentence.sentence_length
                sentence_to_insert['sentence_position'] = sentence_index + 2
                sentence_to_insert['token_number'] = len(sentence_tokens)
                sentence_to_insert['entity_set'] = list(entity_set)
                sentence_to_insert['entity_len'] = len(entity_set)
                sentence_to_insert["topic_category"] = category_result.res

                to_insert.append(sentence_to_insert)
                if len(to_insert) >= batch_size:
                    tmp_file = tmp_dir + "/thread_" + str(thread_id) + "_batch_" + str(batch_number) + ".json"
                    batch_number += 1
                    f = codecs.open(tmp_file, 'w', 'utf-8')
                    f.write(json.dumps(to_insert))
                    f.close()
                    print("Successfully saved one batch ([%d] sentences) in file [%s]!" % (len(to_insert), tmp_file))
                    all_inserted_sentence += len(to_insert)
                    to_insert.clear()

        if len(to_insert) > 0:
            tmp_file = tmp_dir + "/thread_" + str(thread_id) + "_batch_" + str(batch_number) + ".json"
            f = codecs.open(tmp_file, 'w', 'utf-8')
            f.write(json.dumps(to_insert))
            f.close()
            print("Successfully saved rest [%d] sentences in file [%s]!" % (len(to_insert), tmp_file))
            all_inserted_sentence += len(to_insert)
            to_insert.clear()

        log_str = "One thread finished! [%d] sentences are saved!" % all_inserted_sentence
        logging.getLogger("system_log").info(log_str)
        print(log_str)

    except Exception:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        msg = 'unexpected error: %s | %s | %s' % \
            (exc_type, exc_obj, exc_tb.tb_lineno)
        print(msg)
