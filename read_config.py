import sys
import os
from configparser import ConfigParser

if len(sys.argv) != 3:
    sys.exit(1)

config_path = sys.argv[1]
key = sys.argv[2]

if not os.path.isfile(config_path):
    sys.exit(1)

config = ConfigParser()
config.read(config_path)

# Ищем ключ во всех секциях
for section in config.sections():
    if key in config[section]:
        print(config[section][key])
        sys.exit(0)

# Не найдено — пустая строка (но .bat обработает как "не defined")
print("")
sys.exit(1)