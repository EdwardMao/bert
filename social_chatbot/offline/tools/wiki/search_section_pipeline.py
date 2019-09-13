import sys
import os
import logging
import subprocess

import ujson as json
import zhconv

from commons.db.mongodb import MongoDB
from offline.tools.offline_tools import OfflineTools


class SearchSectionPipeline(OfflineTools):

    def __init__(self, local_configure):

        super().__init__()
        self.data_dir = local_configure['data_dir']
        self.output_path = local_configure['output_path']
        self.keywords = local_configure['keywords']
        self.mongo = MongoDB(local_configure['host'],
                             int(local_configure['port']),
                             local_configure['db_name'],
                             local_configure['user'],
                             local_configure['pwd'])
        self.collection = self.mongo.db[local_configure['collection_name']]
        self.system_logger = logging.getLogger("system_log")
        pass

    def execute(self):
        self.search()
        pass

    def search(self):
        self.system_logger.info('loading data...')
        data = json.load(open('%s/sections.json' % self.data_dir))
        self.system_logger.info('keywords: %s' % self.keywords)
        self.system_logger.info('search...')
        with open(self.output_path, 'w') as fw:
            for kbid in data:
                sections = data[kbid]
                for n, i in enumerate(sections):
                    sec = zhconv.convert(i[0], 'zh-ch')
                    for kw in self.keywords:
                        if kw in sec:
                            start = i[1][0]
                            if len(sections) - 1 == n:
                                end = sys.maxsize
                            else:
                                end = sections[n+1][1][0]

                                # In case of:
                                # == 评价 ==     <- 2 '=' mark, target section
                                # === 正面 ===   <- 3 '=' mark, subsection
                                # ...
                                # ==== 争议 ==== <- 4 '=' mark, subsubsection
                                # ...
                                # === 负面 ===   <- 3 '=' mark, subsection
                                # ...
                                # == Foo ==     <- 2 '=' mark, new section
                                # ...
                                nums = sec.count('=')
                                for k in range(n+1, len(sections)):
                                    if sections[k][0].count('=') == nums:
                                        end = sections[k][1][0]
                                        break

                            res = self.collection.find({
                                'source_title': kbid,
                                'start': {'$gt': start-1},
                                'end': {'$lt': end}
                            })
                            if res.count() > 0:
                                fw.write('%s\n' % kbid)
                                for r in res:
                                    sent = ''.join([t[0] for t in r['tokens']])
                                    sent = zhconv.convert(sent, 'zh-ch')
                                    fw.write('%s\n' % sent)
                                fw.write('\n')
                            break
