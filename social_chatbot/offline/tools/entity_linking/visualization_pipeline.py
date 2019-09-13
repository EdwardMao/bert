import logging
import multiprocessing
import os
import pymongo
import sys

from commons.db.mongodb import MongoDB
from commons.utils import get_date_str
from commons.entity.linking.models.text import EntityMention, Entity
from commons.entity.linking.extra import visualizer
from offline.tools.offline_tools import OfflineTools


class VisualizationPipeline(OfflineTools):

    def __init__(self, local_configure):

        super().__init__()
        self.system_logger = logging.getLogger("system_log")
        self.nworkers = int(local_configure['nworkers'])
        self.db_config = {
            'host': local_configure['host'],
            'port': int(local_configure['port']),
            'input_db_name': local_configure['input_db_name'],
            'input_collection_name': local_configure['input_collection_name'],
            'user':local_configure['user'],
            'pwd':local_configure['pwd']
        }
        self.output_dir = local_configure['output_dir']
        self.kg_api_url = local_configure['kg_api_url']
        if len(local_configure['import_date']) != 8:
            instead_date = get_date_str(24)
            log_str = 'import date format error: %s. Using %s instead' % (local_configure['import_date'], instead_date)
            self.system_logger.info(log_str)
            print(log_str)
            self.import_date = int(instead_date)
        else:
            self.import_date = int(local_configure['import_date'])

        pass

    def execute(self):
        self.process()
        pass

    def process(self):
        self.system_logger.info('initializing...')
        os.makedirs(self.output_dir, exist_ok=True)
        visualizer.copy_config_files(self.output_dir)
        visualizer.KBID_PREFIX['Tencent_KG'] = self.kg_api_url

        self.system_logger.info('searching...')
        input_db = MongoDB(self.db_config['host'],
                           self.db_config['port'],
                           self.db_config['input_db_name'],
                           self.db_config['user'],
                           self.db_config['pwd'])
        input_collection = input_db.db[self.db_config['input_collection_name']]

        query = {"import_date": {"$gt": self.import_date}}
        try:
            docids = input_collection.find(query).distinct('docid')
        except pymongo.errors.OperationFailure:
            # TO-DO: fix the following error:
            # pymongo.errors.OperationFailure: distinct too big, 16mb cap
            docids = [i['docid'] for i in input_collection.find(query)]

        chunk_size = int(len(docids) / self.nworkers)
        self.system_logger.info('# of docs found: %s' % len(docids))
        if len(docids) == 0:
            return
        if chunk_size == 0:
            chunk_size = len(docids)

        self.system_logger.info('# of workers: %s' % self.nworkers)
        self.system_logger.info('chunk size: %s' % chunk_size)
        chunks = []
        for i in range(0, len(docids), chunk_size):
            chunks.append(slice(i, i+chunk_size))
        self.system_logger.info('parent pid: %s' % os.getpid())
        self.system_logger.info('processing...')

        # # Single processing
        # for c in chunks:
        #     process_chunk(self.db_config, docids[c], self.output_dir)

        # Multi-processing
        pool = multiprocessing.Pool(processes=self.nworkers)
        for c in chunks:
            args = (self.db_config, docids[c], self.output_dir,)
            pool.apply_async(process_chunk, args=args,)
        pool.close()
        pool.join()


def process_chunk(db_config, docids, output_dir):
    try:
        # MongoDB is not fork-safe:
        # http://api.mongodb.com/python/current/faq.html#is-pymongo-fork-safe
        input_db = MongoDB(db_config['host'],
                           db_config['port'],
                           db_config['input_db_name'],
                           db_config['user'],
                           db_config['pwd'])
        input_collection = input_db.db[db_config['input_collection_name']]

        for docid in docids:
            html = []
            response = input_collection.find({'docid': docid})
            for sent in response:
                # text = ''.join([x.split('/')[0] for x in sent['分词词性']])
                text = sent['raw_sentence']
                entitymentions = []
                if sent['实体链接']:
                    for i in sent['实体链接']:
                        if i['entity']:
                            en = Entity(i['entity']['kbid'])
                        else:
                            en = None
                        em = EntityMention(i['entity_mention'],
                                           beg=i['beg']-sent['sentence_start'],
                                           end=i['end']-sent['sentence_start'],
                                           entity=en)
                        entitymentions.append(em)
                h = visualizer.visualize(text, entitymentions, stats=True)
                html.append(h)
            html = visualizer.HTML_TEMPLATE % '<br>\n'.join(html)

            outpath = '%s/%s.html' % (output_dir, docid)
            with open(outpath, 'w') as fw:
                fw.write(html)

    except Exception:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        msg = 'unexpected error: %s | %s | %s' % \
            (exc_type, exc_obj, exc_tb.tb_lineno)
        print(msg)
