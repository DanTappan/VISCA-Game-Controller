#
# Configuration Functions for VISCA Joystick
#
import gc
import PySimpleGUI as Sg

Debug = False

num_cams = 4
cam_ips = ['10.100.1.202', '10.100.1.116', '0.0.0.0', '0.0.0.0']
cam_ports = [52381, 52381, 0, 0]

sensitivity_tables = {
    'pan': {'joy': [0, 0.05, 0.3, 0.7, 0.9, 1], 'cam': [0, 0, 2, 8, 15, 20]},
    'tilt': {'joy': [0, 0.07, 0.3, 0.65, 0.85, 1], 'cam': [0, 0, 3, 6, 14, 18]},
    'zoom': {'joy': [0, 0.1, 1], 'cam': [0, 0, 7]},
    'focus': {'joy': [0, 0.1, 1], 'cam':[0, 0, 7]},
}
long_press_time = 1.5
invert_tilt = False
swap_pan = False
# Bitfocus companion interface
# the trigger commands are assumed to all be on one page (currently hardwired to 99)
companion_page = 99

def configure():
    """ Configuration dialog """
    global long_press_time, Debug, companion_page, swap_pan, invert_tilt

    layout = [[Sg.Text("Camera", size=20), Sg.Text("Port")],
              [Sg.Input(default_text=cam_ips[0], key='CAM1', size=20),
               Sg.Input(default_text=str(cam_ports[0]), key='PORT1', size=8)],
              [Sg.Input(default_text=cam_ips[1], key='CAM2', size=20),
               Sg.Input(default_text=str(cam_ports[1]), key='PORT2', size=8)],
              [Sg.Input(default_text=cam_ips[2], key='CAM3', size=20),
               Sg.Input(default_text=str(cam_ports[2]), key='PORT3', size=8)],
              [Sg.Input(default_text=cam_ips[3], key='CAM4', size=20),
               Sg.Input(default_text=str(cam_ports[3]), key='PORT4', size=8)],
              [Sg.Text('Long Press (restart required)'),
               Sg.Input(default_text=str(long_press_time), key='LONGPRESS', size=4), Sg.Text('seconds')],
              [Sg.Text('Bitfocus Companion Page '),
               Sg.Input(default_text=str(companion_page), key='COMPANIONPAGE', size=4)],
              [Sg.Checkbox('Invert Tilt', default=invert_tilt, key='-INVERT-TILT-'),
               Sg.Checkbox('Swap Pan', default=swap_pan, key='-SWAP-PAN-'),
               Sg.Checkbox('Debug Mode', False, key='-DEBUG-')],
              [Sg.Button('Relay', tooltip='Fill in values for VISCA Relay'),
               Sg.Button('Save'),
               Sg.Button('Cancel')]
              ]
    window = Sg.Window(title='Configure', layout=layout, finalize=True, keep_on_top=True)

    while True:
        event, values = window.read()

        if event == 'Cancel' or event == Sg.WINDOW_CLOSED:
            break

        elif event == 'Relay':
            for x in range(4):
                window['CAM'+str(x+1)].update(value='127.0.0.1')
                window['PORT'+str(x+1)].update(value=str(10000+x+1))

        elif event == 'Save':
            for x in range(4):
                cam_ips[x] = values['CAM'+str(x+1)]
                cam_ports[x] = int(values['PORT'+str(x+1)])
                Sg.user_settings_set_entry('-CAM' + str(x+1) + '-', cam_ips[x])
                Sg.user_settings_set_entry('-PORT' + str(x+1) + '-', cam_ports[x])

            long_press_time = int(values['LONGPRESS'])
            Debug = values['-DEBUG-']
            invert_tilt = values['-INVERT-TILT-']
            swap_pan = values['-SWAP-PAN-']
            companion_page = int(values['COMPANIONPAGE'])
            Sg.user_settings_set_entry('-long_press_time-', long_press_time)
            Sg.user_settings_set_entry('-companion_page-', companion_page)
            Sg.user_settings_set_entry('-invert-tilt-', invert_tilt)
            Sg.user_settings_set_entry('-swap-pan-', swap_pan)
            Sg.user_settings_set_entry('-configured-', True)
            break

    window.close()
    # 'fix' for PySimpleGUI/Tkintr issue with threading
    del layout
    del window
    gc.collect()


def load_config():
    """ Load the saved configuration values at startup """
    global long_press_time, invert_tilt, swap_pan, companion_page

    for x in range(4):
        cam_ips[x] = Sg.user_settings_get_entry('-CAM'+str(x+1)+'-', '127.0.0.1')
        port = Sg.user_settings_get_entry('-PORT' + str(x + 1) + '-', 52381)
        cam_ports[x] = port

    companion_page = Sg.user_settings_get_entry('-companion_page-', 99)
    long_press_time = Sg.user_settings_get_entry('-long_press_time-', 2)
    invert_tilt = Sg.user_settings_get_entry('-invert-tilt-', False)
    swap_pan = Sg.user_settings_get_entry('-swap-pan-', False)

    if not Sg.user_settings_get_entry('-configured-', False):
        configure()




credits_text = """
Dan Tappan (https://dantappan.net) - 2024

Written/debugged using PyCharm Community Edition (https://www.jetbrains.com/pycharm/)

Derived from https://github.com/International-Anglican-Church/visca-joystick

VISCA Camera control: https://github.com/misterhay/VISCA-IP-Controller

Graphical interface: PySimpleGUI (https://www.pysimplegui.com/) and psgtray (https://github.com/PySimpleGUI/psgtray)

Joystick Handling: pygame (https://www.pygame.org/)

Icon based on: https://www.flaticon.com/free-icon/gamepad_8037145 - created by Hilmy Abiyyu A
 """


class Config:
    def __init__(self):
        self.mappings = None
        # True == 'use buttons for brightness', False == 'use a joystick for brightness'
        self._brightness_button = True
        load_config()

    @staticmethod
    def companion(row:int, column:int):
        return [companion_page, row, column]

    @staticmethod
    def sensitivity(table: str):
        return sensitivity_tables[table]

    @property
    def invert_tilt(self):
        return invert_tilt

    @property
    def swap_pan(self):
        return swap_pan

    @property
    def long_press_time(self):
        return long_press_time

    @staticmethod
    def cam_address(idx):
        try:
            return cam_ips[idx], cam_ports[idx]
        except IndexError:
            return None, 0

    @staticmethod
    def configure():
        configure()

    @property
    def help_text(self):
        return help_text

    @property
    def debug(self):
        return Debug

    @property
    def credits_text(self):
        return credits_text

    @property
    def brightness_button(self):
        return self._brightness_button
