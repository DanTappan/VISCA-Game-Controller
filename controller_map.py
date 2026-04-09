#
# controller_map - functions for mapping joystick names to a JSON file
# defining controller functions
#

import json
from json import JSONDecodeError

import file_paths
from win_print import win_print

controller_map_file = "CONTROLLER_MAP.json"

def controller_map(name: str, dump = None) -> dict | None:
    """ Map a controller name to a file containing the function definitions """
    win_print(f'{name} connected')
    map_name = file_paths.search_path(controller_map_file)

    if map_name is None:
        return None

    with open(map_name, 'r') as f:
        map_dict = json.load(f)

    for key in [ name, "default"]:
        controller_path = map_dict.get(key)
        if controller_path is not None:
            break

    win_print(f'loading {controller_path}')

    controller_dict = None
    if dump is None:
        controller_path = file_paths.search_path(controller_path)
#        win_print(f'-> {controller_path}')
        if controller_path is not None:
            with open(controller_path, 'r') as f:
                try:
                    controller_dict = json.load(f)
                except JSONDecodeError:
                    pass
    else:
        # Dump out file to initialize
        with open(controller_path, 'w') as f:
            json.dump(dump, f)

    return controller_dict
