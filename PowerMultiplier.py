import sqlite3
import os
import sys
import xml
import xml.etree.ElementTree as ET
import glob
import math
import argparse
import Database

class database_read():
    # base class to read original database
    def __init__(self, database):
        self.__database_self = database

    def GenRowList(self, table_name):
        return self.__database_self.get_all_in_table(table_name)

    def GetRowKeys(self, row):
        return list(row.keys())

    def GetRowValue(self, row, name):
        return row[name]


class object_generator(database_read):
    #not ready yet.
    def __init__(self, object_kind_name, object_type_list, database_self, database_original, multiplier = 10):
        self.__object_kind_name = object_kind_name
        self.__object_type_list = object_type_list
        self.__database_self = database_self
        self.__database_original = database_original
        self.__multiplier = multiplier

        self.__output_lines = []
        
        database_read.__init__(self, database_self)

    def GetReplaceTypes(self, type_name):
        # get what this original object it replaces
        capital_t = type_name[0].upper() + type_name[1:]
        
        objects = {}
        for row in self.GenRowList(capital_t+"s"):
            objects[self.GetRowValue(row, capital_t+"Type")] = {}

        if type_name == "improvement":
            return objects
        for row in self.GenRowList(capital_t+"Replaces"):
            if self.GetRowValue(row,"CivUnique"+capital_t+"Type") in objects:
                objects[self.GetRowValue(row,"CivUnique"+capital_t+"Type")]["Replaces"+capital_t+"Type"] = self.GetRowValue(row,"Replaces"+capital_t+"Type")
        return objects
    
    def CalculateAttack(self, attack):
        symbol = attack/abs(attack)
        attack = abs(attack)
        value = 25* math.log( self.__multiplier * math.exp( attack / 25) - (self.__multiplier-1) )
        return int(symbol * round( value ))
    
        
    def GenerateMultipleUpdate(self, table_name, set_dict, where_dict):
        output = ( f"UPDATE {table_name}\nSET ")
        for key in set_dict:
            output += f"{key} = "
            if type(set_dict[key]) == str:
                output += f"'{set_dict[key]}', "
            else:
                output += f"{set_dict[key]}, "
        output = output[:-2]+"\nWHERE "
        for key in where_dict:
            output += f"{key} = "
            if type(where_dict[key]) == str:
                output += f"'{where_dict[key]}' AND "
            else:
                output += f"{where_dict[key]} AND "
        output = output[:-5]+";\n\n"
        self.__output_lines.append(output)
    

    # def gen_for_object_type(self, type_name, properties_list, gain_dict):
        
    #     capital_t = type_name[0].upper() + type_name[1:]

    #     ll = self.__output_lines
    #     if len(self.GenRowList(capital_t+"s")) >0:
    #         ll.append(f"\n\n-- {capital_t} infos\n")
    #     objects = self.GetReplaceTypes(type_name)
    #     strenth_keys = ["Combat", "BaseCombat", "RangedCombat", "AntiAirCombat", "ReligiousStrength", 
    #                     "Bombard", "OuterDefenseStrength", "DefenseModifier", "CityStrengthModifier"]

    #     for row in self.GenRowList(capital_t+"s"): # iterate over objects
    #         object_type = self.GetRowValue(row,capital_t+"Type")
    #         if "Replaces"+capital_t+"Type" in objects[object_type]:
    #             replace_object_type = objects[object_type]["Replaces"+capital_t+"Type"]
    #         else:
    #             replace_object_type = ""
    #         objects[object_type]["info"] = {}
    #         ori_info = {}
    #         for key in self.GetRowKeys(row):
    #             if len(replace_object_type) > 0:
    #                 ori_info[key] = self.__database_original.get_data(capital_t+"s", {capital_t+"Type": replace_object_type}, key)
    #                 if ori_info[key] == None:
    #                     ori_info[key] = 0
    #             else:
    #                 ori_info[key] = 0
            
    #         updated_info = {}
    #         for key in self.GetRowKeys(row):
    #             value = self.GetRowValue(row,key)
    #             if key == "Cost" or key == "Maintenance" or key == "CostProgressionParam1":
    #                 if len(replace_object_type) > 0:
    #                     if float(value) >= float(ori_info[key]) or int(value) == 0:
    #                         continue
    #                     else:
    #                         value = float(ori_info[key])/(float(ori_info[key])/float(value))**self.__multiplier
    #                         value = int(round(value))
    #                 else:
    #                     value = int(round((float(value)/self.__multiplier)))

    #             if key in properties_list:
    #                 if key in strenth_keys:
    #                     if int(value) <= int(ori_info[key]):
    #                         continue
    #                     else:
    #                         value = int(ori_info[key]) + self.CalculateAttack(int(value) - int(ori_info[key]))
    #                         value = min(value, value+self.CalculateAttack(10))
    #                 else:
    #                     if value == None or int(value) <= int(ori_info[key]):
    #                         continue
    #                     else:
    #                         value = int(ori_info[key]) + (int(value) - int(ori_info[key])) * self.__multiplier


    #             if value != self.GetRowValue(row,key) and int(value) != int(self.GetRowValue(row,key)):
    #                 updated_info[key] = value
    #             objects[object_type]["info"][key] = value
    #         self.GenerateMultipleUpdate(capital_t+"s", updated_info, {capital_t+"Type": object_type})

    #         for k in gain_dict:
    #             if k == "_GreatWorks" and self.__change_great_work_slots == False:
    #                 continue
    #             self.GenGainForTable(capital_t+k, capital_t+"Type", object_type, replace_object_type, gain_dict[k])

class modifier_generator(database_read):
    # usable ,give a modifier list and it will generate sql lines for ya.
    # not working now for those modifiers need to be duplicated
    def __init__(self, modifier_id_list, database, multiplier = 10):
        self.__modifier_id_list = modifier_id_list
        self.__database = database
        self.__multiplier = multiplier
        self.__sql_file_line_list = []
        self.__sql_gov_slot_line_list = []
        self.__sql_grant_unit_line_list = []
        self.__modifier_list = []
        database_read.__init__(self, database)
        for row in self.GenRowList("Modifiers"):
            if self.GetRowValue(row,"ModifierId") in self.__modifier_id_list:
                self.__modifier_list.append(row)

    def GenerateAll(self):
        
        additional_modifierid_list = []
        for row in self.GenRowList("ModifierArguments"):
            # print(self.GetRowValue(row,"ModifierId"))
            for row2 in self.__modifier_list:
                if self.GetRowValue(row,"ModifierId") == self.GetRowValue(row2,"ModifierId"):
                    if self.GetRowValue(row,"Name") == "ModifierId":
                        additional_modifierid_list.append(self.GetRowValue(row,"Value"))

        if additional_modifierid_list.__len__() > 0:
            mg_additional = modifier_generator(additional_modifierid_list, self.__database, self.__multiplier)
            additional_normal_line, additional_gov_slot_line, additional_grant_unit_line = mg_additional.GenerateAll()
            self.__sql_file_line_list += additional_normal_line
            self.__sql_gov_slot_line_list += additional_gov_slot_line
            self.__sql_grant_unit_line_list += additional_grant_unit_line


        self.GenAllCombatModifier()
        self.GenGrantUnitModifier()
        self.GenAmountChangeForAllOtherModifiers()
        self.GenForGovernmentSlotModifier()

        return self.__sql_file_line_list, self.__sql_gov_slot_line_list, self.__sql_grant_unit_line_list

    def CalculateAttack(self, attack):
        symbol = attack/abs(attack)
        attack = abs(attack)
        value = 25* math.log( self.__multiplier * math.exp( attack / 25) - (self.__multiplier-1) )
        return int(symbol * round( value ))

    def GenAmountChangeForAllOtherModifiers(self):
        self.__normal_modifier_list = []
        modifier_list_with_arguments = []
        modifier_list_with_multiple_values = {}
        ll = self.__sql_file_line_list
        numeric_value_names = ["Amount", "YieldChange", "YieldBasedOnAppeal", "UnitProductionPercent",
                               "UnitCostPercent", "TurnsActive", "Turns", "TechBoost","SCRIPTURE_SPEAD_STRENGTH",
                               "Range", "Radius","Multiplier", "Modifier", "Discount"]
        modifier_list_scaling_factor = {}
        for row in self.__modifier_list:
            if self.GetRowValue(row,"ModifierType").find("STRENGTH") < 0 and self.GetRowValue(row,"ModifierType").find("GRANT_UNIT") < 0:
                self.__normal_modifier_list.append(self.GetRowValue(row,"ModifierId"))


        for row in self.GenRowList("ModifierArguments"):
            # print(self.GetRowValue(row,"ModifierId"))
            if self.GetRowValue(row,"ModifierId") in self.__normal_modifier_list:
                if self.GetRowValue(row,"Name") in numeric_value_names:
                    if self.GetRowValue(row,"Value").find(",") < 0:
                        modifier_list_with_arguments.append(self.GetRowValue(row,"ModifierId"))
                    else:
                        modifier_list_with_multiple_values[self.GetRowValue(row,"ModifierId")] = self.GetRowValue(row,"Value")
                
                if self.GetRowValue(row,"Name") in ('ScalingFactor', 'Percent', 'BuildingProductionPercent'):
                    modifier_list_scaling_factor[(self.GetRowValue(row,"ModifierId"))] = self.GetRowValue(row,"Value")

        numeric_names = "("
        for name in numeric_value_names:
            numeric_names += f"'{name}', "
        numeric_names = numeric_names[:-2]+")"
        if modifier_list_with_arguments.__len__() > 0:
            ll.append(f"\n\n-- ModifierArguments Change for amount values \n\n")
            ll.append(f"UPDATE ModifierArguments\nSET Value = Value * {self.__multiplier}\nWHERE Name IN {numeric_names}\nAND ModifierId IN\n (")
            for mid in modifier_list_with_arguments:
                ll.append(f"'{mid}',\n")
            ll[-1] = ll[-1][:-2]+");\n\n"

        for mid in modifier_list_with_multiple_values:
            ll.append(f"UPDATE ModifierArguments\nSET Value = ")
            value = modifier_list_with_multiple_values[mid]
            value_list = value.split(",")
            output_value = ""
            for i in range(len(value_list)):
                output_value+= f"{float(value_list[i]) * self.__multiplier}, "
            output_value = output_value[:-2]
            ll.append(f"'{output_value}'\nWHERE Name in {numeric_names}\nand ModifierId = '{mid}';\n\n")

        for mid in modifier_list_scaling_factor:
            value = int(modifier_list_scaling_factor[mid])
            if int(value) > 100:
                value = (int(value) - 100)*self.__multiplier+100
            else:
                value = int(round(value/100)**self.__multiplier*100)
            ll.append(f"UPDATE ModifierArguments\nSET Value = {value}\nWHERE Name in ('ScalingFactor', 'Percent', 'BuildingProductionPercent')\nand ModifierId = '{mid}';\n\n")


    
    def GenAllCombatModifier(self): 
        output_lines = self.__sql_file_line_list
        combat_modifier_list = []
        for row in self.__modifier_list:
            if self.GetRowValue(row,"ModifierType").find("STRENGTH") >= 0:
                combat_modifier_list.append(self.GetRowValue(row,"ModifierId"))
        if combat_modifier_list.__len__() == 0:
            return
        output_lines.append(f"-- Combat Strength Modifiers\n")
        output_lines.append("-- formula is: 25*ln({modifier})*exp({original_strength}/25)-{modifier-1})\n\n\n")
        for row in self.GenRowList("ModifierArguments"):
            if self.GetRowValue(row,"Name") == "Amount" and self.GetRowValue(row,"ModifierId") in combat_modifier_list:
                strength = self.GetRowValue(row,"Value")
                output_lines.append(f"UPDATE ModifierArguments\n")
                output_lines.append(f"SET Value = {self.CalculateAttack(int(strength))}\n")
                output_lines.append(f"WHERE ModifierId = '{self.GetRowValue(row,'ModifierId')}'\n")
                output_lines.append(f"AND Name = 'Amount';\n\n")
        
    
    def GetGovSlotInjector(self, mid):#injector is not TraitType
        injector = {}
        row_lists = {}
        row_lists["Modifiers"] = self.GenRowList("Modifiers")
        row_lists["ModifierArguments"] = self.GenRowList("ModifierArguments")
        row_lists["ModifierStrings"] = self.GenRowList("ModifierStrings")
        row_lists["TraitModifiers"] = self.GenRowList("TraitModifiers")

        for rl in row_lists:
            for row in row_lists[rl]:
                if self.GetRowValue(row, "ModifierId") == mid:
                    if not rl in injector:
                        injector[rl] = {}
                    for key in self.GetRowKeys(row):
                        if not key in injector[rl]:
                            injector[rl][key] = []
                        injector[rl][key].append(self.GetRowValue(row, key))

        return injector

    def GenerateIndertLine(self, value_list, last = False):
        output = "("
        for value in value_list:
            if type(value) == str:
                output += f"'{value}', "
            elif value == None:
                output += "NULL, "
            else:
                output += f"{value}, "
        output = output[:-2]+")"
        if not last:
            output += ",\n"
        else:
            output += ";\n\n"
        return output
    
    def GenerateInsertHead(self, table_name, key_list):
        output = f"INSERT INTO {table_name} ("
        for key in key_list:
            output += f"{key}, "
        output = output[:-2]+")\nVALUES\n"
        return output
    
    def gen_for_gov_table(self, injector, tab, mid):        
        ll = self.__sql_gov_slot_line_list
        tab_keys = injector[tab].keys()
        ll.append(self.GenerateInsertHead(tab, tab_keys))
        for inj_idx in range(len(injector[tab]["ModifierId"])):
            for i_multi in range(self.__multiplier-1):
                value_list = []
                for key in tab_keys:
                    if key == "ModifierId":
                        value_list.append(f"{mid}_{i_multi+1}")
                    else:
                        value_list.append(injector[tab][key][inj_idx])
                ll.append(self.GenerateIndertLine(value_list, i_multi == self.__multiplier-2 and inj_idx == len(injector[tab]["ModifierId"])-1))


    def AddGovSlotInjector(self, gov_slot_m_dict, mid):
        injector = self.GetGovSlotInjector(mid)
        tabs = ["Modifiers", "ModifierArguments", "TraitModifiers"]
        for tab in tabs:
            self.gen_for_gov_table(injector, tab, mid)


    def AddGovSlotModifierInfo(self, gov_slot_m_dict, mid):     
        d = gov_slot_m_dict[mid]["info"]
        ll = self.__sql_gov_slot_line_list        
        ll.append(self.GenerateInsertHead("Modifiers", d.keys()))
        for i in range(self.__multiplier-1):
            value_list = []
            for key in d.keys():
                if key == "ModifierId":
                    value_list.append(f"{mid}_{i+1}")
                else:
                    value_list.append(d[key])
            ll.append(self.GenerateIndertLine(value_list, i == self.__multiplier-2))
        

    def GenForGovernmentSlotModifier(self):
        gov_slot_m_dict = {}
        for row in self.__modifier_list:
            if row["ModifierType"].find("GOVERNMENT_SLOT") >= 0:
                mid = row["ModifierId"]
                gov_slot_m_dict[mid]={"info":{}}
                for key in self.GetRowKeys(row):
                    gov_slot_m_dict[mid]["info"][key] = row[key]

        for row in self.GenRowList("ModifierArguments"):
            mid = row["ModifierId"]
            if mid in gov_slot_m_dict:
                gov_slot_m_dict[mid][row["Name"]] = row["Value"]
                
        # begin to generate sql
        for mid in gov_slot_m_dict:
            d = gov_slot_m_dict[mid]
            if d["info"]['ModifierType'] == "MODIFIER_PLAYER_CULTURE_REPLACE_GOVERNMENT_SLOTS":
                ll = self.__sql_gov_slot_line_list

                # self.AddGovSlotModifierInfo(gov_slot_m_dict, mid)

                ll.append(f"INSERT INTO ModifierArguments (ModifierId, Name, Value)\nVALUES\n")
                for i in range(self.__multiplier-2):
                    if "AddedGovernmentSlotType" in d:
                        ll.append(f"('{mid}_{i+1}', 'AddedGovernmentSlotType', '{d['AddedGovernmentSlotType']}'),\n")
                    if "ReplacesAll" in d:
                        ll.append(f"('{mid}_{i+1}', 'ReplacesAll', '{d['ReplacesAll']}'),\n")
                    ll.append(f"('{mid}_{i+1}', 'ReplacedGovernmentSlotType', '{d['ReplacedGovernmentSlotType']}'),\n")
                
                if "AddedGovernmentSlotType" in d:
                    ll.append(f"('{mid}_{self.__multiplier-1}', 'AddedGovernmentSlotType', '{d['AddedGovernmentSlotType']}'),\n")
                if "ReplacesAll" in d:
                    ll.append(f"('{mid}_{self.__multiplier-1}', 'ReplacesAll', '{d['ReplacesAll']}'),\n")
                ll.append(f"('{mid}_{self.__multiplier-1}', 'ReplacedGovernmentSlotType', '{d['ReplacedGovernmentSlotType']}');\n\n")
            
            else:
                self.AddGovSlotInjector(gov_slot_m_dict, mid)

    def GenGrantUnitModifier(self):
        grant_unit_modifier_list = []
        for row in self.__modifier_list:
            if self.GetRowValue(row,"ModifierType").find("GRANT_UNIT") >= 0:
                grant_unit_modifier_list.append(self.GetRowValue(row,"ModifierId"))
        
        for mid in grant_unit_modifier_list:
            self.__sql_grant_unit_line_list.append(f"UPDATE ModifierArguments\n")
            self.__sql_grant_unit_line_list.append(f"SET Value = Value * {self.__multiplier}\n")
            self.__sql_grant_unit_line_list.append(f"WHERE ModifierId = '{mid}'\n")
            self.__sql_grant_unit_line_list.append(f"AND Name = 'Amount';\n\n")

class mod_power_multiplier(database_read):
    __kind_type_dict = {}
    __table_column_dict = {}
    # __xml_tree_list = []
    __sql_file_line_list = []
    __sql_slot_line_list = []
    __sql_grant_unit_line_list = []

    __grant_unit_modifier_list = []
    __combat_modifier_list = []
    __government_slot_modifier_dict = {}
    
    
    def __init__(self, path, multiplier = 10, change_great_work_slots = False,
                 grant_unit = False, single_file = True, civ_6_database_path = None):
        if os.path.exists("output") == False:
            os.mkdir("output", )
        self.__multiplier = multiplier
        self.__output_prefix = os.path.join("output",os.path.basename(os.path.normpath(path))+"_x"+str(multiplier))

        self.__grant_unit = grant_unit
        self.__path = path
        self.__change_great_work_slots = change_great_work_slots # it may crush the game
        self.__single_file = single_file

        self.__mod_database_reader = Database.ModDatabaseReader(path)
        self.__civ6_database_reader = Database.Civ6DatabaseReader(civ_6_database_path)

        database_read.__init__(self, self.__mod_database_reader)

        print("inited")

    def GenerateAll(self):
        # self.GenForGovernmentSlotModifier()
        # self.GenAllCombatModifier()
        # self.GenGrantUnitModifier()
        # self.GenAmountChangeForAllOtherModifiers() # may cause error, need to check
        modifier_id_list = []
        for row in self.GenRowList("Modifiers"):
            modifier_id_list.append(self.GetRowValue(row,"ModifierId"))
        mg = modifier_generator(modifier_id_list, self.__mod_database_reader, self.__multiplier)
        normal_line, gov_slot_line, grant_unit_line = mg.GenerateAll()
        self.__sql_file_line_list += normal_line
        self.__sql_slot_line_list += gov_slot_line
        self.__sql_grant_unit_line_list += grant_unit_line

        self.GenForBuildings()
        self.GenForDistricts()
        self.GenForUnits()
        self.GenForImprovements()
        self.GenForProjects()
        self.WriteAll()

    


        

    def GetAllTypes(self, kind_name):
        output = {}
        for row in self.GenRowList(kind_name):
            output[self.GetRowValue(row, kind_name[:-1]+"Type")] = {}
        return output

    def RemoveAllAgendaTrait(self):
        for row in self.GenRowList("TraitModifiers")    :
            if self.GetRowValue(row,"TraitType") in self.__table_column_dict["AgendaTraits"]:
                self.__table_column_dict["TraitModifiers"].remove(self.GetRowValue(row,"ModifierId"))
    
    def CalculateAttack(self, attack):
        symbol = attack/abs(attack)
        attack = abs(attack)
        value = 25* math.log( self.__multiplier * math.exp( attack / 25) - (self.__multiplier-1) )
        return int(symbol * round( value ))
    

    
    def GenerateMultipleUpdate(self, table_name, set_dict, where_dict):
        output = ( f"UPDATE {table_name}\nSET ")
        for key in set_dict:
            output += f"{key} = "
            if type(set_dict[key]) == str:
                output += f"'{set_dict[key]}', "
            else:
                output += f"{set_dict[key]}, "
        output = output[:-2]+"\nWHERE "
        for key in where_dict:
            output += f"{key} = "
            if type(where_dict[key]) == str:
                output += f"'{where_dict[key]}' AND "
            else:
                output += f"{where_dict[key]} AND "
        output = output[:-5]+";\n\n"
        self.__sql_file_line_list.append(output)
    


    def WriteAll(self):

        basename = os.path.basename(os.path.normpath(self.__output_prefix))
        loadorders = self.__mod_database_reader.GetModLoadOrder()
        max_loadorder = max(loadorders)
        
        print("generation done, plz add these lines into traits power mod's .modinfo file:\n")

        # print(4*" "+f"<UpdateDatabase id=\"{basename}\">")
        # print(6*" "+f"<Properties>")
        # print(8*" "+f"<LoadOrder>{max_loadorder+1}</LoadOrder>")
        # print(6*" "+f"</Properties>")
        
        if self.__single_file:
            self.__sql_file_line_list += self.__sql_slot_line_list
            self.__sql_file_line_list += self.__sql_grant_unit_line_list
            with open(self.__output_prefix+".sql", "w") as f:
                f.writelines(self.__sql_file_line_list)
            print("<File>"+self.__output_prefix+".sql"+"</File>")

        else:    
            if len(self.__sql_slot_line_list) > 0:
                with open(self.__output_prefix+"_gslot.sql", "w") as f:
                    f.writelines(self.__sql_slot_line_list)
                print(6*" "+"<File>"+basename+"_gslot.sql"+"</File>")

            with open(self.__output_prefix+".sql", "w") as f:
                f.writelines(self.__sql_file_line_list)
            print(6*" "+"<File>"+basename+".sql"+"</File>")

            if self.__grant_unit and len(self.__sql_grant_unit_line_list) > 0:
                with open(self.__output_prefix+"_grant_unit.sql", "w") as f:
                    f.writelines(self.__sql_grant_unit_line_list)
                print(6*" "+"<File>"+basename+"_grant_unit.sql"+"</File>")
        # print(4*" "+f"</UpdateDatabase>")

    def GenForAdjacent(self, adj, oriadj):
        ll = self.__sql_file_line_list
        kv_adj = self.__civ6_database_reader.get_kv("Adjacency_YieldChanges", "ID", adj)
        kv_oriadj = self.__civ6_database_reader.get_kv("Adjacency_YieldChanges", "ID", oriadj)
        checklist = ["YieldType", "OtherDistrictAdjacent", "AdjacentTerrain", "AdjacentFeature",
                     "AdjacentRiver", "AdjacentWonder","AdjacentResource","AdjacentNaturalWonder",
                     "AdjacentImprovement","AdjacentDistrict","PrereqCivic","PrereqTech"]
        
        output = True
        for key in checklist:
            output = output and( kv_adj[key]!= None and kv_adj[key] == kv_oriadj[key])
        
        if output:
            c1 = int(kv_oriadj["YieldChange"])
            c2 = int(kv_adj["YieldChange"])
            t1 = int(kv_oriadj["TilesRequired"])
            t2 = int(kv_adj["TilesRequired"])
            if t1 == t2:
                if c2 > c1:
                    change = int(c1 + (c2-c1)*self.__multiplier)
                    ll.append(f"UPDATE Adjacency_YieldChanges\nSET YieldChange = {change}\nWHERE ID = '{adj}';\n\n")
            elif t2 < t1 and float(c2)/(t2) > float(c1)/(t1):
                change = (c2 * t1/t2 - c1)*self.__multiplier + c1
                ll.append(f"UPDATE Adjacency_YieldChanges\nSET TilesRequired = {t1}, YieldChange = {change}\nWHERE ID = '{adj}';\n\n")
            elif  float(c2)/(t2) > float(c1)/(t1):
                change = (c2 - c1*t2/t1)*self.__multiplier + c1*t2/t1
                ll.append(f"UPDATE Adjacency_YieldChanges\nSET YieldChange = {change}\nWHERE ID = '{adj}';\n\n")
                 
        return output # true if similar original adjency is found
        
    def GenForDistricts(self):
        district_other_properties = ["HitPoints","Appeal", "Housing", "Entertainment", 
                                      "AirSlots", "CitizenSlots", "CityStrengthModifier"]

        gain_dict = {"_GreatPersonPoints": "GreatPersonClassType", "_CitizenGreatPersonPoints": "GreatPersonClassType", "_CitizenYieldChanges": "YieldType","_TradeRouteYields": "YieldType"}
        self.GenForObjectType("district", district_other_properties, gain_dict)

        districts = self.GetReplaceTypes("district")
        for distr in districts.values():
            distr["adj"] = []
                
        ll = self.__sql_file_line_list
        for row in self.GenRowList("District_Adjacencies"):
            if self.GetRowValue(row,"DistrictType") in districts:
                districts[self.GetRowValue(row,"DistrictType")]["adj"].append(self.GetRowValue(row,"YieldChangeId"))

        for distr in districts.values():
            # distr = districts[dis]
            if "adj" not in distr:
                continue
            if "ReplacesDistrictType" not in distr or not self.__civ6_database_reader.is_in("District_Adjacencies", "DistrictType", distr["ReplacesDistrictType"]):
                for adj in distr["adj"]:
                    ll.append(f"UPDATE Adjacency_YieldChanges\nSET YieldChange = YieldChange * {self.__multiplier}\nWHERE ID = '{adj}';\n\n")
            else:
                distr["oriadj"] = self.__civ6_database_reader.get_column("District_Adjacencies", {"DistrictType": distr["ReplacesDistrictType"]}, "YieldChangeId")
                for adjid in distr["adj"]:
                    if adjid in distr["oriadj"]:
                        distr["adj"].remove(adjid)
                for adj in distr["adj"]:
                    for oriadj in distr["oriadj"]:
                        handled = self.GenForAdjacent(adj, oriadj) # original adjency is found and handled
                        if handled:
                            break
                    if not handled:
                        ll.append(f"UPDATE Adjacency_YieldChanges\nSET YieldChange = YieldChange * {self.__multiplier}\nWHERE ID = '{adj}';\n\n")

    def GetReplaceTypes(self, type_name):
        # get what this original object it replaces
        capital_t = type_name[0].upper() + type_name[1:]
        
        objects = self.GetAllTypes(capital_t+"s")
        if type_name == "improvement" or type_name == "project":
            return objects
        for row in self.GenRowList(capital_t+"Replaces"):
            if self.GetRowValue(row,"CivUnique"+capital_t+"Type") in objects:
                objects[self.GetRowValue(row,"CivUnique"+capital_t+"Type")]["Replaces"+capital_t+"Type"] = self.GetRowValue(row,"Replaces"+capital_t+"Type")
        return objects

    def GenForUnits(self):
        unit_other_properties = ["Combat","BaseSightRange", "BaseMoves", "BaseCombat", "RangedCombat", 
                                 "Range", "Bombard", "BuildCharges", "ReligiousStrength",
                                 "SpreadCharges", "ReligiousHealCharges",  "InitialLevel",
                                 "AirSlots", "AntiAirCombat", "ParkCharges", "DisasterCharges"]
        self.GenForObjectType("unit", unit_other_properties, {})

    def GenForObjectType(self, type_name, properties_list, gain_dict):
        
        capital_t = type_name[0].upper() + type_name[1:]

        ll = self.__sql_file_line_list
        if len(self.GenRowList(capital_t+"s")) >0:
            ll.append(f"\n\n-- {capital_t} infos\n")
        objects = self.GetReplaceTypes(type_name)
        strenth_keys = ["Combat", "BaseCombat", "RangedCombat", "AntiAirCombat", "ReligiousStrength", 
                        "Bombard", "OuterDefenseStrength", "DefenseModifier", "CityStrengthModifier"]

        for row in self.GenRowList(capital_t+"s"): # iterate over objects
            object_type = self.GetRowValue(row,capital_t+"Type")
            if "Replaces"+capital_t+"Type" in objects[object_type]:
                replace_object_type = objects[object_type]["Replaces"+capital_t+"Type"]
            else:
                replace_object_type = ""
            objects[object_type]["info"] = {}
            ori_info = {}
            for key in self.GetRowKeys(row):
                if len(replace_object_type) > 0:
                    ori_info[key] = self.__civ6_database_reader.get_data(capital_t+"s", {capital_t+"Type": replace_object_type}, key)
                    if ori_info[key] == None:
                        ori_info[key] = 0
                else:
                    ori_info[key] = 0
            
            updated_info = {}
            for key in self.GetRowKeys(row):
                value = self.GetRowValue(row,key)
                if key == "Cost" or key == "Maintenance" or key == "CostProgressionParam1":
                    if len(replace_object_type) > 0:
                        if float(value) >= float(ori_info[key]) or int(value) == 0:
                            continue
                        else:
                            value = float(ori_info[key])/(float(ori_info[key])/float(value))**self.__multiplier
                            value = int(round(value))
                    else:
                        value = int(round((float(value)/self.__multiplier)))

                if key in properties_list:
                    if key in strenth_keys:
                        if int(value) <= int(ori_info[key]):
                            continue
                        else:
                            value = int(ori_info[key]) + self.CalculateAttack(int(value) - int(ori_info[key]))
                            value = min(value, value+self.CalculateAttack(10))
                    else:
                        if value == None or int(value) <= int(ori_info[key]):
                            continue
                        else:
                            value = int(ori_info[key]) + (int(value) - int(ori_info[key])) * self.__multiplier


                if value != self.GetRowValue(row,key) and int(value) != int(self.GetRowValue(row,key)):
                    updated_info[key] = value
                objects[object_type]["info"][key] = value
            if len(updated_info) == 0:
                continue
            self.GenerateMultipleUpdate(capital_t+"s", updated_info, {capital_t+"Type": object_type})

            for k in gain_dict:
                if k == "_GreatWorks" and self.__change_great_work_slots == False:
                    continue
                self.GenGainForTable(capital_t+k, capital_t+"Type", object_type, replace_object_type, gain_dict[k])
    
    def GenForProjects(self):
        project_other_properties = {}
        gain_dict = {"_GreatPersonPoints":"GreatPersonClassType","_YieldConversions":"YieldType"}
        self.GenForObjectType("project", project_other_properties, gain_dict)


    def GenForImprovements(self):
        improvement_other_properties = ["Housing", "AirSlots", "DefenseModifier", "WeaponSlots", "ReligiousUnitHealRate"
                                        "Appeal", "YieldFromAppealPercent"]
        gain_dict = {"_BonusYieldChanges":"YieldType", "_YieldChanges":"YieldType"}
        self.GenForObjectType("improvement", improvement_other_properties, gain_dict)

        improvements = self.GetAllTypes("Improvements")
        if len(improvements) == 0:
            return

        ll = self.__sql_file_line_list
        adj_list = []
        for row in self.GenRowList("Improvement_Adjacencies"):
            if self.GetRowValue(row,"ImprovementType") in improvements:
                adj = self.GetRowValue(row,"YieldChangeId")
                adj_list.append(adj)
        if adj_list.__len__() == 0:
            return
        ll.append(f"UPDATE Adjacency_YieldChanges\nSET YieldChange = YieldChange * {self.__multiplier}\nWHERE ID IN (")
        for adj in adj_list:
            ll.append(f"'{adj}',\n")
        ll[-1] = ll[-1][:-2]+");\n\n"




    def GenForBuildings(self):
        # buildings = self.GetAllTypes("Buildings")
        building_other_properties = ["Entertainment", 
                               "Housing", "CitizenSlots", "RegionalRange", "OuterDefenseStrength",
                               "OuterDefenseHitPoints", "EntertainmentBonusWithPower"]
        
        gain_dict = {"_CitizenYieldChanges": "YieldType", "_GreatPersonPoints": "GreatPersonClassType"
                     ,"_GreatWorks": "GreatWorkSlotType", "_YieldChanges": "YieldType", "_YieldChangesBonusWithPower": "YieldType"}
        self.GenForObjectType("building", building_other_properties, gain_dict)


    def GetOriginalValue(self, table_name, type_key, type_value, gain_type_key, gain_type_value,gain_point_key):
        if type_value == "":
            return 0
        else:
            output = self.__civ6_database_reader.get_data(table_name, {type_key:type_value, gain_type_key:gain_type_value}, gain_point_key)
            if output == None:
                return 0
            return output
        
    def GenGainForTable(self, table_name, type_key, type_value, original_type_value, gain_type_key):
        ll = self.__sql_file_line_list
        init_line_written = False
        for row in self.GenRowList(table_name):
            if type_value != self.GetRowValue(row, type_key):
                continue
            gain_type_value = self.GetRowValue(row, gain_type_key)
            key_lists = self.GetRowKeys(row)
            key_lists.remove(type_key)
            key_lists.remove(gain_type_key)
            update_kv = {}
            for key in key_lists:
                if key == "Id" or key == "PointProgressionParam1":
                    continue
                original_value = self.GetOriginalValue(table_name, type_key, original_type_value, gain_type_key, gain_type_value, key)
                value = self.GetRowValue(row, key)
                if value == None or (type(value) == str and value[0].isalpha()):
                    continue
                if int(value) <= original_value:
                    continue
                else:
                    value = int(original_value) + (int(value) - int(original_value)) * self.__multiplier
                update_kv[key] = value
            if update_kv.__len__() >0 and not init_line_written:
                # ll.append(f"\n\n-- {table_name} for {type_value}\n\n")
                init_line_written = True
            if update_kv.__len__() >0:
                self.GenerateMultipleUpdate(table_name, update_kv, {type_key:type_value, gain_type_key:gain_type_value})


class power_multiplier_original(database_read):
    # only implement for pantheons


    def __init__(self, multiplier = 10):
        self.__civ6_database_reader = Database.Civ6DatabaseReader()
        self.__multiplier = multiplier
        database_read.__init__(self, self.__civ6_database_reader)

    

    def GenForPantheons(self):
        pantheons = []
        pantheon_types = []
        pantheon_mopdifiers = []
        pantheon_mopdifier_id = []
        for row in self.GenRowList("Beliefs"):
            if row["BeliefClassType"].find("PANTHEON") >= 0:
                pantheons.append(row)
                pantheon_types.append(row["BeliefType"])
        
        for row in self.GenRowList("BeliefModifiers"):
            if row["BeliefType"] in pantheon_types:
                pantheon_mopdifier_id.append(row["ModifierID"])

        # print(pantheon_mopdifier_id)
        mg = modifier_generator(pantheon_mopdifier_id, self.__civ6_database_reader, self.__multiplier)
        l1, l2, l3 = mg.GenerateAll()
        output_lines = []
        output_lines += l1
        output_lines += l2
        output_lines += l3
        with open(f"output/{self.__multiplier}xPantheon.sql", "w") as f:
            f.writelines(output_lines)
        print(f"output/{self.__multiplier}xPantheon.sql"+" generated!")
        
        





if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="path to mod folder, end with the steam workshop id")
    parser.add_argument("multiplier", help="multiplier for power", type=int)
    parser.add_argument('--disable-grant-unit' , help="not giving extra units", required=False, action="store_true")
    parser.add_argument('--disable-grant-gw-slot' , help="not giving extra great work slots", required=False, action="store_true")
    # parser.add_argument('-d','--duplcate-modifier-list',nargs='+', required=False ,  help="some modifiers need to be dupilicate to work\n since there is no numerical argument to change.", action="store")

    args = parser.parse_args()
    print(args.multiplier)


    # InitDatabase()
    # get_data()
    

    generator = mod_power_multiplier(args.path, multiplier=args.multiplier, 
                                     grant_unit=(not args.disable_grant_unit), change_great_work_slots = (not args.disable_grant_gw_slot))
    generator.GenerateAll()

    # original_generator = power_multiplier_original(multiplier=multiplier)
    # original_generator.GenForPantheons()
    # parser.PrintAll()