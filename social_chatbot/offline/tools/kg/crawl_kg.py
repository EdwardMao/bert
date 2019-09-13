from commons.db.mongodb import MongoDB
from offline.tools.offline_tools import OfflineTools
from commons.knowledge_graph import internal_kg_api
from multiprocessing import Process, Queue, Pool
from collections import ChainMap, defaultdict
import numpy as np
import datetime
import os


class EntityType(object):
    def __init__(self, type2number):
        self.type2number = type2number
    
    def isDesiredType(self, type_candidate):
        return type_candidate in self.type2number.keys() or type_candidate in self.type2number.values()

    def getTypeNumber(self, type_str):
        if type_str in self.type2number:
            return self.type2number[type_str]
        else:
            return None
    
    def getTypeName(self, type_number):
        if type_number in self.type2number.values():
            return list(self.type2number.keys())[list(self.type2number.values()).index(type_number)]
        else:
            return None

    def execute(self):
        print("Wrong execute method! Read source codes!")


class BFSKg(OfflineTools):
    def __init__(self, local_configure):
        super().__init__()
        self.seed_entity_id = local_configure["seed_entity_id"]
        self.MongoDB_obj = MongoDB(db_server_ip="10.12.192.47")
        self.internal_use = local_configure["internal_use"]
        self.kg_api = internal_kg_api.InternalKGAPI(self.internal_use)
        self.save_root = local_configure["save_root"]
        self.entityType = EntityType(local_configure["EntityType"])
    
    def execute(self):
        time_start = datetime.datetime.now()
        to_visit_save_file = self.save_root + "to_visit_save_file.npy"
        visited_save_file = self.save_root + "visited_save_file.npy"
        NoID_save_file = self.save_root + "NoID_save_file.npy"

        # If output_filename (.npy file only) already exists, continue to work on existing database. Otherwise, create a new database.
        NoID = []
        entity_id_visited = []
        entity_id_to_visit = [self.seed_entity_id]
        if os.path.isfile(visited_save_file):
            entity_id_visited = list(np.load(visited_save_file, allow_pickle=True))
        if os.path.isfile(to_visit_save_file):
            entity_id_to_visit = list(np.load(to_visit_save_file, allow_pickle=True))
        if os.path.isfile(NoID_save_file):
            NoID = list(np.load(NoID_save_file, allow_pickle=True))

        # for document each epoch
        time_old = datetime.datetime.now()
        # print(entity_id_to_visit)
        while len(entity_id_to_visit) != 0:
            # Dequeue the oldest entity in the queue and set it to visited
            entity_id_current = entity_id_to_visit.pop(0)
            # print(entity_id_visited)

            # Judge if current entity has already been visited
            if entity_id_current not in entity_id_visited:
                data = self.kg_api.retrieve_entity(entity_id_current, False)

                # Judge if the new entity belongs to desinated type. If not, omit it.
                # if type_number not in str(data["type"]):
                #     continue

                # data["popular"] = entity_id_current["popular"]
        
                # 0. set entity "_id"
                data["_id"] = data.pop("__id", None)
                if data["_id"] == None:
                    if data != defaultdict(list, {'_id': None}):
                        NoID.append(data)
                    continue
                else:
                    data["_id"] = data["_id"][0]

                # 1. Save entity into corresponding database
                NeedSaveFlag = True
                for i in data.get("types",[]):
                    if self.entityType.isDesiredType(i):
                        insert_id = self.MongoDB_obj.save_to_mongodb("RelevantType", data)
                        NeedSaveFlag = False
                        break
                if NeedSaveFlag:
                    insert_id = self.MongoDB_obj.save_to_mongodb("FutureUseType", data)
                    NeedSaveFlag = False
                entity_id_visited.append(entity_id_current)

                # 2. explore children of current entity
                children = data.get("相关实体", [])
                # children_expand = []
                # for child in children:
                #     children_expand.extend([i["__id"] for i in self.kg_api.retrieve_relevant_entities2(child)["relevant_entity_list"] if i["__id"] not in children_expand and i["__id"] not in entity_id_visited and i["__id"] not in entity_id_to_visit])

                # 3. Enqueue unvisited children
                entity_id_to_visit.extend([child for child in children if child not in entity_id_visited and child not in entity_id_to_visit])
                # entity_id_to_visit.extend(children_expand)

            if len(entity_id_visited)%20 == 0:
                print("*************************************")
                print(len(entity_id_to_visit))
                print(len(entity_id_visited))
                if os.path.isfile(to_visit_save_file):
                    os.rename(to_visit_save_file, to_visit_save_file[:-4]+"_OLD"+to_visit_save_file[-4:])
                if os.path.isfile(visited_save_file):
                    os.rename(visited_save_file, visited_save_file[:-4]+"_OLD"+visited_save_file[-4:])
                if os.path.isfile(NoID_save_file):
                    os.rename(NoID_save_file, NoID_save_file[:-4]+"_OLD"+NoID_save_file[-4:])
                np.save(to_visit_save_file, entity_id_to_visit)
                np.save(visited_save_file, entity_id_visited)
                np.save(NoID_save_file, NoID)
                time_new = datetime.datetime.now()
                print(time_new - time_start, time_new - time_old)
                time_old = time_new

        print("*************************************")
        print(len(entity_id_to_visit))
        print(len(entity_id_visited))
        if os.path.isfile(to_visit_save_file):
            os.rename(to_visit_save_file, to_visit_save_file[:-4]+"_OLD"+to_visit_save_file[-4:])
        if os.path.isfile(visited_save_file):
            os.rename(visited_save_file, visited_save_file[:-4]+"_OLD"+visited_save_file[-4:])
        if os.path.isfile(NoID_save_file):
            os.rename(NoID_save_file, NoID_save_file[:-4]+"_OLD"+NoID_save_file[-4:])
        np.save(to_visit_save_file, entity_id_to_visit)
        np.save(visited_save_file, entity_id_visited)
        np.save(NoID_save_file, NoID)
        time_new = datetime.datetime.now()
        print(time_new - time_start, time_new - time_old)


def BFSWorker(seeds_to_visit, entity_id_visited, entity_id_to_visit, EntityType, kg_api):
    data_relevant = []
    data_future = []
    entity_id_visited_delta = []
    entity_id_to_visit_delta = []
    NoID_delta = []
    for seed in seeds_to_visit:
        if seed not in entity_id_visited:
            data = kg_api.retrieve_entity(seed, False)

            data["_id"] = data.pop("__id", None)
            if data["_id"] == None:
                if data != defaultdict(list, {'_id': None}):
                    NoID_delta.append(data)
                continue
            else:
                data["_id"] = data["_id"][0]

            NeedSaveFlag = True
            for i in data.get("types",[]):
                if EntityType.isDesiredType(i):
                    NeedSaveFlag = False
                    data_relevant.append(data)
                    break
            if NeedSaveFlag:
                data_future.append(data)
                NeedSaveFlag = False
            entity_id_visited_delta.append(seed)

            children = data.get("相关实体", [])
            entity_id_to_visit_delta.extend([child for child in children if child not in entity_id_visited and child not in entity_id_to_visit and child not in entity_id_to_visit_delta])

    return data_relevant, data_future, entity_id_visited_delta, entity_id_to_visit_delta, NoID_delta


class BFSMultiprocessing(OfflineTools):

    def __init__(self, local_configure):
        super().__init__()
        self.seed_entity_id = local_configure["seed_entity_id"]
        self.internal_use = local_configure["internal_use"]
        self.kg_api = internal_kg_api.InternalKGAPI(self.internal_use)
        self.save_root = local_configure["save_root"]
        self.entityType = EntityType(local_configure["EntityType"])
        self.process_number_max = local_configure["process_number_max"]
        self.batch_size = local_configure["batch_size"]
        self.debug = local_configure["debug"]
        if self.debug:
            self.process_number_max = 5
            self.MongoDB_obj = MongoDB(db_server_ip="10.12.192.47")
        else:
            self.MongoDB_obj = MongoDB()

    def execute(self):
        time_start = datetime.datetime.now()
        processes = []
        to_visit_save_file = self.save_root + "to_visit_save_file.npy"
        visited_save_file = self.save_root + "visited_save_file.npy"
        NoID_save_file = self.save_root + "NoID_save_file.npy"

        # If output_filename (.npy file only) already exists, continue to work on existing database. Otherwise, create a new database.
        NoID = []
        entity_id_visited = []
        entity_id_to_visit = [self.seed_entity_id]
        if os.path.isfile(visited_save_file):
            entity_id_visited = list(np.load(visited_save_file, allow_pickle=True))
        if os.path.isfile(to_visit_save_file):
            entity_id_to_visit = list(np.load(to_visit_save_file, allow_pickle=True))
        if os.path.isfile(NoID_save_file):
            NoID = list(np.load(NoID_save_file, allow_pickle=True))
        

        # for document each epoch
        # Worker Input: seeds_to_visit, entity_id_visited, entity_id_to_visit, EntityType
        # Worker Output: data_relevant, data_future, entity_id_visited_delta, entity_id_to_visit_delta
        time_old = datetime.datetime.now()
        while len(entity_id_to_visit) > 0:
            process_number = int(len(entity_id_to_visit) / self.batch_size)

            if process_number == 0:
                (data_relevant, data_future, entity_id_visited_delta, entity_id_to_visit_delta, NoID_delta) = BFSWorker(entity_id_to_visit, entity_id_visited, entity_id_to_visit, self.entityType, self.kg_api)
                entity_id_to_visit = []
                insert_result = self.MongoDB_obj.save_to_mongodb_many("RelevantType", data_relevant)
                insert_result = self.MongoDB_obj.save_to_mongodb_many("FutureUseType", data_future)
                entity_id_visited.extend(entity_id_visited_delta)
                entity_id_to_visit.extend(entity_id_to_visit_delta)
                NoID.extend(NoID_delta)

                print("*************************************")
                print(len(entity_id_to_visit))
                print(len(entity_id_visited))
                np.save(to_visit_save_file, entity_id_to_visit)
                np.save(visited_save_file, entity_id_visited)
                np.save(NoID_save_file, NoID)
                time_new = datetime.datetime.now()
                print(time_new - time_start, time_new - time_old)
                continue

            if process_number > self.process_number_max:
                process_number = self.process_number_max
            while len(entity_id_to_visit) >= (process_number * self.batch_size):
                parameters = []
                data_relevant = []
                data_future = []
                entity_id_visited_delta = set()
                entity_id_to_visit_delta = set()
                NoID_delta = []

                # Set parameters for multiprocessing
                for i in range(process_number):
                    temp = [entity_id_to_visit[(i*self.batch_size):((i+1)*self.batch_size)], entity_id_visited, entity_id_to_visit, self.entityType, self.kg_api]
                    parameters.append(temp)

                # Multiprocessing
                with Pool(process_number) as p:
                    result_workers = p.starmap(BFSWorker, parameters)

                # delete visited entity in the multiprocessing
                entity_id_to_visit = entity_id_to_visit[((i+1)*self.batch_size):]

                # Merge multiprocessing results
                for i in result_workers:
                    data_relevant.extend(i[0])
                    data_future.extend(i[1])
                    entity_id_visited_delta = entity_id_visited_delta | set(i[2])
                    entity_id_to_visit_delta = entity_id_to_visit_delta | set(i[3])
                    NoID_delta.extend(i[4])

                # print(len(data_relevant))
                # print(len(data_future))
                if self.debug:
                    np.save("/home/markzhao/Desktop/results.npy", result_workers)
                    np.save("/home/markzhao/Desktop/data_relevant.npy", data_relevant)
                    np.save("/home/markzhao/Desktop/data_future.npy", data_future)
                insert_result = self.MongoDB_obj.save_to_mongodb_many("RelevantType", data_relevant)
                insert_result = self.MongoDB_obj.save_to_mongodb_many("FutureUseType", data_future)
                entity_id_visited.extend(list(entity_id_visited_delta))
                entity_id_to_visit.extend(list(entity_id_to_visit_delta))
                NoID.extend(NoID_delta)

                print("*************************************")
                print(len(entity_id_to_visit))
                print(len(entity_id_visited))
                if os.path.isfile(to_visit_save_file):
                    os.rename(to_visit_save_file, to_visit_save_file[:-4]+"_OLD"+to_visit_save_file[-4:])
                if os.path.isfile(visited_save_file):
                    os.rename(visited_save_file, visited_save_file[:-4]+"_OLD"+visited_save_file[-4:])
                if os.path.isfile(NoID_save_file):
                    os.rename(NoID_save_file, NoID_save_file[:-4]+"_OLD"+NoID_save_file[-4:])
                np.save(to_visit_save_file, entity_id_to_visit)
                np.save(visited_save_file, entity_id_visited)
                np.save(NoID_save_file, NoID)
                time_new = datetime.datetime.now()
                print(time_new - time_start, time_new - time_old)
                time_old = time_new

        print("*************************************")
        print(len(entity_id_to_visit))
        print(len(entity_id_visited))
        if os.path.isfile(to_visit_save_file):
            os.rename(to_visit_save_file, to_visit_save_file[:-4]+"_OLD"+to_visit_save_file[-4:])
        if os.path.isfile(visited_save_file):
            os.rename(visited_save_file, visited_save_file[:-4]+"_OLD"+visited_save_file[-4:])
        if os.path.isfile(NoID_save_file):
            os.rename(NoID_save_file, NoID_save_file[:-4]+"_OLD"+NoID_save_file[-4:])
        np.save(to_visit_save_file, entity_id_to_visit)
        np.save(visited_save_file, entity_id_visited)
        np.save(NoID_save_file, NoID)
        time_new = datetime.datetime.now()
        print(time_new - time_start, time_new - time_old)


class MigrateDB(OfflineTools):
    def __init__(self, local_configure):
        super().__init__()
        self.DBIPFrom = local_configure["DBIPFrom"]
        self.DBIPTo = local_configure["DBIPTo"]
        self.DBPortFrom = local_configure["DBPortFrom"]
        self.DBPortTo = local_configure["DBPortTo"]
        self.DBFrom = local_configure["DBFrom"]
        self.DBTo = local_configure["DBTo"]
        self.MongoFrom = MongoDB(db_server_ip=self.DBIPFrom, db_server_port=self.DBPortFrom, database_name=self.DBFrom)
        self.MongoTo = MongoDB(db_server_ip=self.DBIPTo, db_server_port=self.DBPortTo, database_name=self.DBTo)
    
    def execute(self):
        print("From Relevant docs count:", self.MongoFrom.db["RelevantType"].count())
        print("To Relevant docs count:", self.MongoTo.db["RelevantType"].count())
        print("Begin migrating DB ...")
        documents = list(self.MongoFrom.db["RelevantType"].find())
        result1 = self.MongoTo.save_to_mongodb_many("RelevantType", documents)
        print("Relevant Finished!", self.MongoTo.db["RelevantType"].count())

        print("From Relevant docs count:", self.MongoFrom.db["FutureUseType"].count())
        print("To Relevant docs count:", self.MongoTo.db["FutureUseType"].count())
        print("Begin migrating DB ...")
        documents = list(self.MongoFrom.db["FutureUseType"].find())
        result2 = self.MongoTo.save_to_mongodb_many("FutureUseType", documents)
        print("FutureUse Finished!", self.MongoTo.db["FutureUseType"].count())


def update_worker(id_to_visit, kg_api):

    data_delta = []
    NoID_delta = []
    for i in id_to_visit:
        data = kg_api.retrieve_entity(i, True)
        try:
            data["_id"] = data.pop("__id", None)[0]["name"]
            data_delta.append(data)
        except:
            NoID_delta.append(i)

    return (data_delta, NoID_delta)


class UpdateDB(OfflineTools):

    def __init__(self, local_configure):
        super().__init__()
        self.internal_use = local_configure["internal_use"]
        self.kg_api = internal_kg_api.InternalKGAPI(self.internal_use)
        self.save_root = local_configure["save_root"]
        self.process_number_max = local_configure["process_number_max"]
        self.batch_size = local_configure["batch_size"]
        self.debug = local_configure["debug"]
        if self.debug:
            self.process_number_max = 5
            self.MongoDB_obj = MongoDB(db_server_ip="10.12.192.47")
        else:
            self.MongoDB_obj = MongoDB(db_server_ip="10.12.192.22")

    def execute(self):

        time_start = datetime.datetime.now()

        to_visit_id_save_file = self.save_root + "to_visit_id_save_file.npy"
        data_save_file = self.save_root + "data_save_file.npy"
        NoID_save_file = self.save_root + "NoID_save_file.npy"

        NoID = []
        data_save = []
        try:
            entity_id_to_visit = list(np.load(to_visit_id_save_file, allow_pickle=True))
        except:
            print("ERROR! Missing to_visit_id_save_file!")
            exit(1)
        if os.path.isfile(data_save_file):
            data_save = list(np.load(data_save_file, allow_pickle=True))
        if os.path.isfile(NoID_save_file):
            NoID = list(np.load(NoID_save_file, allow_pickle=True))

        time_old = datetime.datetime.now()
        to_visit_num = len(entity_id_to_visit)
        while to_visit_num > 0:
            process_number = int(to_visit_num / self.batch_size)

            if process_number == 0:
                (data_delta, NoID_delta) = update_worker(entity_id_to_visit, self.kg_api)
                entity_id_to_visit = []
                to_visit_num = len(entity_id_to_visit)
                data_save.extend(data_delta)
                NoID.extend(NoID_delta)

                print("*************************************")
                print(to_visit_num)
                print(len(data_save))
                if os.path.isfile(to_visit_id_save_file):
                    os.rename(to_visit_id_save_file, to_visit_id_save_file[:-4]+"_OLD"+to_visit_id_save_file[-4:])
                if os.path.isfile(data_save_file):
                    os.rename(data_save_file, data_save_file[:-4]+"_OLD"+data_save_file[-4:])
                if os.path.isfile(NoID_save_file):
                    os.rename(NoID_save_file, NoID_save_file[:-4]+"_OLD"+NoID_save_file[-4:])
                np.save(to_visit_id_save_file, entity_id_to_visit)
                np.save(data_save_file, data_save)
                np.save(NoID_save_file, NoID)
                time_new = datetime.datetime.now()
                print(time_new - time_start, time_new - time_old)
                continue

            if process_number > self.process_number_max:
                process_number = self.process_number_max

            while len(entity_id_to_visit) >= (process_number * self.batch_size):
                parameters = []
                data_delta = []
                NoID_delta = []

                # Set parameters for multiprocessing
                for i in range(process_number):
                    temp = [entity_id_to_visit[(i*self.batch_size):((i+1)*self.batch_size)], self.kg_api]
                    parameters.append(temp)

                # Multiprocessing
                with Pool(process_number) as p:
                    result_workers = p.starmap(update_worker, parameters)

                # delete visited entity in the multiprocessing
                entity_id_to_visit = entity_id_to_visit[((i+1)*self.batch_size):]
                to_visit_num = len(entity_id_to_visit)

                # Merge multiprocessing results
                for i in result_workers:
                    data_delta.extend(i[0])
                    NoID_delta.extend(i[1])

                # print(len(data_relevant))
                # print(len(data_future))
                if self.debug:
                    np.save("/home/markzhao/Desktop/results.npy", result_workers)
                
                data_save.extend(data_delta)
                NoID.extend(NoID_delta)

                print("*************************************")
                print(to_visit_num)
                print(len(data_save))
                if os.path.isfile(to_visit_id_save_file):
                    os.rename(to_visit_id_save_file, to_visit_id_save_file[:-4]+"_OLD"+to_visit_id_save_file[-4:])
                if os.path.isfile(data_save_file):
                    os.rename(data_save_file, data_save_file[:-4]+"_OLD"+data_save_file[-4:])
                if os.path.isfile(NoID_save_file):
                    os.rename(NoID_save_file, NoID_save_file[:-4]+"_OLD"+NoID_save_file[-4:])
                np.save(to_visit_id_save_file, entity_id_to_visit)
                np.save(data_save_file, data_save)
                np.save(NoID_save_file, NoID)
                time_new = datetime.datetime.now()
                print(time_new - time_start, time_new - time_old)
                time_old = time_new

        print("*************************************")
        print(to_visit_num)
        print(len(data_save))
        if os.path.isfile(to_visit_id_save_file):
            os.rename(to_visit_id_save_file, to_visit_id_save_file[:-4]+"_OLD"+to_visit_id_save_file[-4:])
        if os.path.isfile(data_save_file):
            os.rename(data_save_file, data_save_file[:-4]+"_OLD"+data_save_file[-4:])
        if os.path.isfile(NoID_save_file):
            os.rename(NoID_save_file, NoID_save_file[:-4]+"_OLD"+NoID_save_file[-4:])
        np.save(to_visit_id_save_file, entity_id_to_visit)
        np.save(data_save_file, data_save)
        np.save(NoID_save_file, NoID)
        time_new = datetime.datetime.now()
        print(time_new - time_start, time_new - time_old)
