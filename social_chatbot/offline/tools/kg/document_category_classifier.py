import codecs
import globals
import json
import logging
import re

from collections import defaultdict


class CategoryResult(object):

    def __init__(self, type, res):
        self.type = type
        self.res = res


class SportNewsCategoryClassifier(object):

    def __init__(self, category_file):

        self.system_logger = logging.getLogger("system_log")

        json_str = codecs.open(category_file, 'r', 'utf-8').read()
        json_obj = json.loads(json_str)

        if "defined_category" not in json_obj:
            log_str = "defined_category is not in file [%s]"%category_file
            self.system_logger.error(log_str)
            print(log_str)
            return
        self.defined_category = json_obj["defined_category"]

        if "detail_category" not in json_obj:
            log_str = "detail_category is not in file [%s]"%category_file
            self.system_logger.error(log_str)
            print(log_str)
            return
        self.detail_category = json_obj["detail_category"]

        if "well_format_category" not in json_obj:
            log_str = "well_format_category is not in file [%s]"%category_file
            self.system_logger.error(log_str)
            print(log_str)
            return
        self.well_format_category = json_obj["well_format_category"]

        if "well_format_source" not in json_obj:
            log_str = "well_format_source is not in file [%s]"%category_file
            self.system_logger.error(log_str)
            print(log_str)
            return
        self.well_format_source = json_obj["well_format_source"]

        if "accept_types" not in json_obj:
            log_str = "accept_types is not in file [%s]"%category_file
            self.system_logger.error(log_str)
            print(log_str)
            return
        self.accept_types = set(json_obj["accept_types"])

        if globals.entity_warehouse_server is None:
            log_str = "Please initialize entity_warehouse_server first"
            self.system_logger.error(log_str)
            print(log_str)
            return
        self.entity_warehouse_server = globals.entity_warehouse_server

    def get_category(self, title_entity, content_query, source="", category=""):

        result = CategoryResult("", [])
        if source != "" or category != "":

            if source in self.well_format_source:
                result.res.append(self.well_format_source[source])

            if category in self.well_format_category:
                result.res.append(category)

            if category in self.detail_category:
                result.res.append(self.detail_category[category])

            if len(result.res) > 0:
                result.type = "source"
                result.res = list(set(result.res))
                return result

        predict_value_by_title = self._predict_by_title(title_entity)
        if predict_value_by_title != "":
            result.type = "title"
            result.res = [predict_value_by_title]
            return result

        if content_query is not None:
            predict_value_by_content = self._predict_by_content(content_query.sentence_list)
            if predict_value_by_content != "":
                result.type = "content"
                result.res = [predict_value_by_content]
                return result

            predict_value_by_content_entity = self._predict_by_content_entity(content_query.sentence_list)
            if predict_value_by_content_entity != "":
                result.type = "content_entity"
                result.res = [predict_value_by_content_entity]
                return result

        result.type = "none"
        result.res = ["八卦"]
        return result

    def _predict_by_title(self, title_entity):

        category_vote = defaultdict(int)
        for entity_id in title_entity:
            entity_types = self.entity_warehouse_server.get_type_by_kbid(entity_id)
            if len(set(entity_types).intersection(self.accept_types)) == 0:
                continue
            entity_entry = self.entity_warehouse_server.get_entry_by_kbid(entity_id)

            if "精选上位词" in entity_entry:
                for item in entity_entry["精选上位词"]:
                    for cate in self.defined_category:
                        if item[0].find(cate) >= 0:
                            category_vote[cate] += 1

        sorted_cate = sorted(category_vote.items(), key=lambda x: x[1], reverse=True)
        if len(sorted_cate) == 1:
            return sorted_cate[0][0]
        elif len(sorted_cate) == 0:
            return ""
        elif sorted_cate[0][1] > sorted_cate[1][1]:
            return sorted_cate[0][0]
        else:
            return ""

    def _predict_by_content(self, sentences):

        category_vote = defaultdict(int)
        article_text = "".join(sentence.raw_sentence for sentence in sentences)

        for cate in self.defined_category:
            count = len(list(re.finditer(cate, article_text)))
            category_vote[cate] = count

        for cate in self.detail_category:
            count = len(list(re.finditer(cate, article_text)))
            category_vote[self.detail_category[cate]] += count

        sorted_cate = sorted(category_vote.items(), key=lambda x: x[1], reverse=True)
        if len(sorted_cate) == 1:
            return sorted_cate[0][0]
        elif len(sorted_cate) == 0:
            return ""
        elif sorted_cate[0][1] > sorted_cate[1][1]:
            return sorted_cate[0][0]
        else:
            return ""

    def _predict_by_content_entity(self, sentences):

        category_vote = defaultdict(int)

        for sentence in sentences:
            for entity in sentence.entity_list:
                if entity.entity is not None:
                    entity_id = entity.entity.kbid
                    entity_types = self.entity_warehouse_server.get_type_by_kbid(entity_id)
                    if len(set(entity_types).intersection(self.accept_types)) == 0:
                        continue
                    entity_entry = self.entity_warehouse_server.get_entry_by_kbid(entity_id)

                    if "精选上位词" in entity_entry:
                        for item in entity_entry["精选上位词"]:
                            for cate in self.defined_category:
                                if item[0].find(cate) >= 0:
                                    category_vote[cate] += 1

        sorted_cate = sorted(category_vote.items(), key=lambda x: x[1], reverse=True)
        if len(sorted_cate) == 1:
            return sorted_cate[0][0]
        elif len(sorted_cate) == 0:
            return ""
        elif sorted_cate[0][1] > sorted_cate[1][1]:
            return sorted_cate[0][0]
        else:
            return ""
