from mijnstroom.config import load_config
from mijnstroom.storage import Storage


def main():
    config = load_config()
    storage = Storage(config)
    storage.init()
