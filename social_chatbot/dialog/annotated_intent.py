import copy
import json
import globals
import random
from dialog.schema import GraphBaseObj
from dialog.schema import QuestionCondition

from collections import defaultdict
from online.online_service.short_sentence_search_service import SentenceSearchConstraint


class AnnotatedIntent(GraphBaseObj):

    def __init__(self,
                 id,
                 sample_queries,
                 grounding_id,
                 search_id,
                 intent_entity_type,
                 question_entity_type,
                 questions):

        super().__init__(id, self.__class__.__name__)
        self.sample_query_template = sample_queries
        self.grounding_id = grounding_id
        self.search_id = search_id
        self.entity_type = intent_entity_type
        self.question_entity_type = question_entity_type
        self.questions = defaultdict()
        for question_condition, question_id in questions.items():
            self.questions[QuestionCondition[question_condition]] = question_id

        self.initialize(self.sample_query_template)
        self.sample_queries = copy.deepcopy(self.samples_without_entity_slot)
        self.processed_sample_queries = []
        pass

    def replace_entity_slot_with_id(self, type_mapping):

        for type_id in self.entity_type:
            entity_slot = "[" + str(type_id) + "_object]"
            for one_sample in self.samples_with_entity_slot:
                if one_sample.find(entity_slot) >= 0:
                    self.sample_queries.append(one_sample.replace(entity_slot, type_mapping[type_id]))

        for type_id in self.entity_type:
            for one_sample in self.samples_with_entity_slot:
                if one_sample.find(self.entity_slot_base) >= 0:
                    self.sample_queries.append(one_sample.replace(self.entity_slot_base, type_mapping[type_id]))

    def execute(self, exe_parameter):

        # handle grouding
        current_grounding_id = self.prepare_grounding_id(exe_parameter)
        intent_grounding_str = ""
        if current_grounding_id != "":
            intent_grounding_str = globals.dialog_graph.get_grounding(current_grounding_id).execute(exe_parameter)
        exe_parameter.current_grounding_id = current_grounding_id
        exe_parameter.add_to_log("intent_grounding_str", intent_grounding_str)

        # handle search
        # step1: find entity for search
        random_intent_entity_id, random_intent_entity_type, intent_entity_random_name = \
            self._random_select_execute_entity_candidate(exe_parameter.user_query)
        exe_parameter.add_to_log("random_intent_entity_id", random_intent_entity_id)
        exe_parameter.add_to_log("random_intent_entity_type", random_intent_entity_type)
        exe_parameter.add_to_log("intent_entity_random_name", intent_entity_random_name)

        # step2: search
        ranked_sentence = None
        intent_search_str = ""
        search_constraint = SentenceSearchConstraint(**json.loads(globals.default_sentence_search_constraint_str))
        search_constraint.entity_list = []
        if random_intent_entity_id is not None:
            search_constraint.entity_list = [random_intent_entity_id]

        if self.search_id != "no_search":
            if len(search_constraint.entity_list) == 0:
                # TODO: choose an entity based on previous entity to enforce the news search
                # TODO: or create a list of entities such as 欧冠，NBA etc to enforce the news search
                general_response_result = globals.general_response_generator.init_response(exe_parameter, False,
                                                                                           exe_parameter.dialog_state.topic)
                exe_parameter.add_to_log("general_response_result_no_search_intent", general_response_result.to_json())
                intent_search_str = general_response_result.search_str
            else:
                search_result = \
                    globals.short_sentence_search_server.search_sentence(exe_parameter.user_query, search_constraint)
                random_sentence = search_result.get_random_sentence_from_topk(3)
                if random_sentence is not None:
                    intent_search_str = random_sentence.raw_sentence
                    exe_parameter.current_turn_search_index.add(random_sentence.sentence_index)
                    exe_parameter.current_search_constraint = search_result.search_query_dict
                    exe_parameter.current_search_result = random_sentence
                else:
                    # need a news_search to provide something else
                    # currently, I am thinking from query's entities,
                    # go through others and find one which has related sentences.
                    # if none of them have related sentence. Find a category such as 欧冠，NBA related the one of entities.
                    general_response_result = globals.general_response_generator.init_response(exe_parameter, False,
                                                                                               exe_parameter.dialog_state.topic)
                    exe_parameter.add_to_log("general_response_result_after_intent_with_entity_but_no_result",
                                             general_response_result.to_json())

                    intent_search_str = '不好意思，没有找到最近的关于%s的新闻，是不是已经过气或者不流行了。' % \
                                        intent_entity_random_name
                    intent_search_str = intent_search_str + general_response_result.search_str

        exe_parameter.add_to_log("intent_search_str", intent_search_str)

        # handle question
        intent_question_str = ""
        current_question_id, question_entity_id = self.prepare_question_id_and_entity_id(exe_parameter, ranked_sentence)

        if current_question_id == "":
            exe_parameter.current_question_id = current_question_id
            exe_parameter.current_question_entity_id = question_entity_id
        else:
            exe_parameter.current_question_id = current_question_id
            exe_parameter.current_question_entity_id = question_entity_id
            intent_question_str = globals.dialog_graph.get_question(current_question_id).execute(exe_parameter)
        exe_parameter.add_to_log("intent_question_str", intent_question_str)

        exe_parameter.current_intent_id = self.id
        exe_parameter.response_str_list = [intent_grounding_str, intent_search_str, intent_question_str]

        pass

    def process_sample_queries(self):
        for one_query in self.sample_queries:
            self.processed_sample_queries.append(globals.nlp_processor.generate_query(one_query))

    def to_json(self):

        question = {}
        for condition, question_id in self.questions.items():
            question[condition.name] = "question id: " + " ".join(question_id)

        processed_queries = [query.to_api() for query in self.processed_sample_queries]

        return {
            "sample_query_template": self.sample_query_template,
            "grounding_id": self.grounding_id,
            "search_id": self.search_id,
            "intent_entity_type": self.entity_type,
            "question_entity_type": self.question_entity_type,
            "question": question,
            "sample_queries": self.sample_queries,
            "processed_queries": processed_queries
        }

    def prepare_grounding_id(self, exe_parameter):

        # assure that selection grounding id either not need entity or it has an entity to replace the slot
        grounding_candidates = []
        for grounding_id in self.grounding_id:
            grounding_entity_type = globals.dialog_graph.get_grounding(grounding_id).entity_type
            if len(grounding_entity_type) == 0:
                grounding_candidates.append(grounding_id)
                continue
            for entity_type in exe_parameter.user_query.type2entity:
                if entity_type in grounding_entity_type:
                    grounding_candidates.append(grounding_id)

        if len(grounding_candidates) == 0:
            return ""

        return random.choice(grounding_candidates)

    def prepare_question_id_and_entity_id(self, exe_parameter, ranked_sentence):

        # assure that if return_entity_id is empty, then question of return_question_id does not need an entity
        # assure that if return_entity_id is not empty, then question of return_question_id can accept an entity
        # TODO: need a check function to make sure grounding/intent/question.json satisfy some rules, such as
        # TODO: MultipleEntity->question_id whose corresponding question does not need an entity

        return_question_id = ""
        return_entity_id = ""

        if len(self.question_entity_type) > 0:
            # inside this intent, require entity for some questions

            entity_candidate_from_user_query = self.generate_entity_candidate(exe_parameter.user_query,
                                                                              self.question_entity_type)
            if len(entity_candidate_from_user_query) > 0:
                # from user query, we already have applicable entity for question
                random_entity_type = random.choice(list(entity_candidate_from_user_query.keys()))
                if len(entity_candidate_from_user_query[random_entity_type]) > 1:
                    if QuestionCondition.MultipleEntity in self.questions:
                        return_question_id = random.choice(self.questions[QuestionCondition.MultipleEntity])
                else:
                    if QuestionCondition.SingleEntity in self.questions:
                        return_question_id = random.choice(self.questions[QuestionCondition.SingleEntity])
                        return_entity_id = entity_candidate_from_user_query[random_entity_type][0]

            elif ranked_sentence is not None:
                # try to find applicable entity for question from search string
                search_str = ranked_sentence.raw_sentence
                search_str_query = globals.nlp_processor.generate_query(search_str)
                entity_candidate_from_search_str = self.generate_entity_candidate(search_str_query,
                                                                                  self.question_entity_type)

                if len(entity_candidate_from_search_str) == 0:
                    if QuestionCondition.NoEntity in self.questions:
                        return_question_id = random.choice(self.questions[QuestionCondition.NoEntity])
                else:
                    random_entity_type = random.choice(list(entity_candidate_from_search_str.keys()))
                    if len(entity_candidate_from_search_str[random_entity_type]) > 1:
                        if QuestionCondition.MultipleEntity in self.questions:
                            return_question_id = random.choice(self.questions[QuestionCondition.MultipleEntity])
                    else:
                        if QuestionCondition.SingleEntity in self.questions:
                            return_question_id = random.choice(self.questions[QuestionCondition.SingleEntity])
                            return_entity_id = entity_candidate_from_search_str[random_entity_type][0]

        if return_question_id == "":
            if QuestionCondition.RandomSelection not in self.questions:
                log_str = "No question id is found due to none of question condition is satisfied in intent [%s]" % self.id
                self.system_logger.error(log_str)
                print(log_str)
                return return_question_id, return_entity_id
            else:
                return_question_id = random.choice(self.questions[QuestionCondition.RandomSelection])

        return return_question_id, return_entity_id

