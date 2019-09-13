from commons.entity.extension.entity_extension_wrapper import EntityExtensionStatus
from enum import Enum
from online.online_service.execute_parameter import EntityStatusForSearch
from online.online_service.short_sentence_search_service import SentenceSearchConstraint

import codecs
import globals
import json
import logging
import random


class GeneralResponseType(Enum):

    ExtensionSucceedWithSearch = 1
    ExtensionSucceedWithoutSearch = 2
    ExtensionSucceedWithOnlySearch = 3
    ExtensionFail = 4
    SearchSucceed = 5
    SearchFail = 6
    Init = 7


class GeneralResponse(object):

    def __init__(self, response_type, extension_str, search_str, init_entity, execute_entity, extend_entity):

        self.response_type = response_type
        self.extension_str = extension_str
        self.search_str = search_str
        self.init_entity = init_entity
        self.execute_entity = execute_entity
        self.extend_entity = extend_entity

    def to_json(self):
        return {
            "response_type": self.response_type.name,
            "extension_str": self.extension_str,
            "search_str": self.search_str,
            "init_entity": self.init_entity,
            "extend_entity": self.extend_entity
        }


class GeneralResponseGenerator(object):

    def __init__(self, topic_category_configure):

        self.system_logger = logging.getLogger("system_log")
        self.entity_warehouse_server = globals.entity_warehouse_server
        self.entity_extension_wrapper = globals.entity_extension_server
        self.short_sentence_search_server = globals.short_sentence_search_server
        self.dialog_graph = globals.dialog_graph
        self.shuodao = self.dialog_graph.get_grounding("系统_说到")
        self.tingshuo = self.dialog_graph.get_grounding("系统_听说")
        self.jiran_shuodao = self.dialog_graph.get_grounding("系统_既然说到")
        self.nizhdaome = self.dialog_graph.get_grounding("系统_你知道么")
        self.chushihua = self.dialog_graph.get_grounding("系统_初始化话题")

        json_str = codecs.open(topic_category_configure.sports_topic_category_file, 'r', 'utf-8').read()
        json_obj = json.loads(json_str)
        self.sports_category = []
        if "defined_category" not in json_obj:
            log_str = "sports defined_category is not in file [%s]" % topic_category_configure.sports_topic_category_file
            self.system_logger.error(log_str)
            print(log_str)
        self.sports_category.extend(json_obj["defined_category"])

        if "well_format_category" not in json_obj:
            log_str = "well_format_category is not in file [%s]" % topic_category_configure.sports_topic_category_file
            self.system_logger.error(log_str)
            print(log_str)
        self.sports_category.extend(json_obj["well_format_category"])

        pass

    def generate_general_search_response(self, execute_parameter):

        # decide entity status for search
        execute_parameter.decide_entity_status_for_search()

        # dialog flow based on entity status for search
        if execute_parameter.current_entity_status_for_search == EntityStatusForSearch.NoEntity:
            entities_ranked_by_recent_then_freq = execute_parameter.dialog_state.entities_ranked_by_recent_then_freq()
            if len(entities_ranked_by_recent_then_freq) > 0:
                general_response_result = self._apply_extension(execute_parameter, entities_ranked_by_recent_then_freq)
            else:
                # current query and all the previous entities has no entity,
                # recommend an init news or grounding
                general_response_result = self.init_response(execute_parameter, True, execute_parameter.dialog_state.topic)
        elif execute_parameter.current_entity_status_for_search == EntityStatusForSearch.AllExistEntity:
            general_response_result = \
                self._apply_extension(execute_parameter, execute_parameter.exist_entity_from_current_query)
        elif execute_parameter.current_entity_status_for_search == EntityStatusForSearch.AllNewEntity:
            general_response_result = \
                self._apply_search(execute_parameter, execute_parameter.new_entity_from_current_query)
        elif execute_parameter.current_entity_status_for_search == EntityStatusForSearch.ExistAndNewEntity:
            # if search does not work for new entity, use extension for exist
            general_response_result = \
                self._apply_search(execute_parameter, execute_parameter.new_entity_from_current_query)
            if general_response_result.response_type == GeneralResponseType.SearchFail:
                general_response_result = \
                    self._apply_extension(execute_parameter, execute_parameter.exist_entity_from_current_query)
        else:
            log_str = "Unsupported EntityStatus: [%s]"% execute_parameter.current_entity_status_for_search.name
            print(log_str)
            general_response_result = GeneralResponse(GeneralResponseType.SearchFail, "")

        if general_response_result.response_type in [GeneralResponseType.SearchFail, GeneralResponseType.ExtensionFail]:
            general_response_result = self.init_response(execute_parameter, True, execute_parameter.dialog_state.topic)

        execute_parameter.add_to_log("general_response_result", general_response_result.to_json())
        return self.transfer_result_to_string(general_response_result)

    def transfer_result_to_string(self, general_response_result):

        response_type = general_response_result.response_type
        if response_type == GeneralResponseType.ExtensionSucceedWithSearch:
            partial_one = self.shuodao.execute(None) + self.entity_warehouse_server.get_random_name_by_kbid(
                general_response_result.execute_entity[0]) + "，"
            partial_two = self.tingshuo.execute(None) + general_response_result.extension_str + "。"
            partial_three = self.jiran_shuodao.execute(None) + self.entity_warehouse_server.get_random_name_by_kbid(
                general_response_result.execute_entity[0]) + "，"
            partial_four = self.nizhdaome.execute(None) + general_response_result.search_str + "。"
            return [partial_one + partial_two, partial_three + partial_four]

        elif response_type == GeneralResponseType.ExtensionSucceedWithoutSearch:
            partial_one = self.shuodao.execute(None) + self.entity_warehouse_server.get_random_name_by_kbid(
                general_response_result.execute_entity[0]) + "，"
            partial_two = self.tingshuo.execute(None) + general_response_result.extension_str + "。"
            return [partial_one + partial_two]

        elif response_type == GeneralResponseType.ExtensionSucceedWithOnlySearch or response_type == GeneralResponseType.SearchSucceed:
            partial_one = self.shuodao.execute(None) + self.entity_warehouse_server.get_random_name_by_kbid(
                random.choice(general_response_result.init_entity)) + "，"
            partial_four = self.nizhdaome.execute(None) + general_response_result.search_str + "。"
            return [partial_one + partial_four]

        elif response_type == GeneralResponseType.Init:
            return [general_response_result.search_str]

        else:
            log_str = "Not supported GeneralResponseType [%s] in transfer_result_to_string." % response_type.name
            print(log_str)
            self.system_logger.error(log_str)
            return ""

    def _apply_extension(self, execute_parameter, entity_list):

        '''
            use entity list to extension.
            If extension works, use the extended entity to do search. No matter search works or not, extension succeeds.
            If extension does not work, use entity list and query to do search.
            If search fails again, it means extension fails. Otherwise, we define extension succeed.

            When extension works and search works, a grounding should be between them.
        '''

        extension_str = ""
        search_str = ""
        start_entity = entity_list
        execute_entity = entity_list
        extension_entity = []

        extension_result_in_apply_extension = self.entity_extension_wrapper.generate_sentence_and_entity(entity_list, execute_parameter.dialog_state.extension_index)
        execute_parameter.add_to_log("extension_result_in_apply_extension",
                                     extension_result_in_apply_extension.to_json())
        if extension_result_in_apply_extension.status in [EntityExtensionStatus.OneOrderOneEntity,
                                                          EntityExtensionStatus.TwoOrderOneEntity,
                                                          EntityExtensionStatus.TwoOrderTwoEntity]:
            # extension works
            extension_entity = extension_result_in_apply_extension.extended_id_list
            execute_entity = extension_result_in_apply_extension.executed_id_list
            extension_str = extension_result_in_apply_extension.sentence
            execute_parameter.entity_from_current_response.extend(extension_entity)
            execute_parameter.current_turn_extension_index.add(extension_result_in_apply_extension.index)

            entity_id_for_search = extension_result_in_apply_extension.extended_id_list
            search_constraint = SentenceSearchConstraint(**json.loads(globals.default_sentence_search_constraint_str))
            search_constraint.entity_list = entity_id_for_search

            search_result_in_apply_extension = \
                self.short_sentence_search_server.search_sentence(execute_parameter.user_query, search_constraint)

            random_sentence = search_result_in_apply_extension.get_random_sentence_from_topk(3, execute_parameter.dialog_state.search_index)
            if random_sentence is not None:
                response_type = GeneralResponseType.ExtensionSucceedWithSearch
                # TODO: a grounding is need between entity extension and search
                search_str = random_sentence.raw_sentence
                execute_parameter.current_turn_search_index.add(random_sentence.sentence_index)
                execute_parameter.add_to_log("search_result_in_apply_extension", random_sentence.to_json())
                execute_parameter.add_to_log("search_constraint_in_apply_extension",
                                             search_result_in_apply_extension.search_query_dict)
            else:
                response_type = GeneralResponseType.ExtensionSucceedWithoutSearch

        else:
            # extension does not work
            search_constraint = SentenceSearchConstraint(**json.loads(globals.default_sentence_search_constraint_str))
            search_constraint.entity_list = entity_list

            search_result_in_apply_extension = \
                self.short_sentence_search_server.search_sentence(execute_parameter.user_query, search_constraint)
            random_sentence = search_result_in_apply_extension.get_random_sentence_from_topk(3, execute_parameter.dialog_state.search_index)

            if random_sentence is not None:
                response_type = GeneralResponseType.ExtensionSucceedWithOnlySearch
                search_str = random_sentence.raw_sentence
                execute_parameter.current_turn_search_index.add(random_sentence.sentence_index)
                execute_parameter.add_to_log("search_result_in_apply_extension", random_sentence.to_json())
                execute_parameter.add_to_log("search_constraint_in_apply_extension",
                                             search_result_in_apply_extension.search_query_dict)
            else:
                response_type = GeneralResponseType.ExtensionFail

        return GeneralResponse(response_type, extension_str, search_str, start_entity, execute_entity, extension_entity)

    def _apply_search(self, execute_parameter, entity_list):

        '''
            use entity list to do search.
            If search works, means search succeeds.
            If search does not work, means search fails and use init_response() instead
        '''

        search_str = ""
        start_entity = entity_list
        execute_entity = entity_list

        # search constraint
        search_constraint = SentenceSearchConstraint(**json.loads(globals.default_sentence_search_constraint_str))
        search_constraint.entity_list = entity_list

        search_result_in_apply_search = \
            self.short_sentence_search_server.search_sentence(execute_parameter.user_query, search_constraint)
        random_sentence = search_result_in_apply_search.get_random_sentence_from_topk(3, execute_parameter.dialog_state.search_index)

        if random_sentence is not None:
            # search works
            response_type = GeneralResponseType.SearchSucceed
            search_str = random_sentence.raw_sentence
            execute_parameter.current_turn_search_index.add(random_sentence.sentence_index)
            execute_parameter.add_to_log("search_result_in_apply_search", random_sentence.to_json())
            execute_parameter.add_to_log("search_constraint_in_apply_search",
                                         search_result_in_apply_search.search_query_dict)
        else:
            # search does not work
            response_type = GeneralResponseType.SearchFail

        return GeneralResponse(response_type, "", search_str, start_entity, execute_entity, [])

    def init_response(self, execute_parameter, need_grounding=True, exist_topic=set()):

        partial_one = ""
        if need_grounding:
            partial_one = self.chushihua.execute(None)
        tried_categories = set()
        while True:
            search_constraint = SentenceSearchConstraint(**json.loads(globals.default_sentence_search_constraint_str))
            search_constraint.entity_list = []
            random_category = random.choice(self.sports_category)
            if random_category in tried_categories or random_category in exist_topic:
                continue
            tried_categories.add(random_category)
            search_constraint.topic_category = [random_category]
            search_constraint.days_ago = 180

            search_result_in_init_response = \
                self.short_sentence_search_server.search_sentence(execute_parameter.user_query, search_constraint)

            random_sentence = search_result_in_init_response.get_random_sentence_from_topk(10)
            if random_sentence is not None:
                search_str = "我这有个" + random_category + "新闻，一起来瞧瞧， " + random_sentence.title
                execute_parameter.add_to_log("search_result_in_init_response", random_sentence.to_json())
                execute_parameter.add_to_log("search_constraint_in_init_response",
                                             search_result_in_init_response.search_query_dict)
                execute_parameter.current_turn_topic.add(random_category)
                break

        return GeneralResponse(GeneralResponseType.Init, "", partial_one + search_str, [], [], [])
