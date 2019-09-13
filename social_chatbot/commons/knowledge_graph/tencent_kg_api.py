# -*- coding: utf-8 -*-
import re
import requests
import json
import time
import random

class OfficialTencentKGAPI(object):

    def __init__(self):
        # self.entity_retrieval_server_ip_pool = ["http://100.115.129.169:6297/api", "http://10.175.123.92:6297/api"]
        self.entity_retrieval_server_ip_pool = ["http://100.115.135.106:6297/api"]
        self.entity_retrieval_server_ip_num = len(self.entity_retrieval_server_ip_pool)
        self.entity_link_server_ip = "http://100.102.36.21:9011/entity_linking"
        self.qa_server_ip = "http://qa.ainlp.oa.com/nlp_kore_online.php"

        self.headers = {}
        self.headers["Content-Type"] = "application/json"

        self.entity_input = {}
        self.entity_input["operation"] = "subgraph"
        self.entity_input["auth"] = "virtual_human"

        self.entity_relation = {}
        self.entity_relation["operation"] = "relation"
        self.entity_relation["auth"] = "virtual_human"
        self.entity_relation["name"] = []

        self.entity_with_same_property = {}
        self.entity_with_same_property["operation"] = "query"
        self.entity_with_same_property["auth"] = "virtual_human"

        self.entity_link_input = {}
        self.entity_link_input["type"] = "raw"
        self.entity_link_input["body"] = ""

        self.qa_input = {}
        self.qa_input['query'] = ""
        self.qa_input['user_id'] = "ailab_dialog_dm"
        self.qa_input['session_id'] = "123456789"

        self.default_return = '{"status":"false", "result":{}}'

    def retrieve_entity(self, text, is_id):

        if len(text) == 0:
            return self.default_return

        if not is_id:
            self.entity_input["name"] = text
            self.entity_input.pop("id", None)
        else:
            self.entity_input["id"] = text
            self.entity_input.pop("name", None)

        sleep_time = 20
        while True:
            entity_retrieval_server_ip = self.entity_retrieval_server_ip_pool[int(self.entity_retrieval_server_ip_num * random.random())]
            r = requests.post(entity_retrieval_server_ip, data=json.dumps(self.entity_input), headers=self.headers)
            json_obj = json.loads(r.content.decode("utf-8"))
            result = json_obj.get("result", None)
            if type(result) == dict:
                return result
            elif result is not None:
                print(result)
            if int(r.status_code) != 200:
                return self.default_return
            print("Reset Connection! Wait for {} seconds!".format(sleep_time))
            time.sleep(sleep_time)

        # return r.text

    def link_entities(self, text):

        if len(text) == 0:
            return self.default_return

        self.entity_link_input['body']= text
        r = requests.post(self.entity_link_server_ip, data=json.dumps(self.entity_link_input), headers=self.headers)
        if int(r.status_code) != 200:
            return self.default_return

        content_str = r.content.decode("utf-8")
        json_obj = json.loads(content_str)
        all_entities = re.findall(r'{{.*?}}', json_obj['body'])
        entity_list = []
        for entity in all_entities:
            name_id = entity[2:-2].split("||")
            name_id_dict ={}
            name_id_dict[name_id[-1]] = name_id[0]
            entity_list.append(name_id_dict)
        json_obj['entity_list'] = entity_list

        return json.dumps(json_obj)

    def qa_retrieve(self, question):

        if len(question) == 0:
            return self.default_return

        self.qa_input['query']= question
        r = requests.post(self.qa_server_ip, data=json.dumps(self.qa_input), headers=self.headers)
        if int(r.status_code) != 200:
            return self.default_return
        return r.content.decode("utf-8")

    def retrieve_entity_relation(self, entity1, entity2):

        if len(entity1) == 0 or len(entity2) == 0:
            return self.default_return

        self.entity_relation["name"].clear()
        self.entity_relation["name"].append(entity1)
        self.entity_relation["name"].append(entity2)
        entity_retrieval_server_ip = self.entity_retrieval_server_ip_pool[int(self.entity_retrieval_server_ip_num * random.random())]
        r = requests.post(entity_retrieval_server_ip, data=json.dumps(self.entity_relation), headers=self.headers)
        if int(r.status_code) != 200:
            return self.default_return

        return r.content.decode("utf-8")

    def retrieve_relevant_entities(self, subject, equal_property, property_value):

        self.entity_with_same_property["condition"] = {}
        self.entity_with_same_property["condition"]["and"] = [{"equal": property_value, "property": [equal_property]}]
        self.entity_with_same_property["property"] = ["相关实体"]
        self.entity_with_same_property["subject"] = {"name" : subject}

        entity_retrieval_server_ip = self.entity_retrieval_server_ip_pool[int(self.entity_retrieval_server_ip_num * random.random())]
        r = requests.post(entity_retrieval_server_ip,
                          data=json.dumps(self.entity_with_same_property),
                          headers=self.headers)
        if int(r.status_code) != 200:
            return self.default_return

        return r.content.decode("utf-8")

    def retrieve_relevant_entities2(self, subject):

        self.entity_with_same_property["condition"] = {}
        self.entity_with_same_property["condition"]["and"] = [{"equal": subject, "property": ["精选别名"]}]

        entity_retrieval_server_ip = self.entity_retrieval_server_ip_pool[int(self.entity_retrieval_server_ip_num * random.random())]
        r = requests.post(entity_retrieval_server_ip,
                          data=json.dumps(self.entity_with_same_property),
                          headers=self.headers)
        if int(r.status_code) != 200:
            return self.default_return

        return r.content.decode("utf-8")
