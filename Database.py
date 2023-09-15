import sqlite3
import os
import glob
import xml.etree.ElementTree as ET

class DataBaseReader():
    def __init__(self, corsor):
        self.__cursor = corsor

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
            sqlfile = os.path.join("C:\\Users", USERNAME, "Documents", "My Games", "Sid Meier's Civilization VI", "Cache", "DebugGameplay.sqlite")
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
    def __init__(self, path):
        if os.path.exists("db") == False:
            os.mkdir("db", )
        self.__prefix = "db/"+os.path.basename(os.path.normpath(path))
        # if os.path.exists(self.__prefix+".sqlite"):
        #     os.remove(self.__prefix+".sqlite")
        if not os.path.exists(self.__prefix+".sqlite"):
            self.__con = sqlite3.connect(self.__prefix+".sqlite")
        else:
            self.__con = sqlite3.connect(self.__prefix+".sqlite")
            self.__cursor = self.__con.cursor()
            DataBaseReader.__init__(self, self.__cursor)
            print(f"find existing mod database {self.__prefix}.sqlite, skip creating database")
            print(f"if you want to recreate the database, please delete {self.__prefix}.sqlite")
            return
        self.__sql_file_list =  glob.glob(os.path.join(path, '**/*.sql')) + glob.glob(os.path.join(path, '*.sql'))
        self.__xml_file_list =  glob.glob(os.path.join(path, '**/*.xml')) + glob.glob(os.path.join(path, '*.xml'))

        self.execute_file("01_GameplaySchema.sql")
        self.execute_file("Expansion2_Schema.sql")

        
        for file in self.__xml_file_list:
            self.execute_xml_file(file)

        for file in self.__sql_file_list:
            self.execute_file(file)

        print(f"database created, {len(self.__sql_file_list)} sql files and {len(self.__xml_file_list)} xml files executed")
        print(f"sqlite file saved to {self.__prefix}.sqlite")

        self.__con.commit()
        self.__cursor = self.__con.cursor()
        DataBaseReader.__init__(self, self.__cursor)
        
    def is_table_in_db(self, table):
        line = "SELECT name FROM sqlite_master WHERE type='table' AND name='"+table+"'"
        cursor = self.__con.cursor()
        cursor.execute(line)
        return cursor.fetchone() != None
    def execute(self, sql):
        self.__con.execute(sql)

    def execute_file(self,file):
        # print("executing "+file)
        with open(file, 'r') as f:
            sql = f.read()
            self.__con.executescript(sql)

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
                    if v == "true" or v == "True":
                        v = 1
                    elif v == "false" or v == "False":
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
    
    mdb = ModDatabaseReader("D:\\SteamLibrary\\steamapps\\workshop\\content\\289070\\2048816113\\")
    print(mdb.get_all_in_table("Types"))
