import sqlite3
import os
import glob
import xml.etree.ElementTree as ET
import random
import sqlparse
import re
import threading

class DataBaseReader():
    def __init__(self, corsor):
        self.__cursor = corsor

    def execute_and_fetchall(self, line):
        self.__cursor.execute(line)
        _discription = self.__cursor.description
        description = []
        for i in _discription:
            description.append(i[0])
        return description, self.__cursor.fetchall()
    
    def get_kv(self, table, key, value): # no duplications
        line = "SELECT * FROM "+table+" WHERE "+key+" = '"+value+"'"
        self.__cursor.execute(line)
        output = {}
        discription = self.__cursor.description
        fetched = self.__cursor.fetchone()
        for i, line in enumerate(discription):
            output[line[0]] = fetched[i]
        return output
    
    def get_column(self, table, kv, column):
        line = "SELECT "+column+" FROM "+table+" WHERE "
        for k, v in kv.items():
            line += k+" = '"+v+"' AND "
        line = line[:-5]
        self.__cursor.execute(line)
        lines = self.__cursor.fetchall()
        output = []
        for line in lines:
            output.append(line[0])
        return output

    def get_data(self, table, kv, column):

        line = "SELECT "+column+" FROM "+table+" WHERE "
        for k, v in kv.items():
            line += k+" = '"+v+"' AND "
        line = line[:-5]
        self.__cursor.execute(line)
        output = self.__cursor.fetchone()
        if output == None:
            return None
        return output[0]
    
    def is_in(self, table, key, value):
        line = "SELECT * FROM "+table+" WHERE "+key+" = '"+value+"'"
        self.__cursor.execute(line)
        return self.__cursor.fetchone() != None
    
    def get_all_in_table(self, table):
        output_list = []
        line = "SELECT * FROM "+table
        self.__cursor.execute(line)
        discription = self.__cursor.description
        # print(discription)
        fetched = self.__cursor.fetchall()
        # print(fetched)
        for line in fetched:
            output = {}
            for i, line_des in enumerate(discription):
                output[line_des[0]] = line[i]
            output_list.append(output)

        return output_list

class Civ6DatabaseReader(DataBaseReader):
    def __init__(self, file = None): 
        USERNAME = os.getlogin( ) 
        if file != None and file.endswith("DebugGameplay.sqlite"):
            sqlfile = file
        else:
            sqlfile = os.path.join("C:\\Users",USERNAME, "AppData\\Local\\Firaxis Games\\Sid Meier's Civilization VI\\Cache\\DebugGameplay.sqlite")
            print(sqlfile)
        if os.path.exists(sqlfile):
            self.__database = sqlite3.connect(sqlfile)
            self.__cursor = self.__database.cursor()
        else:
            while os.path.exists(sqlfile) == False:
                print("civ 6 gameplay database cache not found, plz insert civ 6 database cache path (end with ../DebugGameplay.sqlite):")
                sqlfile = input()
            self.__database = sqlite3.connect(sqlfile)
            self.__cursor = self.__database.cursor()
        DataBaseReader.__init__(self, self.__cursor)
        print (f"database loaded")
        
    
    
class ModDatabaseReader(DataBaseReader):
    
    def __init__(self, path, civ6sqlfile_path = None):
        if os.path.exists("db") == False:
            os.mkdir("db", )
        self.__prefix = "db/"+os.path.basename(os.path.normpath(path))
        # if os.path.exists(self.__prefix+".sqlite"):
        #     os.remove(self.__prefix+".sqlite")

        self.GetDataFileList(path)


        if not os.path.exists(self.__prefix+".sqlite"):
            self.__con = sqlite3.connect(self.__prefix+".sqlite")
            self.__cursor = self.__con.cursor()
        else:
            self.__con = sqlite3.connect(self.__prefix+".sqlite")
            self.__cursor = self.__con.cursor()
            DataBaseReader.__init__(self, self.__cursor)
            print(f"find existing mod database {self.__prefix}.sqlite, skip creating database")
            print(f"if you want to recreate the database, please delete {self.__prefix}.sqlite")
            return

        print("buildng mod datable, plz wait")
        self.execute_file("01_GameplaySchema.sql")
        self.execute_file("Expansion2_Schema.sql")
        
        for file in self.__database_file_list:
            if file.endswith(".xml"):
                self.execute_xml_file(file)
            else:
                if os.path.basename(file).find(os.path.basename(self.__prefix))>= 0:
                    print("ignore "+file)
                    continue
                self.execute_file(file)

        print(f"database created, {len(self.__database_file_list)} data files executed")
        print(f"sqlite file saved to {self.__prefix}.sqlite")

        self.__con.commit()
        DataBaseReader.__init__(self, self.__cursor)
        
    def GetModLoadOrder(self):
        return self.__load_order_list
    def GetDataFileList(self, path):
        modinfofile = glob.glob(os.path.join(path, "*.modinfo"))[0]
        tree = ET.parse(modinfofile)
        root = tree.getroot()
        in_game_actions = root.find("InGameActions")
        update_db_list = in_game_actions.findall("UpdateDatabase")
        
        self.__database_file_list = []
        self.__load_order_list = []

        for update_db in update_db_list:
            load_order = 0
            if update_db.get("id").find(os.path.basename(self.__prefix)) >= 0:
                continue
            if update_db.findall("Properties"):
                propeties = update_db.findall("Properties")[0]
                if propeties.findall("LoadOrder"):
                    load_order = int(propeties.findall("LoadOrder")[0].text)
                elif propeties.get("LoadOrder"):
                    load_order = int(propeties.get("LoadOrder"))
            files = update_db.findall("File")
            for file in files:
                filepath = os.path.join(path, file.text)
                self.__database_file_list.append(filepath) 
                self.__load_order_list.append(load_order)

        self.__database_file_list  = sorted(self.__database_file_list, key=lambda x: self.__load_order_list[self.__database_file_list.index(x)])
        # print(self.__database_file_list)
                


    def is_table_in_db(self, table):
        line = "SELECT name FROM sqlite_master WHERE type='table' AND name='"+table+"'"
        cursor = self.__con.cursor()
        cursor.execute(line)
        return cursor.fetchone() != None
    
    def check_is_insert_into_types(self, statement):
        for token in statement.tokens:
            types_started = False
            if token.is_group and token.tokens[0].ttype == None and token.tokens[0].value == "Types":
                # token.value = token.value.replace(")",", Hash)")
                types_started = True
                break
        return types_started

    def execute_file(self, file):
        print("executing "+file)
        f = open(file)
        sql = f.read()
        f.close()

        parsed = sqlparse.parse(sqlparse.format(sql, strip_comments=True, strip_whitespace = True).strip())
        
        fixed_statements, selection = self.fix_hash_get_select(parsed)
        if len(selection) > 0:
            self.read_selection(selection)
        for i, statement in enumerate(parsed):
            if i in fixed_statements:
                self.__con.execute(fixed_statements[i])
            else:
                self.__con.execute(statement.value)
        if len(selection) > 0:
            self.delete_selection(selection)

    def delete_selection(self,selection):
        for table, condition in selection:
            sql = "DELETE FROM "+table+" WHERE " +condition
            # print(sql)
            self.__cursor.execute(sql)



    def read_selection(self, selection):
        if hasattr(self, "__civ6db") == False:
            self.__civ6db = Civ6DatabaseReader()
        for table, condition in selection:
            sql = "SELECT * FROM "+table+" WHERE "+condition
            describ, results = self.__civ6db.execute_and_fetchall(sql)
            # print(len(results[0]), len(describ))
            for result in results:
                sql = "INSERT INTO "+table+" ("
                for i, des in enumerate(describ):
                    sql += des+", "
                sql = sql[:-2]
                sql += ") VALUES ("
            for i, value in enumerate(result):
                if value == None:
                    value = 0
                if isinstance(value, str):
                    sql += "'"+value+"', "
                else:
                    sql += str(value)+", "
            sql = sql[:-2]
            sql += ");"
            # print(sql)
            self.__cursor.execute(sql)



    def fix_hash_get_select(self, statements, write=False):
        fixed_type = {}
        selection = []
        for i, statement in enumerate(statements):
            output = ""
            types_started = False
            has_selection = False
            for token in statement.tokens:
                if token.is_group and token.tokens[0].ttype == None and token.tokens[0].value == "Types":
                    # token.value = token.value.replace(")",", Hash)")
                    types_started = True
                    output += token.normalized.replace(")",", Hash)")
                elif types_started  and token.is_group:
                    output += token.normalized.replace(f")",f", HashPlacehoder)")
                else:
                    output += token.normalized

                if token.is_group and token.tokens[0].ttype == None:
                    table_name = token.tokens[0].value

                if token.normalized.find("SELECT") >= 0:
                    has_selection = True
                
                if has_selection and token.is_group and token.tokens[0].value == "WHERE": 
                    # print(token, type(token.tokens[2]))
                    for sub_token in token.tokens:
                        # is class 'sqlparse.sql.Comparison'
                        if isinstance(sub_token, sqlparse.sql.Comparison):
                            selection.append((table_name, sub_token.value))
                            
            if types_started:
                while output.find("HashPlacehoder") >= 0:
                    h = str(hash(random.random()) % 0x100000000-0x80000000)
                    output = output.replace("HashPlacehoder", h, 1)
                fixed_type[i] = output
        return fixed_type, selection

        # types_started = False
        # output = ""
        # for i, line in enumerate(lines):
        #     if line.find('INSERT INTO Types') >= 0:
        #         lines[i] = line.replace(")", ", Hash)")
        #         types_started = True
        #         output += (lines[i]+ "\n")
        #         continue

        #     if types_started:
        #         h = str(hash(random.random()) % 0x100000000-0x80000000)
        #         lines[i] = line.replace(")", ", "+h+")")
        #         if line.find(";") >= 0:
        #             types_started = False
            
        #     output += (lines[i]+ "\n")
        # if write:
        #     print(output)
        # return output
        


    def execute_xml_file(self, file):
        # print("executing "+file)
        tree = ET.parse(file)
        root = tree.getroot()
        child_list = []
        for child in root:
            child_list.append(child.tag)

        if not self.is_table_in_db(child_list[0]):
            # print("not a valid GameData file")
            return
        cursor = self.__con.cursor()
        for child in root:
            row_list = child.findall("Row")
            # print(child.tag, len(row_list))
            if len(row_list) == 0:
                continue
            row = row_list[0]
            keys = []
            if len(row.keys()) > 0:
                keys = row.keys()
            else:
                for key in row.iter():
                    if key.tag != "Row":
                        keys.append(key.tag)
            if child.tag == "Types": # Hash is unique and not null
                keys.append("Hash")
            sql_line = "INSERT INTO "+child.tag+" ("+",".join(keys)+") VALUES\n"
            if child.tag == "Types": # Hash is unique and not null
                keys.remove("Hash")
            for row in row_list:
                sql_line += "("
                for key in keys:
                    if row.find(key) != None:
                        v = row.find(key).text
                        if key == "Type":
                            type_hash = hash(v) % 0x100000000-0x80000000
                    else:
                        v = row.get(key)
                        if key == "Type":
                            type_hash = hash(v) % 0x100000000-0x80000000
                    if v == "true" or v == "True" or v == "TRUE":
                        v = 1
                    elif v == "false" or v == "False" or v == "FALSE":
                        v = 0
                    sql_line += "'"+str(v)+"',"
                if child.tag == "Types": # Hash is unique and not null
                    sql_line += "'"+str(type_hash)+"',"

                sql_line = sql_line[:-1]
                sql_line += "),\n"
            sql_line = sql_line[:-2]
            sql_line += ";"
            print(sql_line)
            cursor.execute(sql_line)
        


    



if __name__ == '__main__':
    mdb = ModDatabaseReader("D:\\SteamLibrary\\steamapps\\workshop\\content\\289070\\3017462977\\")
    # print(mdb.get_all_in_table("Types"))

    # execute_file('D:\\SteamLibrary\\steamapps\\workshop\\content\\289070\\3017462977\\Data/Majo_no_Tabitabi_Buildings.sql')
