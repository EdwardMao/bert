import globals
import json
import logging
import sys
import traceback
import uuid

from commons.entity.extension.entity_extension_wrapper import EntityExtensionWrapper
from commons.nlu.classifier.intent_classify import IntentClassifier
from commons.nlu.encoder import Encoder
from commons.nlu.language_processor import LanguageProcessor
from commons.nlu.sentence_similarity import BM25SentenceSimilarity
from commons.utils import initialize_logger
from commons.warehouse.entity_warehouse import EntityWarehouse
from commons.warehouse.search_warehouse import SearchWarehouse
from configures import OnlineConfigure
from dialog.dialog_graph import DialogGraph
from dialog.dialog_state import DialogSessionState
from dialog.general_response import GeneralResponseGenerator
from online.chat_engine import ChatEngine
from online.online_service.online_logging import OnlineInfoLogger
from online.online_service.qa_service import QAServer
from online.online_service.short_sentence_search_service import ShortSentenceSearch

from collections import defaultdict

from flask import Flask
from flask import jsonify
from flask import make_response
from flask import request

app = Flask(__name__)
t2s = Encoder('zh')

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


@app.route('/', methods=['POST'])
def process_chatbot():

    data = request.data.decode("utf-8")
    data = t2s.to_simplified(data)
    print(data)
    json_data = eval(data)
    user_response_text = json_data["text"].strip()

    cookie_user_id = request.cookies.get("userid2bot")

    if len(user_response_text) == 0:
        cookie_user_id = str(uuid.uuid4())

        user_session_state = DialogSessionState(cookie_user_id)
        user_current_turn = 1

        try:
            text_response = globals.chat_engine.call(user_current_turn, user_session_state, user_response_text)
        except Exception as e:
            log_str = traceback.format_exc(limit=10)
            logging.getLogger("system_log").error(log_str)
            text_response = "Internal Error"

        globals.user_state[cookie_user_id] = [user_session_state, user_current_turn]

        current_response = make_response(jsonify({'text': text_response.replace("\n", "")}), 200)
        current_response.set_cookie("userid2bot", cookie_user_id)
    else:
        user_session_state, user_current_turn = globals.user_state[cookie_user_id]
        user_current_turn += 1
        text_response = globals.chat_engine.call(user_current_turn, user_session_state, user_response_text)
        globals.user_state[cookie_user_id] = [user_session_state, user_current_turn]
        current_response = make_response(jsonify({'text': text_response.replace("\n", "")}), 200)

    return current_response


@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, session_id, Set-Cookie')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS,HEAD')
    response.headers.add("Access-Control-Allow-Credentials", "true")
    response.headers['Access-Control-Allow-Origin'] = 'http://localhost'
    return response


@app.before_request
def before_request():
    pass


if __name__ == "__main__":

    with open(sys.argv[1], 'r') as f:
        configure_obj = OnlineConfigure(**json.load(f))

    initialize_logger(configure_obj.log_configure)
    globals.online_info_logger = OnlineInfoLogger()
    globals.qa_server = QAServer(configure_obj.qa_configure)

    globals.search_warehouse_server = SearchWarehouse(configure_obj.search_warehouse_configure)
    globals.entity_warehouse_server = EntityWarehouse(configure_obj.entity_warehouse_configure)

    globals.nlp_processor = LanguageProcessor(configure_obj.nlu_configure)
    globals.dialog_graph = DialogGraph(configure_obj.dialog_graph_configure)
    globals.short_sentence_search_server = ShortSentenceSearch(configure_obj.short_sentence_search_configure)
    globals.bm25_sentence_similarity_server = BM25SentenceSimilarity(configure_obj.bm25ss_configure)
    globals.intent_classifier_server = IntentClassifier(configure_obj.intent_classifier_configure)
    globals.entity_extension_server = EntityExtensionWrapper(configure_obj.entity_extension_configure)
    globals.general_response_generator = GeneralResponseGenerator(configure_obj.topic_category_configure)
    globals.chat_engine = ChatEngine()
    globals.user_state = defaultdict()

    app.run(host='localhost', debug=True, port=5000, use_reloader=False)
