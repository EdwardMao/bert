import sys
import os
import logging
import re
import pickle
import argparse
import multiprocessing

import ujson as json

from utils.parser import Parser


logger = logging.getLogger()
logging.basicConfig(format='%(asctime)s: %(levelname)s: %(message)s')
logging.root.setLevel(level=logging.INFO)


def is_in_range(x, y):
    return x[0] >= y[0] and x[1] <= y[1]


def is_overlapping(x, y):
    return max(x[0], y[0]) < min(x[1], y[1])


def normalise_wikilink(s, prefix):
    s = s.replace(' ', '_').strip('_').strip()
    return prefix + s


def process_line(line, parser):
    d = json.loads(line)
    res = {
        'id': d['id'],
        'title': d['title'],
        'sentences': []
    }
    if d['redirect']:
        return res

    count = {
        'matched_links': 0
    }
    text = d['article']
    for link in d['links']:
        b, e = link['offset']
        # TO-DO: Preserve anchor text, e.g., splited by sentence splitter
        text = text[:b] + text[b:e].replace(' ', '_') + text[e:]

    sentences = parser.parse(text)
    for sent in sentences:
        matched_links = []
        for link in d['links']:
            if is_in_range(link['offset'], (sent['start'], sent['end'])):
                link['offset'][0] -= sent['start']
                link['offset'][1] -= sent['start']
                link['tokens'] = parser.tokenizer(link['text'],
                                                  link['offset'][0])
                try:
                    assert link['tokens'][0][1][0] == link['offset'][0]
                    assert link['tokens'][-1][1][-1] == link['offset'][-1]
                except AssertionError:
                    msg = 'wicked link: (%s, %s)' % (link, d['title'])
                    logger.warning(msg)
                    continue
                matched_links.append(link)
                count['matched_links'] += 1
        sent['links'] = matched_links
    res['sentences'] = sentences
    # try:
    #     assert len(d['links']) == count['matched_links']
    # except AssertionError:
    #     if len(d['links']) < count['matched_links'] or \
    #        len(d['links']) > count['matched_links'] + 20:
    #         msg = 'unmatched links: %s %s %s %s' % \
    #               (d['_id'], d['title'], len(d['links']),
    #                count['matched_links'])
    #         logger.warning(msg)
    return res


def process_block(inpath, outpath):
    try:
        with open(outpath, 'w') as fw:
            with open(inpath, 'r') as f:
                for line in f:
                    res = process_line(line, parser)
                    if res['sentences']:
                        fw.write('%s\n' % json.dumps(res, sort_keys=True))
                    del res

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        msg = 'unexpected error: %s | %s | %s' % \
              (exc_type, exc_obj, exc_tb.tb_lineno)
        logger.error(msg)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('indir',
                        help='Input directory (blocks)')
    parser.add_argument('outdir',
                        help='Output directory')
    parser.add_argument('lang',
                        help='Language code')
    parser.add_argument('--nworker', '-n', default=1,
                        help='Number of workers (default=1)')
    args = parser.parse_args()

    nworker = int(args.nworker)
    os.makedirs(args.outdir, exist_ok=True)
    parser = Parser(args.lang)

    logger.info('processing...')
    pool = multiprocessing.Pool(processes=nworker)
    logger.info('# of workers: %s' % nworker)
    logger.info('parent pid: %s' % os.getpid())
    for i in sorted(os.listdir(args.indir),
                    key=lambda x: os.path.getsize('%s/%s' % (args.indir, x)),
                    reverse=True):
        inpath = '%s/%s' % (args.indir, i)
        outpath = '%s/%s.pp' % (args.outdir, i)
        pool.apply_async(process_block, args=(inpath, outpath,),)
    pool.close()
    pool.join()
    logger.info('done.')
