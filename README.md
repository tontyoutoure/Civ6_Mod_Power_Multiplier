# Civ6 Mod Power Multiplier

This project is for the generation of .sql file for mods civizations, making them more powerful, like those in https://github.com/username4/civ6_x3_mod 

## usage 

1. One should locate the mod folder for the mod civization. It's something like "D:\SteamLibrary\steamapps\workshop\content\289070\1662972647"

2. One should get Python in their computer. Average user can get one in the microsoft store. Also you would need the "sqlparse" module. You can install it by "pip install sqlparse"

3. Run the script by 
```
python GenForXml.py "D:\SteamLibrary\steamapps\workshop\content\289070\1662972647" 10
```
meaning modify the power of the mod civization by 10 times. Then the modification sql file would be located in the output folder. In this case, it should be named as "1662972647_x10.sql".

4. move sql file to the civilization trait mod folder, add it into the modinfo file.

## TODO

civilization trait mod auto generation
wonder/suzerain/patheon mod auto generation
localization auto generation (numbers only)


