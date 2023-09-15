import sqlite3
import os
import sys
import xml
import xml.etree.ElementTree as ET
import glob
import math
import Database

class xml_parser():
    __kind_type_dict = {}
    __table_column_dict = {}
    __xml_tree_list = []
    __sql_file_line_list = []
    __sql_slot_line_list = []
    __sql_grant_unit_line_list = []

    __grant_unit_modifier_list = []
    __combat_modifier_list = []
    __government_slot_modifier_dict = {}
    
    def __init__(self, path, multiplier = 10, change_great_work_slots = False,
                 grant_unit = True, single_file = False):
        if os.path.exists("output") == False:
            os.mkdir("output", )
        self.__prefix = "output/"+os.path.basename(os.path.normpath(path))+"_x"+str(multiplier)

        self.__grant_unit = grant_unit
        self.__path = path
        self.__change_great_work_slots = change_great_work_slots # it may crush the game
        self.__single_file = single_file

        for filename in glob.glob(os.path.join(path, '**/*.xml')):
            tree = ET.parse(filename)
            self.__xml_tree_list.append(tree)
        self.__multiplier = multiplier
            
        for filename in glob.glob(os.path.join(path, '*.xml')):
            tree = ET.parse(filename)
            self.__xml_tree_list.append(tree)
        print (f"{len(self.__xml_tree_list)} xml files loaded")
        self.__database_parser = Database.Civ6DatabaseParser()


    
    def GenRowList(self, table_name):
        output = []
        for tree in self.__xml_tree_list:
            alltables = tree.findall(table_name)
            if len(alltables) > 0:
                for tagnode in alltables:
                    tagnode_row_list = tagnode.findall("Row")
                    output+=tagnode_row_list
        return output

    def GetRowKeys(self, row):
        output = []
        if len(row.keys()) > 0:
            return row.keys()
        else:
            for key in row.iter():
                if key.tag != "Row":
                    output.append(key.tag)
            return output

    def GetRowkvs(self, row, initial = {}):
        output = initial
        for key in self.GetRowKeys(row):
            if not key in output:
                output[key] = []
            output[key].append(self.GetRowValue(row, key))
        return output

    def GetRowValue(self, row, name):
        if row.find(name) != None:
            return row.find(name).text
        else:
            return row.get(name)
        
    # def PrintAll(self):
    #     print(self.__table_column_dict)
    #     print(self.__kind_type_dict)

    def GetAllTableColumn(self, table_name, column_name):
        self.__table_column_dict[table_name] = []
        for row in self.GenRowList(table_name):
            self.__table_column_dict[table_name].append(self.GetRowValue(row, column_name))
    
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
    
    def GenerateInsertHead(self, table_name, key_list):
        output = f"INSERT INTO {table_name} ("
        for key in key_list:
            output += f"{key}, "
        output = output[:-2]+")\nVALUES\n"
        return output
    
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
    
    def GenerateIndertLine(self, value_list, last = False):
        output = "("
        for value in value_list:
            if type(value) == str:
                output += f"'{value}', "
            else:
                output += f"{value}, "
        output = output[:-2]+")"
        if not last:
            output += ",\n"
        else:
            output += ";\n\n"
        return output

    def GetGovSlotInjector(self, mid):#injector is not TraitType
        injector = {}
        for tree in self.__xml_tree_list:
            root = tree.getroot()
            for tab in root:
                if tab.tag in ["Modifiers", "ModifierArguments", "ModifierStrings"]:
                    continue
                rl = tab.findall("Row")
                for row in rl:
                    if self.GetRowValue(row, "ModifierId") == mid:
                        if not tab.tag in injector:
                            injector[tab.tag] = {}
                            
                        for key in self.GetRowKeys(row):
                            if not key in injector[tab.tag]:
                                injector[tab.tag][key] = []
                            injector[tab.tag][key].append(self.GetRowValue(row, key))
        return injector

    def AddGovSlotInjector(self, gov_slot_m_dict, mid):
        d = gov_slot_m_dict[mid]
        ll = self.__sql_slot_line_list
        injector = self.GetGovSlotInjector(mid)
        for tab in injector:
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
    
    def AddGovSlotModifierInfo(self, gov_slot_m_dict, mid):     
        d = gov_slot_m_dict[mid]["info"]
        ll = self.__sql_slot_line_list        
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
        for row in self.GenRowList("Modifiers"):
            if self.GetRowValue(row,"ModifierType").find("GOVERNMENT_SLOT") >= 0:
                mid = self.GetRowValue(row,"ModifierId")
                gov_slot_m_dict[mid]={"info":{}}
                for key in self.GetRowKeys(row):
                    gov_slot_m_dict[mid]["info"][key] = self.GetRowValue(row,key)

        for row in self.GenRowList("ModifierArguments"):
            mid = self.GetRowValue(row,"ModifierId")
            if mid in gov_slot_m_dict:
                gov_slot_m_dict[mid][self.GetRowValue(row,"Name")] = self.GetRowValue(row,"Value")
                
        # begin to generate sql
        for mid in gov_slot_m_dict:
            d = gov_slot_m_dict[mid]
            ll = self.__sql_slot_line_list
            self.AddGovSlotInjector(gov_slot_m_dict, mid)

            self.AddGovSlotModifierInfo(gov_slot_m_dict, mid)

            ll.append(f"INSERT INTO ModifierArguments (ModifierId, Name, Value)\nVALUES\n")
            if d["info"]['ModifierType'] == "MODIFIER_PLAYER_CULTURE_REPLACE_GOVERNMENT_SLOTS":
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
                for i in range(self.__multiplier-2):
                    ll.append(f"('{mid}_{i+1}', 'GovernmentSlotType', '{d['GovernmentSlotType']}'),\n")
                ll.append(f"('{mid}_{self.__multiplier-1}', 'GovernmentSlotType', '{d['GovernmentSlotType']}');\n\n")



    def GenAllCombatModifier(self):
        lines = self.__sql_file_line_list
        self.__sql_file_line_list.append(f"-- Combat Strength Modifiers\n")
        lines.append("-- formula is: 25*ln({modifier})*exp({original_strength}/25)-{modifier-1})\n\n\n")
        for row in self.GenRowList("Modifiers"):
            if self.GetRowValue(row,"ModifierType").find("STRENGTH") >= 0:
                self.__combat_modifier_list.append(self.GetRowValue(row,"ModifierId"))
        # print("combat modif list:", self.__combat_modifier_list)

        for row in self.GenRowList("ModifierArguments"):
            if self.GetRowValue(row,"Name") == "Amount" and self.GetRowValue(row,"ModifierId") in self.__combat_modifier_list:
                strength = self.GetRowValue(row,"Value")
                self.__sql_file_line_list.append(f"UPDATE ModifierArguments\n")
                self.__sql_file_line_list.append(f"SET Value = {self.CalculateAttack(int(strength))}\n")
                self.__sql_file_line_list.append(f"WHERE ModifierId = '{self.GetRowValue(row,'ModifierId')}'\n")
                self.__sql_file_line_list.append(f"AND Name = 'Amount';\n\n")
    
    def GenGrantUnitModifier(self):
        if self.__grant_unit == False:
            return
        self.__sql_grant_unit_line_list = []
        for row in self.GenRowList("Modifiers"):
            if self.GetRowValue(row,"ModifierType").find("GRANT_UNIT") >= 0:
                self.__grant_unit_modifier_list.append(self.GetRowValue(row,"ModifierId"))
        
        for mid in self.__grant_unit_modifier_list:
            self.__sql_grant_unit_line_list.append(f"UPDATE ModifierArguments\n")
            self.__sql_grant_unit_line_list.append(f"SET Value = Value * {self.__multiplier}\n")
            self.__sql_grant_unit_line_list.append(f"WHERE ModifierId = '{mid}'\n")
            self.__sql_grant_unit_line_list.append(f"AND Name = 'Amount';\n\n")
        


    def GenAmountChangeForAllOtherModifiers(self):
        self.__normal_modifier_list = []
        modifier_list_with_arguments = []
        modifier_list_with_multiple_values = {}
        ll = self.__sql_file_line_list
        numeric_value_names = ["Amount", "YieldChange", "YieldBasedOnAppeal", "UnitProductionPercent",
                               "UnitCostPercent", "TurnsActive", "Turns", "TechBoost","SCRIPTURE_SPEAD_STRENGTH",
                               "Range", "Radius","Multiplier", "Modifier", "Discount"]
        modifier_list_scaling_factor = {}
        for row in self.GenRowList("Modifiers"):
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

    def WriteAll(self):
        if self.__single_file:
            self.__sql_file_line_list += self.__sql_slot_line_list
            self.__sql_file_line_list += self.__sql_grant_unit_line_list
            with open(self.__prefix+".sql", "w") as f:
                f.writelines(self.__sql_file_line_list)
            print("<file>"+self.__prefix+".sql"+"<file>")

        else:    
            if len(self.__sql_slot_line_list) > 0:
                with open(self.__prefix+"_gslot.sql", "w") as f:
                    f.writelines(self.__sql_slot_line_list)
                print("<file>"+self.__prefix+"_gslot.sql"+"<file>")

            with open(self.__prefix+".sql", "w") as f:
                f.writelines(self.__sql_file_line_list)
            print("<file>"+self.__prefix+".sql"+"<file>")

            if self.__grant_unit:
                with open(self.__prefix+"_grant_unit.sql", "w") as f:
                    f.writelines(self.__sql_grant_unit_line_list)
                print("<file>"+self.__prefix+"_grant_unit.sql"+"<file>")

    def ParseAll(self):
        self.GenForGovernmentSlotModifier()

        self.GenAllCombatModifier()
        self.GenGrantUnitModifier()
        self.GenAmountChangeForAllOtherModifiers() # may cause error, need to check
        self.GenForBuildings()
        self.GenForDistricts()
        self.GenForImprovements()
        self.GenForUnits()
        self.WriteAll()

    def GenForAdjacent(self, adj, oriadj):
        ll = self.__sql_file_line_list
        kv_adj = self.__database_parser.get_kv("Adjacency_YieldChanges", "ID", adj)
        kv_oriadj = self.__database_parser.get_kv("Adjacency_YieldChanges", "ID", oriadj)
        checklist = ["YieldType", "OtherDistrictAdjacent", "AdjacentTerrain", "AdjacentFeature",
                     "AdjacentRiver", "AdjacentWonder","AdjacentResource","AdjacentNaturalWonder",
                     "AdjacentImprovement","AdjacentDistrict","PrereqCivic","PrereqTech"]
        
        output = True
        for key in checklist:
            output = output and( kv_adj[key]!= None and kv_adj[key] == kv_oriadj[key])
        
        if output == True:
            c1 = int(kv_oriadj["YieldChange"])
            c2 = int(kv_adj["YieldChange"])
            t1 = int(kv_oriadj["TilesRequired"])
            t2 = int(kv_adj["TilesRequired"])
            if t1 == t2:
                if c2 > c1:
                    change = int(c1 + (c2-c1)*self.__multiplier)
                    ll.append(f"UPDATE District_Adjacencies\nSET YieldChange = {change}\nWHERE ID = '{adj}';\n\n")
            elif t2 < t1 and float(c2)/(t2) > float(c1)/(t1):
                change = (c2 * t1/t2 - c1)*self.__multiplier + c1
                ll.append(f"UPDATE District_Adjacencies\nSET TilesRequired = {t1}, YieldChange = {change}\nWHERE ID = '{adj}';\n\n")
            elif  float(c2)/(t2) > float(c1)/(t1):
                change = (c2 - c1*t2/t1)*self.__multiplier + c1*t2/t1
                ll.append(f"UPDATE District_Adjacencies\nSET YieldChange = {change}\nWHERE ID = '{adj}';\n\n")
                 
        return output
        
    def GenForDistricts(self):
        district_other_properties = ["HitPoints","Appeal", "Housing", "Entertainment", 
                                      "AirSlots", "CitizenSlots", "CityStrengthModifier"]

        gain_dict = {"_GreatPersonPoints": "GreatPersonClassType", "_CitizenGreatPersonPoints": "GreatPersonClassType", "_CitizenYieldChanges": "YieldType","_TradeRouteYields": "YieldType"}
        self.GenForObjectType("district", district_other_properties, gain_dict)

        districts = self.GetReplaceTypes("district")
        for dis in districts:
            districts[dis]["adj"] = []
                
        ll = self.__sql_file_line_list
        for row in self.GenRowList("District_Adjacencies"):
            if self.GetRowValue(row,"DistrictType") in districts:
                districts[self.GetRowValue(row,"DistrictType")]["adj"].append(self.GetRowValue(row,"YieldChangeId"))

        for dis in districts:
            distr = districts[dis]
            if "adj" not in distr:
                continue
            if "ReplacesDistrictType" not in distr or self.__database_parser.is_in("District_Adjacencies", "DistrictType", distr["ReplacesDistrictType"]) == False:
                for adj in distr["adj"]:
                    ll.append(f"UPDATE District_Adjacencies\nSET YieldChange = YieldChange * {self.__multiplier}\nWHERE ID = '{adj}';\n\n")
            else:
                distr["oriadj"] = self.__database_parser.get_column("District_Adjacencies", {"DistrictType": distr["ReplacesDistrictType"]}, "YieldChangeId")
                for adjid in distr["adj"]:
                    if adjid in distr["oriadj"]:
                        distr["adj"].remove(adjid)
                for adj in distr["adj"]:
                    for oriadj in distr["oriadj"]:
                        handled = self.GenForAdjacent(adj, oriadj)
                        if handled:
                            break
                    if not handled:
                        ll.append(f"UPDATE District_Adjacencies\nSET YieldChange = YieldChange * {self.__multiplier}\nWHERE ID = '{adj}';\n\n")

    def GetReplaceTypes(self, type_name):
        capital_t = type_name[0].upper() + type_name[1:]
        
        objects = self.GetAllTypes(capital_t+"s")
        if type_name == "improvement":
            return objects
        for row in self.GenRowList(capital_t+"Replaces"):
            if self.GetRowValue(row,"CivUnique"+capital_t+"Type") in objects:
                objects[self.GetRowValue(row,"CivUnique"+capital_t+"Type")]["Replaces"+capital_t+"Type"] = self.GetRowValue(row,"Replaces"+capital_t+"Type")
        return objects

    def GenForUnits(self):
        unit_other_properties = ["BaseSightRange", "BaseMoves", "BaseCombat", "RangedCombat", 
                                 "Range", "Bombard", "BuildCharges", "ReligiousStrength",
                                 "SpreadCharges", "ReligiousHealCharges",  "InitialLevel",
                                 "AirSlots", "AntiAirCombat", "ParkCharges", "DisasterCharges"]

        pass

    def GenForObjectType(self, type_name, properties_list, gain_dict):
        
        capital_t = type_name[0].upper() + type_name[1:]

        ll = self.__sql_file_line_list
        ll.append(f"\n\n-- {capital_t} infos\n")
        objects = self.GetReplaceTypes(type_name)
        strenth_keys = ["BaseCombat", "RangedCombat", "AntiAirCombat", "ReligiousStrength", 
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
                    ori_info[key] = self.__database_parser.get_data(capital_t+"s", {capital_t+"Type": replace_object_type}, key)
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
                            value_new = int(ori_info[key]) + self.CalculateAttack(int(value) - int(ori_info[key]))
                            value_new = min(value_new, value+self.CalculateAttack(10))
                    else:
                        if int(value) <= int(ori_info[key]):
                            continue
                        else:
                            value = int(ori_info[key]) + (int(value) - int(ori_info[key])) * self.__multiplier


                if value != self.GetRowValue(row,key) and int(value) != int(self.GetRowValue(row,key)):
                    updated_info[key] = value
                objects[object_type]["info"][key] = value
            self.GenerateMultipleUpdate(capital_t+"s", updated_info, {capital_t+"Type": object_type})

            for k in gain_dict:
                if k == "_GreatWorks" and self.__change_great_work_slots == False:
                    continue
                self.GenGainForTable(capital_t+k, capital_t+"Type", object_type, replace_object_type, gain_dict[k])
        

    def GenForImprovements(self):
        improvement_other_properties = ["Housing", "AirSlots", "DefenseModifier", "WeaponSlots", "ReligiousUnitHealRate"
                                        "Appeal", "YieldFromAppealPercent"]
        gain_dict = {"_BonusYieldChanges":"YieldType", "_YieldChanges":"YieldType"}
        self.GenForObjectType("improvement", improvement_other_properties, gain_dict)

        improvements = self.GetAllTypes("Improvements")

        ll = self.__sql_file_line_list
        adj_list = []
        for row in self.GenRowList("Improvement_Adjacencies"):
            if self.GetRowValue(row,"ImprovementType") in improvements:
                adj = self.GetRowValue(row,"YieldChangeId")
                adj_list.append(adj)
        
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
            output = self.__database_parser.get_data(table_name, {type_key:type_value, gain_type_key:gain_type_value}, gain_point_key)
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
                original_value = self.GetOriginalValue(table_name, type_key, original_type_value, gain_type_key, gain_type_value, key)
                value = self.GetRowValue(row, key)
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


    def GenForAllTraitModifier(self):
        self.GetAllTableColumn("TraitModifiers", "ModifierId")
        self.GetAllTableColumn("AgendaTraits", "TraitType") 
        self.RemoveAllAgendaTrait()

        for tree in self.__xml_tree_list:
            if tree.find("ModifierArguments") != None:
                pass

if __name__ == '__main__':
    # InitDatabase()
    # get_data()
    #D:\SteamLibrary\steamapps\workshop\content\289070\3003039611
    parser = xml_parser("D:\\SteamLibrary\\steamapps\\workshop\\content\\289070\\2048816113\\")
    parser.ParseAll()
    # parser.PrintAll()