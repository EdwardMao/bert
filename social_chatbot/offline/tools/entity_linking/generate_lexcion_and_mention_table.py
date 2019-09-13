import json
import logging
import os
import pymongo
import re
import sys

import globals

from collections import Counter
from collections import defaultdict
from commons.db.mongodb import MongoDB
from commons.utils import check_contain_chinese
from offline.tools.offline_tools import OfflineTools

LEXICON_PROPS = [
    'name',
    '精选别名'
]

MENTION_PROPS = [
                 'name',
                 '精选别名',
                 '原始名称',
                 '名称',
                 'rich_name'
                 # '中文名',
                 # '外文名',
                ]

TYPES = {
    10: '游戏',
    39: '歌曲',
    42: '歌手',
    57: '人物',
    58: '体育明星',
    63: '影视明星',
    178: '音乐团体',
    204: '电影',
    205: '电视剧',
    216: '体育项目',
    221: '体育组织',
    222: '体育赛事',
    273: '综艺',
    298: '虚拟人物',
    333: '电视频道',
    404: '体育事件',
}

PERSON = {
    42: '歌手',
    57: '人物',
    58: '体育明星',
    63: '影视明星',
    298: '虚拟人物',
}

CHINESE_LAST_NAME = set(['王', '李', '张', '刘', '陈', '杨', '黄', '赵',
                         '吴', '周', '徐', '孙', '马', '朱', '胡', '郭',
                         '何', '高', '林', '罗', '郑', '梁', '谢', '宋',
                         '唐', '许', '韩', '冯', '邓', '曹', '彭', '曾',
                         '肖', '田', '董', '袁', '潘', '于', '蒋', '蔡',
                         '余', '杜', '叶', '程', '苏', '魏', '吕', '丁',
                         '任', '沈', '姚', '卢', '姜', '崔', '锺', '谭',
                         '陆', '汪', '范', '金', '石', '廖', '贾', '夏',
                         '韦', '付', '方', '白', '邹', '孟', '熊', '秦',
                         '邱', '江', '尹', '薛', '闫', '段', '雷', '侯',
                         '龙', '史', '陶', '黎', '贺', '顾', '毛', '郝',
                         '龚', '邵', '万', '钱', '严', '覃', '武', '戴',
                         '莫', '孔', '向', '汤'])


class CreateLexiconAndMentionTable(OfflineTools):

    def __init__(self, local_configure):
        super().__init__()
        self.system_logger = logging.getLogger("system_log")
        self.local_configure = local_configure
        self.db_config = {
            'host': local_configure['host'],
            'port': int(local_configure['port']),
            'db_name': local_configure['db_name'],
            'input_collection_name': local_configure['input_collection_name'],
            'output_collection_name': local_configure['output_collection_name'],
            'user': local_configure["user"],
            'pwd': local_configure["pwd"],
        }
        self.output_dir = local_configure["output_dir"]
        self.lexicon_min_length = local_configure["lexicon_min_length"]
        pass

    def execute(self):
        # self.create_lexicon()
        self.create_metion_table()
        pass

    def get_names(self, props):
        '''
        Extract name list from Tencent KG
        '''
        self.system_logger.info('host: %s' % self.db_config['host'])
        self.system_logger.info('port: %s' % self.db_config['port'])
        self.system_logger.info('db name: %s' % self.db_config['db_name'])
        self.system_logger.info('collection name: %s' % self.db_config['input_collection_name'])

        client = MongoDB(self.db_config['host'],
                         self.db_config['port'],
                         self.db_config['db_name'],
                         self.db_config['user'],
                         self.db_config['pwd'])
        collection = client.db[self.db_config['input_collection_name']]

        kbid2names = defaultdict(lambda: defaultdict(int))
        kbid2types = {}
        kbid2hypernyms = {}
        kbid2popularity = {}
        count = defaultdict(int)
        res = collection.find({})
        self.system_logger.info('# of entries found: %s' % res.count())
        for i in res:
            for p in props:
                try:
                    # if not set([x[0] for x in i['types']]).intersection(TYPES):
                    #     continue
                    kbid2types[i['_id']] = [x[0] for x in i['types']]
                except KeyError:
                    count['missing_type'] += 1

                try:
                    for name in i[p]:
                        kbid2names[i['_id']][name[0]] += 1
                except KeyError:
                    count['missing_%s' % p] += 1

                try:
                    kbid2hypernyms[i['_id']] = [x[0] for x in i['精选上位词']]
                except KeyError:
                    count['missing_hypernyms'] += 1

                try:
                    kbid2popularity[i['_id']] = int(i['popular'][0][0])
                except KeyError:
                    count['missing_popularity'] += 1

        self.system_logger.info('Missing properties:')
        for i in count:
            self.system_logger.info('  %s: %s' % (i, count[i]))

        return kbid2names, kbid2types, kbid2hypernyms, kbid2popularity

    def create_lexicon(self):

        def expand_lexicon(text):
            res = [text]
            if '·' in text:
                res.append(text.replace('·', '-'))
                res.append(text.replace('·', ''))
            return res

        def strip_lexicon(s):
            if check_contain_chinese(s):
                s = s.replace(' ', '')
            return s

        def is_valid_lexicon(s):
            punctuations = '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'
            if s[0] in punctuations:
                return False
            if len(s) < self.lexicon_min_length:
                return False
            if s.isdigit():
                return False
            return True

        def is_valid_person_name(s):

            if s[0] in CHINESE_LAST_NAME:
                return True
            if s[0].isalpha() and not s[0].isdigit():
                return True
            else:
                return False

        kbid2names, kbid2types, _, _ = self.get_names(LEXICON_PROPS)
        output_path = '%s/lexicon.txt' % self.output_dir

        lexicon = set()
        for kbid in kbid2names:
            for l in kbid2names[kbid]:
                l = strip_lexicon(l)
                if not is_valid_lexicon(l):
                    if kbid2types \
                            and set(kbid2types[kbid]).intersection(PERSON) \
                            and is_valid_person_name(l):
                        lexicon.add(l)
                    continue
                for i in expand_lexicon(l):
                    lexicon.add(i)
        lexicon = sorted(lexicon)

        self.system_logger.info('# of unique lexicon found: %s' % len(lexicon))
        self.system_logger.info('Writing...')
        with open(output_path, 'w') as fw:
            fw.write('\n'.join(lexicon))

    def create_metion_table(self):

        def strip_mention(text):
            text = text.replace('\t', ' ').replace('\n', ' ').replace('\r', ' ')
            text = text.lower().strip()
            text = text.replace('\\', '')
            text = ' '.join(text.split())
            return text

        def expand_mention(text):
            RE_STRIP = r' \([^)]*\)|\<[^)]*\>|,|"|\.|\'|:|-'
            # STOP_WORDS = ['a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for',
            #               'from', 'has', 'he', 'i', 'in', 'is', 'it', 'its', 'of', 'on',
            #               'that', 'the', 'their', 'we', 'to', 'was', 'were', 'with',
            #               'you', 'your', 'yours', 'our', 'ours', 'theirs', 'her',
            #               'hers', 'his', 'him', 'mine', 'or', 'but', 'though', 'since']
            res = []
            # Strip mention
            res.append(''.join(re.sub(RE_STRIP, '', text).strip().split()))
            # # Remove stop words
            # res.append(' '.join([word for word in text.split() \
            #                      if word not in STOP_WORDS]).strip())
            # '·' in Chinese names
            if '·' in text:
                res.append(text.replace('·', '-'))

            return res

        def filter_mention(mention):
            if not mention:
                return False
            if mention == '':
                return False
            return True

        def get_kbid2mention(data):
            res = defaultdict(lambda: defaultdict(int))
            for mention in data:
                for kbid in data[mention]:
                    assert type(data[mention][kbid]) == int
                    res[kbid][mention] = data[mention][kbid]
            return res

        def add_score(data):
            for mention in data:
                c = Counter(data[mention])
                tol = sum(c.values())
                assert type(tol) == int
                for kbid in data[mention]:
                    data[mention][kbid] = data[mention][kbid] / tol

        kbid2names, _, _, kbid2popularity = self.get_names(MENTION_PROPS)

        mention2kbid = defaultdict(lambda: defaultdict(int))
        for kbid in kbid2names:
            for name in kbid2names[kbid]:
                mention = strip_mention(name)
                mentions = [mention]
                mentions.extend(expand_mention(mention))
                mentions = set(mentions)

                for m in mentions:
                    if not filter_mention(m):
                        continue
                    # mention2kbid[m][kbid] += kbid2names[kbid][name]
                    try:
                        mention2kbid[m][kbid] += kbid2popularity[kbid]
                    except KeyError:
                        mention2kbid[m][kbid] += 1

        mention2kbid = dict(mention2kbid)
        with open('%s/mention2kbid_raw.json' % self.output_dir, 'w') as fw:
            json.dump(mention2kbid, fw, indent=4)

        self.system_logger.info('converting kbid2mention..')
        kbid2mention = get_kbid2mention(mention2kbid)
        self.system_logger.info('done.')
        with open('%s/kbid2mention_raw.json' % self.output_dir, 'w') as fw:
            json.dump(kbid2mention, fw, indent=4)

        self.system_logger.info('computing mention2kbid...')
        add_score(mention2kbid)
        with open('%s/mention2kbid.json' % self.output_dir, 'w') as fw:
            json.dump(mention2kbid, fw, indent=4)
        self.system_logger.info('done.')

        self.system_logger.info('computing kbid2mention...')
        add_score(kbid2mention)
        with open('%s/kbid2mention.json' % self.output_dir, 'w') as fw:
            json.dump(kbid2mention, fw, indent=4)
        self.system_logger.info('done.')

        # start insert into mongo db
        self.system_logger.info('db name: %s' % self.db_config['db_name'])
        self.system_logger.info('collection name: %s' % self.db_config["output_collection_name"])
        client = MongoDB(self.db_config['host'],
                         self.db_config['port'],
                         self.db_config['db_name'],
                         self.db_config['user'],
                         self.db_config['pwd'])

        self.system_logger.info('drop collection')
        client.db.drop_collection(self.db_config['output_collection_name'])

        collection = client.db[self.db_config['output_collection_name']]
        self.system_logger.info('processing...')

        to_insert = []
        self.system_logger.info('converting...')  # TO-DO: save RAM
        for mention in mention2kbid:
            if sys.getsizeof(mention) >= 512:
                self.system_logger.warning('mention is too large, skip')
                continue

            entities = sorted(mention2kbid[mention].items(), key=lambda x: x[1], reverse=True)
            ins = {
                'mention': mention,
                'entities': entities
            }
            to_insert.append(ins)

        self.system_logger.info('importing...')
        try:
            collection.insert(to_insert)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msg = 'unexpected error: %s | %s | %s' % \
                  (exc_type, exc_obj, exc_tb.tb_lineno)
            self.system_logger.error(msg)

        self.system_logger.info('done.')

        self.system_logger.info('indexing...')
        collection.create_index('mention', unique=True)
        # collection.create_index([('mention', 1), ('entities', 1)], unique=True)
        self.system_logger.info('done.')

        self.system_logger.info(collection)
        self.system_logger.info(collection.count())
