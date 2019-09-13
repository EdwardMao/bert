import functools
import json
import os

from collections import defaultdict
from commons.db.mongodb import MongoDB
from commons.utils import get_gb_bytes, get_files


def load_bin_index_file(filename):

    if not os.path.exists(filename):
        return defaultdict()

    index2pos = defaultdict()
    lines = open(filename, 'r').read().splitlines()
    for line in lines:
        elems = line.split("\t")
        index2pos[int(elems[0].strip())] = (int(elems[1].strip()), int(elems[2].strip()))
    return index2pos


def write_bin_index_file(index2pos, filename):

    f = open(filename,'w')
    for key, value in index2pos.items():
        f.write("%s\t%s\t%s\n"%(str(key),str(value[0]),str(value[1])))
    f.close()


def load_index(index_template):

    index_file = index_template + ".index"
    bin_file = index_template + ".bin"
    index2pos = load_bin_index_file(index_file)
    bin_handle = open(bin_file, 'rb')
    word2sentence_tf = defaultdict()

    if get_gb_bytes(os.path.getsize(bin_file)) <= 32:
        for word_id, word_info in index2pos.items():
            start = word_info[0]
            length = word_info[1]
            bin_handle.seek(start)
            byte_content = bin_handle.read(length)
            sentence_tf = recover_bytes_to_dict(byte_content)
            word2sentence_tf[word_id] = sentence_tf
    else:
        word2sentence_tf = None

    return index2pos, bin_handle, word2sentence_tf


def recover_bytes_to_dict(bytes_content):

    return_dict = {}
    index = 0
    all_bytes = len(bytes_content)
    while index < all_bytes:
        if index + 7 > all_bytes:
            break
        sentence_id = int.from_bytes(bytes_content[index:index + 7], byteorder='big')
        tf = int.from_bytes(bytes_content[index + 7:index + 8], byteorder='big')
        return_dict[sentence_id] = tf
        index += 8

    return return_dict


def convert_dict_to_bytes(sentence_tf):

    save_bytes = b"".join([k.to_bytes(7, byteorder='big') + v.to_bytes(1, byteorder='big')
                           for k, v in sentence_tf.items()])
    return save_bytes


class SearchWarehouse(object):

    def __init__(self, search_warehouse_configure):

        self.name = search_warehouse_configure.name
        self.host = search_warehouse_configure.host
        self.port = search_warehouse_configure.port
        self.db_name = search_warehouse_configure.db_name
        self.user = search_warehouse_configure.user
        self.pwd = search_warehouse_configure.pwd
        self.sentence_collection_name = search_warehouse_configure.sentence_collection_name
        self.index_dir = search_warehouse_configure.index_dir
        self.memcache_ip_port = search_warehouse_configure.memcache_ip_port

        self.db_client = MongoDB(self.host, self.port, self.db_name, self.user, self.pwd)
        self.sentence_collection = self.db_client.db[self.sentence_collection_name]

        tmp_files = get_files(self.index_dir, r'.*bin')
        if len(tmp_files) == 1:
            self.index_template = tmp_files[0].replace(".bin", "")
        else:
            files_date = {}
            for filename in tmp_files:
                files_date[filename]= int(os.path.basename(filename)[:8])
            sorted_filenames = sorted(files_date.items(), key=lambda x: x[1], reverse=True)
            self.index_template = sorted_filenames[0][0].replace(".bin", "")

        index2pos, bin_handle, word2sentence_tf = load_index(self.index_template)

        self.word_index_to_position_in_file = index2pos
        self.index_bin_file_handle = bin_handle
        self.word_index_to_sentence_tf = word2sentence_tf

    @functools.lru_cache(maxsize=None)
    def request_sentences_by_query(self, search_query):
        sentence_index = set()
        for one_sent in self.sentence_collection.find(json.loads(search_query)):
            sentence_index.add(one_sent["sentence_index"])
        return list(sentence_index)

    @functools.lru_cache(maxsize=None)
    def request_sentences_by_query_orderby_date(self, search_query):
        sentence_obj = list(self.sentence_collection.find(json.loads(search_query)))
        ranked_sentences = sorted(sentence_obj, key=lambda x:x["news_date"], reverse=True)
        sentence_index = [sent['sentence_index'] for sent in ranked_sentences[:50]]
        return sentence_index

    @functools.lru_cache(maxsize=None)
    def request_token_by_index(self, token_index):

        if self.word_index_to_sentence_tf is not None:
            try:
                return self.word_index_to_sentence_tf[token_index]
            except KeyError:
                return {}

        if token_index in self.word_index_to_position_in_file:
            start_position = self.word_index_to_position_in_file[token_index][0]
            index_length = self.word_index_to_position_in_file[token_index][1]
            self.index_bin_file_handle.seek(start_position)
            return recover_bytes_to_dict(self.index_bin_file_handle.read(index_length))
        else:
            return {}

    @functools.lru_cache(maxsize=None)
    def request_sentence_by_index(self, sentence_index):
        return list(self.sentence_collection.find({"sentence_index": sentence_index}))
