from pymongo import MongoClient


class MongoDB(object):
    def __init__(self,
                 db_server_ip="10.93.128.143",
                 db_server_port=27017,
                 database_name="tencent_kg",
                 user='admin',
                 pwd='12345678'):
        self.host = '%s:%s' % (db_server_ip, db_server_port)
        self.client = MongoClient(host=db_server_ip,
                                  port=db_server_port,
                                  username=user,
                                  password=pwd,
                                  authSource="admin")
        self.db = self.client[database_name]

    def save_to_mongodb(self, collection_name, document):
        collection = self.db[collection_name]
        if not self.is_id_exist(collection_name, document["_id"]):
            insert_id = collection.insert_one(document)
            return insert_id
        else:
            return None

    def is_id_exist(self, collection_name, doc_id):
        if len(list(self.db[collection_name].find({"_id": doc_id}))) == 0:
            return False
        else:
            return True

    def save_to_mongodb_many(self, collection_name, document, ordered=False):
        collection = self.db[collection_name]
        document_unique = []
        unique_id = set()
        for doc in document:
            if doc not in document_unique and \
                    not self.is_id_exist(collection_name, doc["_id"]) and \
                    doc["_id"] not in unique_id:
                document_unique.append(doc)
                unique_id.add(doc["_id"])

        if len(document_unique) > 0:
            insert_result = collection.insert_many(document_unique)
            return insert_result
        else:
            return None

    def update_one_row(self, collection_name, search_query, update_query):

        collection = self.db[collection_name]
        collection.update_one(search_query, update_query)

    def find_entity_by_query(self, collection_name, query):

        collection = self.db[collection_name]
        search_results = list(collection.find(query))
        if len(search_results) == 0:
            return None
        return search_results

    def find_entity_by_property_query(self, collection_name, property_name, query, unique=True):

        return self.find_entity_by_query(collection_name, {property_name: query})

    def find_entry_by_name(self, collection_name, entity_name):
        
        result = self.find_entity_by_property(collection_name, "name", entity_name)
        return result

    def find_all_entries(self, collection_name):

        collection = self.db[collection_name]
        results = list(collection.find())
        return results

    def find(self, collection_name, entity_name, entity_property):

        search_results = self.find_entity_by_property(collection_name, "name", entity_name)
        if entity_property in search_results:
            return search_results[entity_property]
        else:
            print("No found information from db for the combination of collection_name[{}], entity_name[{}] and property[{}]".format(collection_name, entity_name, entity_property))
            return None

    def find_entity_by_property(self, collection_name, property_name, property_value, unique=True):

        collection = self.db[collection_name]
        search_query = {property_name: [property_value]}
        search_results = list(collection.find(search_query))
        if len(search_results) == 0:
            return None
        elif len(search_results) == 1:
            return search_results[0]
        elif not unique:
            return search_results
        else:
            search_results = [i for i in search_results if i["_id"].find("_") == -1]
            if all([True if "popular" in i else False for i in search_results]):
                search_results.sort(key=lambda i: int(i["popular"][0]), reverse=True)
            return search_results[0]

    def get_all_properties(self, collection_name):

        collection = self.db[collection_name]
        mapper = Code("""
                      function(){
                        for (var key in this) {emit(key, null);}
                      }
                      """)
        reducer = Code("""
                       function(key, stuff){
                         return null;
                       }
                       """)
        result = collection.map_reduce(mapper, reducer, "MPresult").distinct("_id")
        self.db.MPresult.drop()
        return result
