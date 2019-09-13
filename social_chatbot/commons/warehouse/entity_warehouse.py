import functools
import json
import random

from commons.db.mongodb import MongoDB
from commons.utils import check_contain_chinese


class EntityWarehouse(object):

    def __init__(self, entity_warehouse_configure):

        self.name = entity_warehouse_configure.name
        self.host = entity_warehouse_configure.host
        self.port = entity_warehouse_configure.port
        self.db_name = entity_warehouse_configure.db_name
        self.user = entity_warehouse_configure.user
        self.pwd = entity_warehouse_configure.pwd
        self.collection_name = entity_warehouse_configure.entity_collection_name
        self.mentions_name = entity_warehouse_configure.entity_mentions_name
        self.memcache_ip_port = entity_warehouse_configure.memcache_ip_port

        self.db_client = MongoDB(self.host, self.port, self.db_name, self.user, self.pwd)
        self.collection = self.db_client.db[self.collection_name]
        self.mentions = self.db_client.db[self.mentions_name]

    @functools.lru_cache(maxsize=None)
    def get_entry_by_kbid(self, kbid):

        query = {'_id': kbid}
        response = self.collection.find_one(query)
        if response:
            return dict(response)
        else:
            return None

    @functools.lru_cache(maxsize=None)
    def get_type_by_kbid(self, kbid):

        return_types = []
        entry_dict = self.get_entry_by_kbid(kbid)
        if "types" in entry_dict:
            for item in entry_dict["types"]:
                return_types.append(int(item[0]))
        return return_types

    @functools.lru_cache(maxsize=None)
    def get_random_name_by_kbid(self, kbid):

        entry_dict = self.get_entry_by_kbid(kbid)
        if isinstance(entry_dict["name"][0], dict):
            return entry_dict["name"][0]["name"]
        return entry_dict["name"][0][0]
        candidate_names = [entry_dict["name"][0][0]]
        if "精选别名" in entry_dict:
            for item in entry_dict["精选别名"]:
                if check_contain_chinese(item[0]):
                    candidate_names.append(item[0])

        return random.choice(candidate_names)

    @functools.lru_cache(maxsize=None)
    def get_entry_by_name(self, name):
        query = {'mention': name.lower()}
        response = self.mentions.find_one(query)
        if response:
            return response['entities']
        else:
            return []

    @functools.lru_cache(maxsize=None)
    def get_response_by_query(self, query):
        return self.mentions.find_one(json.loads(query))
