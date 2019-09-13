import argparse
import socket
import sys

from flask import Flask, request, jsonify

from configures import *
from commons.utils import initialize_logger
from commons.entity.extension.entity_extension_wrapper import *
from commons.nlu.classifier.intent_classify import IntentClassifier
from commons.nlu.language_processor import LanguageProcessor
from commons.nlu.sentence_similarity import BM25SentenceSimilarity
from commons.warehouse.entity_warehouse import EntityWarehouse
from commons.warehouse.search_warehouse import SearchWarehouse
from dialog.dialog_graph import DialogGraph
from offline.api.dialog_graph_module import DialogGraphApi
from offline.api.kg import KgApi
from offline.api.nlu_module import NluApi
from offline.api.search_module import ShortSentenceSearchApi
from online.online_service.short_sentence_search_service import ShortSentenceSearch

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False


@app.route('/get_entry', methods=["GET"])
def get_entry():
    for i in ['kbid']:
        try:
            assert i in request.args
        except AssertionError:
            return 'ERROR: Missing argument: %s' % i
    kbid = request.args.get('kbid')
    try:
        result = apis['KgApi'].get_entry_by_kbid(kbid)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        msg = 'UNEXPECTED ERROR: %s | %s | %s' % \
              (exc_type, exc_obj, exc_tb.tb_lineno)
        return msg
    return jsonify(result)


@app.route('/search_entry', methods=["GET"])
def search_entry():
    for i in ['name']:
        try:
            assert i in request.args
        except AssertionError:
            return 'ERROR: Missing argument: %s' % i
    name = request.args.get('name')

    global host
    global port
    if host in ['localhost', '0.0.0.0', '127.0.1.1']:
        host = get_local_ip()

    try:
        results = []
        kbids = apis['KgApi'].search_entry_by_name(name)
        for kbid, score in kbids:
            entity_name = apis['KgApi'].get_entry_by_kbid(kbid)['name'][0]
            line = '<a href="http://%s:%s/get_entry?kbid=%s">%s %s</a>' % \
                (host, port, kbid, entity_name, score)
            results.append(line)
        result = '<br>\n'.join(results)
        if not result:
            result = 'null'
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        msg = 'UNEXPECTED ERROR: %s | %s | %s' % \
              (exc_type, exc_obj, exc_tb.tb_lineno)
        return msg
    return result


@app.route('/nlu_process', methods=["GET"])
def nlu_process():
    for i in ['query']:
        try:
            assert i in request.args
        except AssertionError:
            return 'ERROR: Missing argument: %s' % i
    query = request.args.get('query')

    try:
        results = apis['NluApi'].nlu_processor(query)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        msg = 'UNEXPECTED ERROR: %s | %s | %s' % \
              (exc_type, exc_obj, exc_tb.tb_lineno)
        return msg
    return jsonify(results)


@app.route('/bm25_similarity', methods=["GET"])
def bm25_similarity():
    for i in ['query_a', 'query_b']:
        try:
            assert i in request.args
        except AssertionError:
            return 'ERROR: Missing argument: %s' % i
    query_a = request.args.get('query_a')
    query_b = request.args.get('query_b')

    try:
        results = apis['NluApi'].bm25_similarity(query_a, query_b)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        msg = 'UNEXPECTED ERROR: %s | %s | %s' % \
              (exc_type, exc_obj, exc_tb.tb_lineno)
        return msg
    return jsonify(results)


@app.route('/intent_classifier', methods=["GET"])
def intent_classifier():
    for i in ['query']:
        try:
            assert i in request.args
        except AssertionError:
            return 'ERROR: Missing argument: %s' % i
    query = request.args.get('query')

    try:
        results = apis['NluApi'].intent_classifier(query)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        msg = 'UNEXPECTED ERROR: %s | %s | %s' % \
              (exc_type, exc_obj, exc_tb.tb_lineno)
        return msg
    return jsonify(results)


@app.route('/sentence_search', methods=["GET"])
def search_process():
    for i in ['query']:
        try:
            assert i in request.args
        except AssertionError:
            return 'ERROR: Missing argument: %s' % i
    raw_query = request.args.get('query')
    constraint_dict = json.loads(globals.default_sentence_search_constraint_str)

    if 'entity_list' in request.args:
        constraint_dict["entity_list"] = request.args.get("entity_list").split("_")

    if 'source' in request.args:
        constraint_dict["source"] = request.args.get("source")

    if 'category' in request.args:
        constraint_dict["category"] = request.args.get("category")

    if 'days_ago' in request.args:
        constraint_dict["days_ago"] = request.args.get("days_ago")

    if 'entity_number' in request.args:
        constraint_dict["entity_number"] = request.args.get("entity_number")

    if 'sentence_length' in request.args:
        constraint_dict["sentence_length"] = request.args.get("sentence_length")

    if 'sentence_position' in request.args:
        constraint_dict["sentence_position"] = request.args.get("sentence_position")

    try:
        results = apis['ShortSentenceSearchApi'].search_processor(raw_query, constraint_dict)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        msg = 'UNEXPECTED ERROR: %s | %s | %s' % \
              (exc_type, exc_obj, exc_tb.tb_lineno)
        return msg
    return jsonify(results)


@app.route('/dialog_graph', methods=["GET"])
def get_dialog_graph():
    if 'intent' not in request.args and 'question' not in request.args and 'grouding' not in request.args:
        return 'ERROR: Missing argument'

    results = {}
    try:
        if 'intent' in request.args:
            intent_id = request.args.get('intent')
            results = apis['DialogGraphApi'].get_intent(intent_id)
        elif 'question' in request.args:
            question_id = request.args.get('question')
            results = apis['DialogGraphApi'].get_question(question_id)
        elif 'grounding' in request.args:
            grounding_id = request.args.get("grounding")
            results = apis['DialogGraphApi'].get_grounding(grounding_id)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        msg = 'UNEXPECTED ERROR: %s | %s | %s' % \
              (exc_type, exc_obj, exc_tb.tb_lineno)
        return msg

    return jsonify(results)

@app.route('/entity_extension', methods=["GET"])
def get_entity_extension():
    if 'kbid' not in request.args or 'extension_type' not in request.args:
        return 'ERROR: Missing argument'

    results = {}
    try:
        kbid = [request.args.get('kbid')]
        extension_type = request.args.get('extension_type')
        results = apis['KgApi'].obtain_entity_extension(kbid, extension_type)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        msg = 'UNEXPECTED ERROR: %s | %s | %s' % \
              (exc_type, exc_obj, exc_tb.tb_lineno)
        return msg

    return jsonify(results)

@app.route('/entity_analogy_extension', methods=["GET"])
def get_entity_analogy_extension():
    if 'kbid1' not in request.args or 'kbid2' not in request.args or 'kbid3' not in request.args:
        return 'ERROR: Missing argument'

    results = {}
    try:
        kbid1 = request.args.get('kbid1')
        kbid2 = request.args.get('kbid2')
        kbid3 = request.args.get('kbid3')
        kbid = [kbid1, kbid2, kbid3]
        results = apis['KgApi'].obtain_entity_extension(kbid, '3')
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        msg = 'UNEXPECTED ERROR: %s | %s | %s' % \
              (exc_type, exc_obj, exc_tb.tb_lineno)
        return msg

    return jsonify(results)


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('config', help='Path to API config file')
    args = parser.parse_args()

    with open(args.config, 'r') as f:
        configure_obj = json.load(f)

    with open(configure_obj["global_configure_file"]) as f:
        global_configure_obj = json.load(f)

    globals.data_root = global_configure_obj["data_root"]
    globals.default_sentence_search_constraint_str = json.dumps(global_configure_obj["default_sentence_search_constraint"])

    logConfigure = LogConfigure(**global_configure_obj["log_configure"])
    initialize_logger(logConfigure)

    search_warehouse_configure = SearchWarehouseConfigure(**global_configure_obj["search_warehouse_configure"])
    globals.search_warehouse_server = SearchWarehouse(search_warehouse_configure)

    entity_warehouse_configure = EntityWarehouseConfigure(**global_configure_obj["entity_warehouse_configure"])
    globals.entity_warehouse_server = EntityWarehouse(entity_warehouse_configure)

    entity_extension_configure = EntityExtensionConfigure(**global_configure_obj["entity_extension_configure"])
    globals.entity_extension_server = EntityExtensionWrapper(entity_extension_configure)

    bm25_configure = BM25Configure(**global_configure_obj["bm25_configure"])

    nlu_configure = NLUConfigure(**global_configure_obj["nlu_configure"])
    globals.nlp_processor = LanguageProcessor(nlu_configure)

    dialog_graph_configure = DialogGraphConfigure(**global_configure_obj["dialog_graph_configure"])
    globals.dialog_graph = DialogGraph(dialog_graph_configure)

    global_configure_obj["short_sentence_search_configure"]["bm25_configure"] = bm25_configure
    sss_configure = ShortSentenceSearchConfigure(**global_configure_obj["short_sentence_search_configure"])
    globals.short_sentence_search_server = ShortSentenceSearch(sss_configure)

    bm25ss_configure = BM25SentenceSimilarityConfigure(bm25_configure)
    globals.bm25_sentence_similarity_server = BM25SentenceSimilarity(bm25ss_configure)

    intent_classifier_configure = IntentClassifierConfigure(**global_configure_obj["intent_classifier_configure"])
    globals.intent_classifier_server = IntentClassifier(intent_classifier_configure)

    apis = {}
    for api_name in configure_obj:
        if api_name in ['portal', 'global_configure_file']:
            continue
        exec("apis[\"%s\"] = %s(configure_obj[\"%s\"])" % \
             (api_name, api_name, api_name))

    if apis is {}:
        sys.stderr.write("No API found\n")
        sys.exit()

    host = configure_obj['portal']['host']
    port = configure_obj['portal']['port']
    app.run(host, port=int(port), threaded=True)
