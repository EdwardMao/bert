import json
import sys
import globals

from configures import *
from commons.utils import initialize_logger
from commons.nlu.language_processor import LanguageProcessor
from commons.warehouse.entity_warehouse import EntityWarehouse
from offline.tools.entity_linking.calculate_idf import IDFPipeline
from offline.tools.entity_linking.entity_linking_pipeline import EntityLinkingPipeline
from offline.tools.entity_linking.entity_linking_statistic import EntityLinkingStatistic
from offline.tools.entity_linking.inverted_index_pipeline import InvertedIndexPipeline
from offline.tools.entity_linking.generate_lexcion_and_mention_table import CreateLexiconAndMentionTable
from offline.tools.kg.crawl_kg import BFSMultiprocessing, BFSKg, MigrateDB, UpdateDB
from offline.tools.kg.save_data_to_db import SaveEntity2DB
from offline.tools.nlu.dialog_act_train_pipeline import DialogActClassifierPipeline
from offline.tools.nlu.attitude_train_pipeline import AttitudeClassifierPipeline
from offline.tools.nlu.question_train_pipeline import QuestionClassifierPipeline
from offline.tools.wiki.wiki_pipeline import WikiPipeline
from offline.tools.wiki.search_section_pipeline import SearchSectionPipeline

if __name__ == "__main__":

    if len(sys.argv) != 3:
        sys.stdout.write("Incorrect parameter numbers!\n")
        sys.stdout.write("Usage: main_app.py configure_offline.txt name_of_command_tool")
        sys.exit()

    with open(sys.argv[1], 'r') as f:
        configure_obj = json.load(f)

    command_str = sys.argv[2]
    if command_str not in configure_obj:
        sys.stdout.write("Command tool [%s]'s parameters are not in configure file\n"%command_str)
        sys.exit()

    with open(configure_obj["global_configure_file"]) as f:
        global_configure_obj = json.load(f)

    globals.data_root = global_configure_obj["data_root"]

    logConfigure = LogConfigure(**global_configure_obj["log_configure"])
    initialize_logger(logConfigure)

    entity_warehouse_configure = EntityWarehouseConfigure(**global_configure_obj["entity_warehouse_configure"])
    globals.entity_warehouse_server = EntityWarehouse(entity_warehouse_configure)

    nlu_configure = NLUConfigure(**global_configure_obj["nlu_configure"])
    globals.nlp_processor = LanguageProcessor(nlu_configure)

    command_tool = None
    exec("command_tool = %s(configure_obj[\"%s\"])" % (command_str, command_str))
    if command_tool is None:
        sys.stderr.write("Command tool [%s] has not been implemented!\n" % command_str)
        sys.exit()

    command_tool.execute()
