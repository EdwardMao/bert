import json
import requests
import sys
import time

from . import tencent_kg_api
from collections import defaultdict


class InternalKGAPI(object):

    def __init__(self, internal_use):

        self.server_ip = "http://10.12.192.47:9900/kg_service"
        self.official_api = tencent_kg_api.OfficialTencentKGAPI()
        self.internal_use = internal_use

        self.headers = {}
        self.headers["Content-Type"] = "application/json"

        self.post_input = {}
        self.post_input["text"] = {}
        self.post_input["type"] = ""

        self.default_return = '{"status":"false", "result":{}}'

    def _call_service(self, function_name):
        sleep_time = 20
        while True:
            r = requests.post(self.server_ip, data=json.dumps(self.post_input), headers=self.headers)

            if function_name == "qa_retrieve":
                return json.loads(r.json())
            elif function_name == "retrieve_entity":
                result = json.loads(r.json()).get("result", None)
                if type(result) == dict:
                    return r.json()
                elif result is not None:
                    print(result)
                if int(r.status_code) != 200:
                    return self.default_return
                print("Reset Connection! Wait for {} seconds!".format(sleep_time))
                time.sleep(sleep_time)
            else:
                sys.stderr.write("Current InternalKGAPI does not support [%s] operation!\n"%function_name)
                return self.default_return

    def retrieve_entity(self, text, is_id):

        if len(text) == 0:
            return self.default_return

        self.post_input["text"]["entity_name"] = text
        if is_id:
            self.post_input["type"] = "entity_retrieval_by_id"
        else:
            self.post_input["type"] = "entity_retrieval_by_name"

        if not self.internal_use:
            return_dict = self.official_api.retrieve_entity(text, is_id)
            return return_dict

        return_text = self._call_service(sys._getframe().f_code.co_name)
        json_obj = json.loads(return_text)

        return_dict = defaultdict(list)
        if len(json_obj['result']) == 0:
            return return_dict

        for key, value in json_obj['result'].items():
            if isinstance(value, list):
                for element in value:
                    if isinstance(element, dict):
                        return_dict[key].append(element['name'])
                    elif isinstance(element, str):
                        return_dict[key].append(element)
                    else:
                        sys.stderr.write("Unsupported element type [%s]\n" % type(element))
            elif isinstance(value, str):
                return_dict[key].append(value)
            else:
                sys.stderr.write("Unsupported value type [%s]\n"%type(value))

        return return_dict

    def link_entities(self, sentence):

        if len(sentence) == 0:
            return self.default_return

        self.post_input["text"]["sentence"] = sentence
        self.post_input["type"] = "entity_linking"

        if not self.internal_use:
            return_dict = self.official_api.link_entities(sentence)
            return return_dict

        return_text = self._call_service(sys._getframe().f_code.co_name)
        json_obj = json.loads(return_text)

        return_dict = defaultdict(list)
        if len(json_obj['entity_list']) == 0:
            return return_dict

        for key, value in json_obj.items():
            if key == 'entity_list':
                return_dict[key] = value
            else:
                return_dict[key].append(value)

        return_dict['raw_body'] = sentence

        return return_dict

    def qa_retrieve(self, question):

        if len(question) == 0:
            return self.default_return

        self.post_input["text"]["question"] = question
        self.post_input["type"] = "qa"

        if not self.internal_use:
            return_dict = self.official_api.qa_retrieve(question)
            return return_dict

        json_obj = self._call_service(sys._getframe().f_code.co_name)
        return_dict = defaultdict(list)
        if json_obj[0]['result'] == "$":
            return return_dict

        for key, value in json_obj[0].items():
            return_dict[key].append(value)

        return return_dict

    def retrieve_entity_relation(self, entity1, entity2):

        if len(entity1) == 0 or len(entity2) == 0:
            return self.default_return

        self.post_input["text"]["entity1"] = entity1
        self.post_input["text"]["entity2"] = entity2
        self.post_input["type"] = "entity_relation"

        if not self.internal_use:
            return_dict = self.official_api.retrieve_entity_relation(entity1, entity2)
            return return_dict

        return_text = self._call_service(sys._getframe().f_code.co_name)
        json_obj = json.loads(return_text)

        return_dict = defaultdict(list)
        if len(json_obj['result']) == 0:
            return return_dict

        top_result = json_obj['result'][0]
        return_dict['object'] = []
        return_dict['object'].append({top_result['object'][0]["__id"][0]:top_result['object'][0]["name"][0]})
        return_dict['subject'] = []
        return_dict['subject'].append({top_result['subject'][0]["__id"][0]: top_result['subject'][0]["name"][0]})
        return_dict['relation'] = [top_result['relation']]

        return return_dict

    def retrieve_relevant_entities(self, subject, equal_property, property_value):

        self.post_input["text"]["subject"] = subject
        self.post_input["text"]["equal_property"] = equal_property
        self.post_input["text"]["property_value"] = property_value
        self.post_input["type"] = "relevant_entity"

        if not self.internal_use:
            return_dict = self.official_api.retrieve_relevant_entities(subject, equal_property, property_value)
            return return_dict
        
        return_text = self._call_service(sys._getframe().f_code.co_name)
        json_obj = json.loads(return_text)

        return_dict = defaultdict(list)
        if len(json_obj['result']) == 0:
            return return_dict

        return_dict['relevant_entity_list'] = []
        for one_result in json_obj['result']:
            return_dict["relevant_entity_list"].append({one_result["__id"]:one_result["name"], "popular":int(one_result["popular"])})

        return return_dict

    def retrieve_relevant_entities2(self, subject):

        self.post_input["text"]["subject"] = subject
        self.post_input["type"] = "relevant_entity2"

        if not self.internal_use:
            return_dict = self.official_api.retrieve_relevant_entities2(subject)
            return return_dict
        
        return_text = self._call_service(sys._getframe().f_code.co_name)
        json_obj = json.loads(return_text)
        # print(json_obj)
        return_dict = defaultdict(list)
        if len(json_obj['result']) == 0:
            return return_dict

        return_dict['relevant_entity_list'] = []
        for one_result in json_obj['result']:
            return_dict["relevant_entity_list"].append(
                {one_result["__id"]: one_result["name"], "popular": int(one_result["popular"]),
                 "__id": one_result["__id"]})

        return return_dict