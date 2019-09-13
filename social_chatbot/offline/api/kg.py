import functools
import globals
from commons.db.mongodb import MongoDB


class KgApi(object):
    def __init__(self, local_configure):
        self.host = local_configure['db_host']
        self.port = int(local_configure['db_port'])
        self.db_name = local_configure['db_name']
        self.user = local_configure['user']
        self.pwd = local_configure['pwd']
        self.kg_collection_name = local_configure['kg_collection_name']
        self.linker_collection_name = local_configure['linker_collection_name']

        self.client = MongoDB(self.host, self.port, self.db_name, self.user, self.pwd)
        self.collection_kg = self.client.db[self.kg_collection_name]
        self.collection_mentions = self.client.db[self.linker_collection_name]

    @functools.lru_cache(maxsize=None)
    def get_entry_by_kbid(self, kbid):
        query = {'_id': kbid}
        response = self.collection_kg.find_one(query)
        if response:
            return dict(response)
        else:
            return {}

    @functools.lru_cache(maxsize=None)
    def search_entry_by_name(self, name):
        query = {'mention': name.lower()}
        response = self.collection_mentions.find_one(query)
        if response:
            return response['entities']
        else:
            return []

    def obtain_entity_extension(self, kbid, extension_type):
        res = globals.entity_extension_server.generate_sentence_and_entity(kbid, extension_type)
        return {'sentence':res.sentence, '_id_obj':res.extended_id_list, 'popular':res.pop_val, 'status':res.status.name}
