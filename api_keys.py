from configparser import ConfigParser, Error
import os
from pathlib import Path


CONFIG_PATH = Path(__file__).with_name("config.ini")


def get_api_key(name):
    config = ConfigParser(interpolation=None)
    try:
        with CONFIG_PATH.open(encoding="utf-8-sig") as stream:
            config.read_file(stream)
    except FileNotFoundError:
        pass
    except Error:
        raise ValueError("Invalid Prism config.ini. Check its INI format.") from None

    key = config.get("api_keys", name, fallback="").strip()
    if len(key) >= 2 and key[0] in ("'", '"') and key[-1] == key[0]:
        key = key[1:-1]
    key = key or os.getenv(name)
    if not key:
        raise ValueError(f"Set {name} under [api_keys] in Prism config.ini or in the environment.")
    return key
