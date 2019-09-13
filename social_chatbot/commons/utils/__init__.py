import codecs
import datetime
import logging
import logging.handlers
import math
import os
import re
import sys

from collections import defaultdict
negation_keywords = ["不", "没"]
MBFACTOR = float(1 << 20)
GBFACTOR = float(1 << 30)


def get_files(path, pattern):
    """
    Recursively find all files rooted in <path> that match the regexp <pattern>
    """
    L = []

    # base case: path is just a file
    if (re.match(pattern, os.path.basename(path)) is not None) and os.path.isfile(path):
        L.append(path)
        return L

    # general case
    if not os.path.isdir(path):
        return L

    contents = os.listdir(path)
    for item in contents:
        item = path + item
        if (re.search(pattern, os.path.basename(item)) is not None) and os.path.isfile(item):
            L.append(item)
        elif os.path.isdir(path):
            L.extend(get_files(item + '/', pattern))

    return L


def initialize_logger(log_configure):

    def create_logger(logger_name, log_level):

        logger = logging.getLogger(logger_name)
        logger.setLevel(log_level)
        if logger_name == "component_log":
            log_file_name = log_configure.component_log_dir + logger_name + ".tsv"
        elif logger_name == "user_log":
            log_file_name = log_configure.user_log_dir + logger_name + ".tsv"
        elif logger_name == "system_log":
            log_file_name = log_configure.system_log_dir + logger_name + ".tsv"
        else:
            sys.stderr.write("Not supported logger name [%s]"%logger_name)
            return

        logger_handler = logging.handlers.TimedRotatingFileHandler(log_file_name,
                                                                   when='midnight',
                                                                   interval=1,
                                                                   backupCount=0,
                                                                   atTime=datetime.time(0, 0, 0, 0))
        logger_handler.setFormatter(logging.Formatter("%(asctime)s\t%(levelname)s\t%(module)s\t%(message)s\n"))
        logger.addHandler(logger_handler)

        if logger_name == "system_log":
            err_handler = logging.StreamHandler()
            err_handler.setLevel(logging.WARNING)
            logger_handler.setFormatter(logging.Formatter("%(asctime)s\t%(levelname)s\t%(module)s\t%(message)s\n"))
            logger.addHandler(err_handler)

    for name, level in log_configure.loggers:
        if level == "DEBUG":
            create_logger(name, logging.DEBUG)
        elif level == "INFO":
            create_logger(name, logging.INFO)
        elif level == "WARNING":
            create_logger(name, logging.WARNING)
        elif level == "ERROR":
            create_logger(name, logging.ERROR)
        elif level == "FATAL":
            create_logger(name, logging.FATAL)
        else:
            raise ValueError("Log level [%s] is not set correctly for logger [%s]\n"%(level, name))


def get_ngrams(sent, n):

    ngrams = []

    if isinstance(sent, str):
        words = sent.split()
    elif isinstance(sent, list):
        words = sent
    else:
        sys.stderr.write('unrecognized input type [%s]\n' % type(sent))
        return ngrams

    N = len(words)
    for i in range(n-1, N):
        ngram = words[i-n+1:i+1]
        ngrams.append("_".join(ngram))
    return ngrams


def load_df_file(idf_file, unknown_token_df):

    lines = codecs.open(idf_file, 'r', 'utf-8').read().splitlines()
    idf_dict = defaultdict()
    token2id = defaultdict()
    id2token = defaultdict()

    all_docs = int(lines[0].strip())
    for line in lines[1:]:
        elems = line.strip().split("\t")
        if len(elems) != 3:
            log_str = "Format error in idf file [%s]!\n" % line
            print(log_str.strip())
            continue
        token2id[elems[1]] = int(elems[0])
        id2token[int(elems[0])] = elems[1]
        df = int(elems[2])
        idf = math.log((all_docs - df + 0.5) / (0.5 + df))
        idf_dict[elems[1]] = max(0.0, idf)

    idf_dict["<UNKNOWN>"] = max(0.0, math.log((all_docs - unknown_token_df + 0.5) / (0.5 + unknown_token_df)))

    return idf_dict, token2id, id2token


def generate_trie_tree(input_path, lower=False, min_len=3):
    trie_tree = {}
    lexicon = {}
    with codecs.open(input_path, 'r', 'utf-8') as f:
        for line in f:
            if not line.rstrip() or line.startswith('//'):
                continue
            tmp = line.rstrip('\n').split('\t')
            mention = tmp[0]
            if len(list(mention)) <= min_len:
                continue
            if lower:
                mention = mention.lower()
            lexicon[mention] = None # For future extension

            tree = trie_tree
            for ch in list(mention):
                if ch not in tree:
                    tree[ch] = {}
                tree = tree[ch]

    return trie_tree, lexicon


def get_date_str(delta_hours):
    """
        get a relative day's string in YYYYMMDD format compared with current time
    """
    adjust_time = datetime.datetime.now() - datetime.timedelta(hours=delta_hours)
    instead_date = str(adjust_time.year)
    if len(str(adjust_time.month)) == 1:
        instead_date += "0" + str(adjust_time.month)
    else:
        instead_date += str(adjust_time.month)

    if len(str(adjust_time.day)) == 1:
        instead_date += "0" + str(adjust_time.day)
    else:
        instead_date += str(adjust_time.day)

    return instead_date


def confirm_negation(source, target):

    for nkey in negation_keywords:
        if source.find(nkey) >= 0:
            if target.find(nkey) >= 0:
                return True
            else:
                return False
    return True


def generate_html_str_with_br(response_str_list):

    html_strs = []
    for one_action_response in response_str_list:
        if len(one_action_response) == 0:
            continue
        html_strs.append("<br>" + one_action_response)
    return "".join(html_strs)


def check_contain_chinese(check_str):
    for ch in check_str:
        if u'\u4e00' <= ch <= u'\u9fff':
             return True
    return False


def get_mb_bytes(byte_size):

    return int(byte_size / MBFACTOR)


def get_gb_bytes(byte_size):

    return int(byte_size / GBFACTOR)


def l1_norm(v):

    d = 0
    for key, weight in v.items():
        d += math.fabs(weight)
    return d


def l2_norm(v):

    d = 0
    for key, weight in v.items():
        d += weight * weight
    return math.sqrt(d)


def space_tokenizer(input_string):
    return input_string.split(" ")
