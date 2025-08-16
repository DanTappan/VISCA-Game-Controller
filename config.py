#
# Configuration Functions for VISCA Joystick
#
import gc
import PySimpleGUI as Sg

g_Debug = False

g_Progname = "VISCA Game Controller"
g_ProgVers = "1.0beta2"

g_num_cams = 8
cam_ips = ['127.0.0.1']*g_num_cams
cam_ports = [52381]*g_num_cams

sensitivity_tables = {
    'pan': {'joy': [0, 0.15, 0.2, 0.3, 0.5, 0.8, 0.9, 1], 'cam': [0, 0, 1, 2, 6,  8, 12, 18]},
    'tilt': {'joy': [0, 0.15, 0.2, 0.3, 0.5, 0.8, 0.9, 1], 'cam': [0, 0, 1, 3, 6, 8, 12, 18]},
    'zoom': {'joy': [0, 0.15, 0.2, 0.3, 0.4, 0.5, 0.7, 1], 'cam': [0, 0, 1, 1, 1, 3, 5, 7]},
    'focus': {'joy': [0, 0.2, 0.3, 0.7, 1], 'cam':[0, 0, 2, 5, 7]},
}

g_long_press_time = 0
g_invert_tilt = False
g_swap_pan = False
g_dead_zone = None

# Bitfocus companion interface
# the trigger commands are assumed to all be on one page (currently defaults to 99)
g_companion_page = 99

def configure():
    """ Configuration dialog """
    global g_long_press_time, g_Debug, g_companion_page, g_swap_pan, g_invert_tilt, g_dead_zone

    layout = [[Sg.Text("Camera", size=20), Sg.Text("Port")],
              [Sg.Input(default_text=cam_ips[0], key='CAM1', size=20),
               Sg.Input(default_text=str(cam_ports[0]), key='PORT1', size=8)],
              [Sg.Input(default_text=cam_ips[1], key='CAM2', size=20),
               Sg.Input(default_text=str(cam_ports[1]), key='PORT2', size=8)],
              [Sg.Input(default_text=cam_ips[2], key='CAM3', size=20),
               Sg.Input(default_text=str(cam_ports[2]), key='PORT3', size=8)],
              [Sg.Input(default_text=cam_ips[3], key='CAM4', size=20),
               Sg.Input(default_text=str(cam_ports[3]), key='PORT4', size=8)],
              [Sg.Input(default_text=cam_ips[4], key='CAM5', size=20),
               Sg.Input(default_text=str(cam_ports[4]), key='PORT5', size=8)],
              [Sg.Input(default_text=cam_ips[5], key='CAM6', size=20),
               Sg.Input(default_text=str(cam_ports[5]), key='PORT6', size=8)],
              [Sg.Input(default_text=cam_ips[6], key='CAM7', size=20),
               Sg.Input(default_text=str(cam_ports[6]), key='PORT7', size=8)],
              [Sg.Input(default_text=cam_ips[7], key='CAM8', size=20),
               Sg.Input(default_text=str(cam_ports[7]), key='PORT8', size=8)],
              [Sg.Text('Long Press (restart required)'),
               Sg.Input(default_text=str(g_long_press_time), key='-LONG-PRESS-', size=4), Sg.Text('seconds')],
              [Sg.Text('Joystick dead zone (restart required)'),
               Sg.Input(default_text=str(g_dead_zone or ''), key='-DEAD-ZONE-', size=4)],
              [Sg.Text('Bitfocus Companion Page '),
               Sg.Input(default_text=str(g_companion_page), key='-COMPANION-PAGE-', size=4)],
              [Sg.Checkbox('Invert Tilt', default=g_invert_tilt, key='-INVERT-TILT-'),
               Sg.Checkbox('Swap Pan', default=g_swap_pan, key='-SWAP-PAN-'),
               Sg.Checkbox('Debug Mode', default=g_Debug, key='-DEBUG-')],
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
            for x in range(g_num_cams):
                window['CAM'+str(x+1)].update(value='127.0.0.1')
                window['PORT'+str(x+1)].update(value=str(10000+x+1))

        elif event == 'Save':
            for x in range(g_num_cams):
                cam_ips[x] = values['CAM'+str(x+1)]
                cam_ports[x] = int(values['PORT'+str(x+1)])
                Sg.user_settings_set_entry('-CAM' + str(x+1) + '-', cam_ips[x])
                Sg.user_settings_set_entry('-PORT' + str(x+1) + '-', cam_ports[x])

            try:
                g_long_press_time = float(values['-LONG-PRESS-'])
            except ValueError:
                g_long_press_time = 0.5
            g_Debug = values['-DEBUG-']
            g_invert_tilt = values['-INVERT-TILT-']
            g_swap_pan = values['-SWAP-PAN-']
            g_dead_zone = values['-DEAD-ZONE-']
            try:
                g_dead_zone = float(g_dead_zone)
            except ValueError:
                g_dead_zone = None
            g_companion_page = int(values['-COMPANION-PAGE-'])
            Sg.user_settings_set_entry('-long_press_time-', g_long_press_time)
            Sg.user_settings_set_entry('-companion_page-', g_companion_page)
            Sg.user_settings_set_entry('-invert-tilt-', g_invert_tilt)
            Sg.user_settings_set_entry('-swap-pan-', g_swap_pan)
            Sg.user_settings_set_entry('-debug-', g_Debug)
            Sg.user_settings_set_entry('-dead-zone-', g_dead_zone)
            Sg.user_settings_set_entry('-configured-', True)
            break

    window.close()
    # 'fix' for PySimpleGUI/Tkintr issue with threading
    del layout
    del window
    gc.collect()


def load_config():
    """ Load the saved configuration values at startup """
    global g_long_press_time, g_invert_tilt, g_swap_pan, g_companion_page, g_Debug, g_dead_zone

    for x in range(g_num_cams):
        cam_ips[x] = Sg.user_settings_get_entry('-CAM'+str(x+1)+'-', '')
        port = Sg.user_settings_get_entry('-PORT' + str(x + 1) + '-', 52381)
        cam_ports[x] = port

    g_companion_page = Sg.user_settings_get_entry('-companion_page-', 99)
    g_long_press_time = Sg.user_settings_get_entry('-long_press_time-', .5)
    g_invert_tilt = Sg.user_settings_get_entry('-invert-tilt-', False)
    g_swap_pan = Sg.user_settings_get_entry('-swap-pan-', False)
    g_Debug = Sg.user_settings_get_entry('-debug-', False)
    g_dead_zone = Sg.user_settings_get_entry('-dead-zone-', None)
    if not Sg.user_settings_get_entry('-configured-', False):
        configure()

credits_text = """
Dan Tappan (https://dantappan.net) - (c) 2024, 2025

Written/debugged using PyCharm Community Edition 
    https://www.jetbrains.com/pycharm/

Derived from:
    https://github.com/International-Anglican-Church/visca-joystick

VISCA Camera control: 
     https://github.com/misterhay/VISCA-IP-Controller

Graphical interface: 
    PySimpleGUI-foss 
    https://github.com/andor-pierdelacabeza/PySimpleGUI-4-foss
    psgtray-foss

Joystick Handling: pygame (https://www.pygame.org/)

Icon based on: 
    https://www.flaticon.com/free-icon/gamepad_8037145
    created by Hilmy Abiyyu
 """

class Config:
    global g_dead_zone, g_Debug, g_Progname, g_ProgVers, g_invert_tilt, g_swap_pan, g_num_cams, g_long_press_time

    def __init__(self):
        self.mappings = None
        # True == 'use buttons for brightness', False == 'use a joystick for brightness'
        self._brightness_button = True
        load_config()

    @staticmethod
    def companion(row:int, column:int):
        return [g_companion_page, row, column]

    @staticmethod
    def sensitivity(table: str):
        return sensitivity_tables[table]

    @property
    def progname(self):
        return g_Progname
    @property
    def progvers(self):
        return g_ProgVers

    @property
    def invert_tilt(self):
        return g_invert_tilt

    @property
    def swap_pan(self):
        return g_swap_pan

    @property
    def long_press_time(self):
        return g_long_press_time

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
    def num_cams(self):
        return g_num_cams

    @property
    def debug(self):
        return g_Debug

    @property
    def dead_zone(self):
        return g_dead_zone

    @property
    def credits_text(self):
        return f"{g_Progname} {g_ProgVers}\n"+credits_text

    @property
    def brightness_button(self):
        return self._brightness_button
