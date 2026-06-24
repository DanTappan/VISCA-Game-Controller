#
# Configuration Functions for VISCA Joystick
#
import gc
import PySimpleGUI as Sg

g_Debug = False

g_Progname = "VISCA Game Controller"
g_ProgVers = "1.0beta7"

g_num_cams = 8
cam_ips = ['127.0.0.1']*g_num_cams
cam_ports = [52381]*g_num_cams

# Phil Rose: user-friendly camera names for display consistency.
cam_names = [f'Camera {x+1}' for x in range(g_num_cams)]

g_visca_relay_port = 10000  # currently hardwired

# ------------------------------------------------------------------
# Phil Rose (2026-06-24)
# Tune Xbox joystick sensitivity for smoother PTZ control.
# Original values retained below for easy rollback.
# ------------------------------------------------------------------

# sensitivity_tables = {
#     'pan': {'joy': [0, 0.15, 0.2, 0.3, 0.5, 0.8, 0.9, 1], 'cam': [0, 0, 1, 2, 6, 8, 12, 18]},
#     'tilt': {'joy': [0, 0.15, 0.2, 0.3, 0.5, 0.8, 0.9, 1], 'cam': [0, 0, 1, 3, 6, 8, 12, 18]},
#     'zoom': {'joy': [0, 0.15, 0.2, 0.3, 0.4, 0.5, 0.7, 1], 'cam': [0, 0, 1, 1, 1, 3, 5, 7]},
#     'focus': {'joy': [0, 0.2, 0.3, 0.7, 1], 'cam': [0, 0, 2, 5, 7]},
# }

# ------------------------------------------------------------------
# Phil Rose (2026-06-24)
# User-configurable PTZ response speed lists.
# These are the editable camera speed values only; the leading zero
# values and joystick breakpoints are handled in code.
# ------------------------------------------------------------------
g_pan_speeds = "1,1,3,5,7,9"
g_tilt_speeds = "1,1,3,5,7,9"
g_zoom_speeds = "1,1,1,3,5,7"
g_focus_speeds = "2,5,7"

sensitivity_tables = {
    'pan': {'joy': [0, 0.15, 0.2, 0.3, 0.5, 0.8, 0.9, 1], 'cam': [0, 0, 1, 2, 6,  8, 12, 18]},
    'tilt': {'joy': [0, 0.15, 0.2, 0.3, 0.5, 0.8, 0.9, 1], 'cam': [0, 0, 1, 3, 6, 8, 12, 18]},
    'zoom': {'joy': [0, 0.15, 0.2, 0.3, 0.4, 0.5, 0.7, 1], 'cam': [0, 0, 1, 1, 1, 3, 5, 7]},
    'focus': {'joy': [0, 0.2, 0.3, 0.7, 1], 'cam':[0, 0, 2, 5, 7]},
}

g_long_press_time = 0
g_invert_tilt = False
g_swap_pan = False
g_dead_zone = 0.0

# Bitfocus companion interface
# the trigger commands are assumed to all be on one page
g_companion_page = 0
g_companion_host = "127.0.0.1"

# ------------------------------------------------------------------
# Phil Rose (2026-06-24)
# Parse, validate, and apply comma-separated speed response lists.
# ------------------------------------------------------------------
def parse_speed_list(text, expected_count, max_value, label):
    try:
        values = [int(x.strip()) for x in text.split(',')]
    except ValueError:
        raise ValueError(f"{label} must contain only comma-separated whole numbers.")

    if len(values) != expected_count:
        raise ValueError(
            f"{label} must contain exactly {expected_count} comma-separated values.\n"
            f"Example: {'1,1,3,5,7,9' if expected_count == 6 else '2,5,7'}"
        )

    for value in values:
        if value < 0 or value > max_value:
            raise ValueError(f"{label} values must be between 0 and {max_value}.")

    return values


# ------------------------------------------------------------------
# Phil Rose (2026-06-24)
#
# The user edits only the camera speed values.
# The joystick breakpoints and leading zero values remain fixed.
#
# Example:
#   User enters: 1,1,3,5,7,9
#
# Resulting table:
#   [0, 0, 1, 1, 3, 5, 7, 9]
# ------------------------------------------------------------------

def rebuild_sensitivity_tables():
    global sensitivity_tables

    pan = parse_speed_list(g_pan_speeds, 6, 24, "Pan Speeds")
    tilt = parse_speed_list(g_tilt_speeds, 6, 24, "Tilt Speeds")
    zoom = parse_speed_list(g_zoom_speeds, 6, 7, "Zoom Speeds")
    focus = parse_speed_list(g_focus_speeds, 3, 7, "Focus Speeds")

    sensitivity_tables = {
        'pan':   {'joy': [0, 0.15, 0.2, 0.3, 0.5, 0.8, 0.9, 1], 'cam': [0, 0] + pan},
        'tilt':  {'joy': [0, 0.15, 0.2, 0.3, 0.5, 0.8, 0.9, 1], 'cam': [0, 0] + tilt},
        'zoom':  {'joy': [0, 0.15, 0.2, 0.3, 0.4, 0.5, 0.7, 1], 'cam': [0, 0] + zoom},
        'focus': {'joy': [0, 0.2, 0.3, 0.7, 1], 'cam': [0, 0] + focus},
    }


def configure():
    """ Configuration dialog """
    global g_long_press_time, g_Debug, g_companion_page, g_companion_host, g_swap_pan, g_invert_tilt
    global g_dead_zone
# ------------------------------------------------------------------
# Phil Rose (2026-06-24)
#
# Added globals to support changes
# ------------------------------------------------------------------
    global g_swap_pan, g_invert_tilt
    global g_pan_speeds, g_tilt_speeds, g_zoom_speeds, g_focus_speeds


# ------------------------------------------------------------------
# Phil Rose (2026-06-24)
# Reorganized Configure dialog into logical sections and added:
# - Camera names
# - Configurable PTZ response curves
# - Companion integration help
# ------------------------------------------------------------------

    layout = [
        [Sg.Text('Cameras', font=('Any', 10, 'bold'))],
        [Sg.Text("Name", size=(15, 1)),
        Sg.Text("IP Address", size=(20, 1)),
        Sg.Text("Port", size=(8, 1))],

        [Sg.Input(default_text=cam_names[0], key='NAME1', size=15),
        Sg.Input(default_text=cam_ips[0], key='CAM1', size=20),
        Sg.Input(default_text=str(cam_ports[0]), key='PORT1', size=8)],

        [Sg.Input(default_text=cam_names[1], key='NAME2', size=15),
        Sg.Input(default_text=cam_ips[1], key='CAM2', size=20),
        Sg.Input(default_text=str(cam_ports[1]), key='PORT2', size=8)],

        [Sg.Input(default_text=cam_names[2], key='NAME3', size=15),
        Sg.Input(default_text=cam_ips[2], key='CAM3', size=20),
        Sg.Input(default_text=str(cam_ports[2]), key='PORT3', size=8)],

        [Sg.Input(default_text=cam_names[3], key='NAME4', size=15),
        Sg.Input(default_text=cam_ips[3], key='CAM4', size=20),
        Sg.Input(default_text=str(cam_ports[3]), key='PORT4', size=8)],

        [Sg.Input(default_text=cam_names[4], key='NAME5', size=15),
        Sg.Input(default_text=cam_ips[4], key='CAM5', size=20),
        Sg.Input(default_text=str(cam_ports[4]), key='PORT5', size=8)],

        [Sg.Input(default_text=cam_names[5], key='NAME6', size=15),
        Sg.Input(default_text=cam_ips[5], key='CAM6', size=20),
        Sg.Input(default_text=str(cam_ports[5]), key='PORT6', size=8)],

        [Sg.Input(default_text=cam_names[6], key='NAME7', size=15),
        Sg.Input(default_text=cam_ips[6], key='CAM7', size=20),
        Sg.Input(default_text=str(cam_ports[6]), key='PORT7', size=8)],

        [Sg.Input(default_text=cam_names[7], key='NAME8', size=15),
        Sg.Input(default_text=cam_ips[7], key='CAM8', size=20),
        Sg.Input(default_text=str(cam_ports[7]), key='PORT8', size=8)],

        [Sg.HorizontalSeparator()],
        [Sg.Text('Controller', font=('Any', 10, 'bold'))],
        [Sg.Text('(Changes take effect after restart)', font=('Any', 10, 'italic'))],
        [Sg.Text('Long Press'),
        Sg.Input(default_text=str(g_long_press_time), key='-LONG-PRESS-', size=4),
        Sg.Text('seconds')],

        [Sg.Text('Joystick dead zone'),
        Sg.Input(default_text=str(g_dead_zone or ''), key='-DEAD-ZONE-', size=4)],

        [Sg.Checkbox('Invert Tilt', default=g_invert_tilt, key='-INVERT-TILT-'),
        Sg.Checkbox('Swap Pan', default=g_swap_pan, key='-SWAP-PAN-'),
        Sg.Checkbox('Debug Mode', default=g_Debug, key='-DEBUG-')],

        # ------------------------------------------------------------------
        # Phil Rose (2026-06-24)
        # User-configurable response curves.
        # ------------------------------------------------------------------
        [Sg.HorizontalSeparator()],
        [Sg.Text('Speed Profiles', font=('Any', 10, 'bold'))],
        [Sg.Text('Comma-separated values. Higher numbers = faster movement.')],
         
        [Sg.Text('Pan Speeds', size=18),
        Sg.Input(default_text=g_pan_speeds, key='-PAN-SPEEDS-', size=20),
        Sg.Text('e.g. 1,1,3,5,7,9')],

        [Sg.Text('Tilt Speeds', size=18),
        Sg.Input(default_text=g_tilt_speeds, key='-TILT-SPEEDS-', size=20),
        Sg.Text('e.g. 1,1,3,5,7,9')],

        [Sg.Text('Zoom Speeds', size=18),
        Sg.Input(default_text=g_zoom_speeds, key='-ZOOM-SPEEDS-', size=20),
        Sg.Text('e.g. 1,1,1,3,5,7')],

        [Sg.Text('Focus Speeds', size=18),
        Sg.Input(default_text=g_focus_speeds, key='-FOCUS-SPEEDS-', size=20),
        Sg.Text('e.g. 2,5,7')],

        [Sg.HorizontalSeparator()],
        [Sg.Text('Companion', font=('Any', 10, 'bold'))],
        [Sg.Text('Bitfocus Companion Page '),
        Sg.Input(default_text=str(g_companion_page), key='-COMPANION-PAGE-', size=4),
        Sg.Text('Bitfocus Companion Host '),
        Sg.Input(default_text=g_companion_host, key='-COMPANION-HOST-', size=15)],

        [Sg.HorizontalSeparator()],
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
            
            # ------------------------------------------------------------------
            # Phil Rose (2026-06-24)
            # Save user-configured camera names.
            # ------------------------------------------------------------------

            for x in range(g_num_cams):
                cam_names[x] = values['NAME' + str(x+1)] or f'Camera {x+1}'
                cam_ips[x] = values['CAM' + str(x+1)]
                cam_ports[x] = int(values['PORT' + str(x+1)])

                Sg.user_settings_set_entry('-NAME' + str(x+1) + '-', cam_names[x])
                Sg.user_settings_set_entry('-CAM' + str(x+1) + '-', cam_ips[x])
                Sg.user_settings_set_entry('-PORT' + str(x+1) + '-', cam_ports[x])
            # ------------------------

            try:
                g_long_press_time = float(values['-LONG-PRESS-'])
            except ValueError:
                g_long_press_time = 0.5
            g_Debug = values['-DEBUG-']
            g_invert_tilt = values['-INVERT-TILT-']
            g_swap_pan = values['-SWAP-PAN-']
            try:
                g_dead_zone = float(values['-DEAD-ZONE-'])
            except ValueError:
                g_dead_zone = 0.0

            
            # ------------------------------------------------------------------
            # Phil Rose (2026-06-24)
            # Validate, save, and apply user-configurable response curves.
            # ------------------------------------------------------------------
            try:
                parse_speed_list(values['-PAN-SPEEDS-'], 6, 24, "Pan Speeds")
                parse_speed_list(values['-TILT-SPEEDS-'], 6, 24, "Tilt Speeds")
                parse_speed_list(values['-ZOOM-SPEEDS-'], 6, 7, "Zoom Speeds")
                parse_speed_list(values['-FOCUS-SPEEDS-'], 3, 7, "Focus Speeds")
            except ValueError as exc:
                Sg.popup(str(exc), title="Invalid Speed Settings", keep_on_top=True)
                continue

            g_pan_speeds = values['-PAN-SPEEDS-']
            g_tilt_speeds = values['-TILT-SPEEDS-']
            g_zoom_speeds = values['-ZOOM-SPEEDS-']
            g_focus_speeds = values['-FOCUS-SPEEDS-']

            Sg.user_settings_set_entry('-pan_speeds-', g_pan_speeds)
            Sg.user_settings_set_entry('-tilt_speeds-', g_tilt_speeds)
            Sg.user_settings_set_entry('-zoom_speeds-', g_zoom_speeds)
            Sg.user_settings_set_entry('-focus_speeds-', g_focus_speeds)

            rebuild_sensitivity_tables()
             # ------------------------------------------------------------------
           
            g_companion_page = int(values['-COMPANION-PAGE-'])
            g_companion_host = values['-COMPANION-HOST-']
            Sg.user_settings_set_entry('-long_press_time-', g_long_press_time)
            Sg.user_settings_set_entry('-companion_page-', g_companion_page)
            Sg.user_settings_set_entry('-companion_host-', g_companion_host)
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
    global g_long_press_time, g_invert_tilt, g_swap_pan, g_companion_page
    global g_companion_host, g_Debug, g_dead_zone
# Phil Rose (2026-06024 added globals)
    global g_pan_speeds, g_tilt_speeds, g_zoom_speeds, g_focus_speeds

    # ------------------------------------------------------------------
    # Phil Rose (2026-06-24)
    # Load user-configured camera names.
    # ------------------------------------------------------------------

    for x in range(g_num_cams):
        cam_names[x] = Sg.user_settings_get_entry('-NAME' + str(x+1) + '-', f'Camera {x+1}')
        cam_ips[x] = Sg.user_settings_get_entry('-CAM' + str(x+1) + '-', '')
        port = Sg.user_settings_get_entry('-PORT' + str(x+1) + '-', 52381)
        cam_ports[x] = port

    g_companion_page = Sg.user_settings_get_entry('-companion_page-', 99)
    g_companion_host = Sg.user_settings_get_entry('-companion_host-', '127.0.0.1')
    g_long_press_time = Sg.user_settings_get_entry('-long_press_time-', .5)
    g_invert_tilt = Sg.user_settings_get_entry('-invert-tilt-', False)
    g_swap_pan = Sg.user_settings_get_entry('-swap-pan-', False)
    g_Debug = Sg.user_settings_get_entry('-debug-', False)
    g_dead_zone = Sg.user_settings_get_entry('-dead-zone-', None)
    
    # ------------------------------------------------------------------
    # Phil Rose (2026-06-24)
    # Load saved user-configurable response curves.
    # ------------------------------------------------------------------
    g_pan_speeds = Sg.user_settings_get_entry('-pan_speeds-', g_pan_speeds)
    g_tilt_speeds = Sg.user_settings_get_entry('-tilt_speeds-', g_tilt_speeds)
    g_zoom_speeds = Sg.user_settings_get_entry('-zoom_speeds-', g_zoom_speeds)
    g_focus_speeds = Sg.user_settings_get_entry('-focus_speeds-', g_focus_speeds)

    
    rebuild_sensitivity_tables()

    if not Sg.user_settings_get_entry('-configured-', False):
        configure()

credits_text = """
Dan Tappan (https://dantappan.net) - (c) 2024, 2025, 2026

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
    global g_dead_zone, g_Debug, g_Progname, g_ProgVers, g_invert_tilt, g_swap_pan, g_num_cams
    global g_long_press_time, g_visca_relay_port

    def __init__(self):
        self.mappings = None
        # True == 'use buttons for brightness', False == 'use a joystick for brightness'
        self._brightness_button = True
        load_config()

    def set_cam_name(self, idx,  name):
        try:
            # should we save this in the config?
            # for now, make it temporary change and let config override
            cam_names[idx-1] = name
        except IndexError:
            pass    # do nothing

    @staticmethod
    def companion(row:int, column:int):
        return [g_companion_page, row, column, g_companion_host]

    @staticmethod
    def companion_host():
        return g_companion_host

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

    
    # ------------------------------------------------------------------
    # Phil Rose (2026-06-24)
    # Return the configured display name for a camera.
    # ------------------------------------------------------------------
    @staticmethod
    def cam_name(idx):
        try:
            return cam_names[idx-1]
        except IndexError:
            return f"Camera {idx}"
    # ------------------------------------------------------------------

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
    def visca_relay_port(self):
        return g_visca_relay_port

    @property
    def credits_text(self):
        return f"{g_Progname} {g_ProgVers}\n"+credits_text

    @property
    def brightness_button(self):
        return self._brightness_button
