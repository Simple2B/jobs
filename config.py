import json
import pathlib

CONFIG_FILE = pathlib.Path(__file__).parent.absolute().joinpath('config.json')


class Configuration():
    def __init__(self):
        with open(CONFIG_FILE, 'r') as f:
            self.__conf = json.load(f)

    def __getitem__(self, name: str):
        return self.__conf[name]


config = Configuration()
