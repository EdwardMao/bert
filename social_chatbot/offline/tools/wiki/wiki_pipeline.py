import os
import logging
import subprocess

from offline.tools.offline_tools import OfflineTools


class WikiPipeline(OfflineTools):

    def __init__(self, local_configure):

        super().__init__()
        self.output_dir = local_configure['output_dir']
        self.nworkers = local_configure['nworkers']
        self.host = local_configure['host']
        self.port = local_configure['port']
        self.db_name = local_configure['db_name']
        self.collection_name = local_configure['collection_name']
        self.user = local_configure['user']
        self.pwd = local_configure['pwd']
        self.pwd_dir = os.path.dirname(os.path.abspath(__file__))
        self.system_logger = logging.getLogger("system_log")
        os.makedirs(self.output_dir, exist_ok=True)
        pass

    def execute(self):
        self.download()
        self.process()
        self.parse()
        self.import_to_db()
        self.parse_links()
        pass

    def download(self):
        cmd = [
            'python',
            '%s/download.py' % self.pwd_dir,
            'zhwiki',
            'latest',
            self.output_dir
        ]
        self.system_logger.info('*** Step 1: download Wikipedia dump ***')
        subprocess.call(' '.join(cmd), shell=True)

    def process(self):
        dump_dir = '%s/latest/zhwiki-latest/' % self.output_dir
        cmd = [
            'python',
            '%s/process_pages-articles_multistream.py' % self.pwd_dir,
            '%s/zhwiki-latest-pages-articles-multistream.xml.bz2' % dump_dir,
            '%s/zhwiki-latest-pages-articles-multistream-index.txt.bz2' % dump_dir,
            '%s/output' % self.output_dir,
            '-n %s' % self.nworkers
        ]
        self.system_logger.info('*** Step 2: process dump ***')
        subprocess.call(' '.join(cmd), shell=True)

    def parse(self):
        cmd = [
            'python',
            '%s/parse_processed_pages_articles.py' % self.pwd_dir,
            '%s/output/blocks' % self.output_dir,
            '%s/output/blocks.pp' % self.output_dir,
            'zh',
            '-n %s' % self.nworkers
        ]
        self.system_logger.info('*** Step 3: parse dump ***')
        subprocess.call(' '.join(cmd), shell=True)

    def import_to_db(self):
        cmd = [
            'python',
            '%s/import_sentences.py' % self.pwd_dir,
            '%s/output/blocks.pp' % self.output_dir,
            self.host,
            self.port,
            self.user,
            self.pwd,
            self.db_name,
            self.collection_name,
            '-n %s' % self.nworkers
        ]
        self.system_logger.info('*** Step 4: import to MongoDB ***')
        subprocess.call(' '.join(cmd), shell=True)

    def parse_links(self):
        cmd = [
            'python',
            '%s/links.py' % self.pwd,
            '%s/output/blocks' % self.output_dir,
            '%s/output/links' % self.output_dir,
            '-n %s' % self.nworkers
        ]
        self.system_logger.info('*** Step 5: parse links ***')
        subprocess.call(' '.join(cmd), shell=True)
