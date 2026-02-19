import configparser

config_path = "config.ini"


def read_config_parameter(module, value):
    config = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
    config.read(config_path)
    return config.get(module, value)


def print_config():
    config = configparser.ConfigParser()
    config.read(config_path)
    for section in config.sections():
        print("\033[1;4m{}\033[0m".format(section))
        for key, value in config[section].items():
            print("{}: {}".format(key, value))