
# TODO: re-enable typing inspection and figure out how to get rid of all the "X|None" complaints

import platform
import threading
from typing import Optional
from enum import IntEnum

from visca_exceptions import ViscaException
from file_paths import controller_icon, search_path
import PySimpleGUI as Sg
from camera import Camera
from osc import OSCTask

# from exceptions import ViscaException
# Use pygame-ce
import pygame
from numpy import interp
from config import Config
from companion import Companion
from controller import ControllerList,  ControllerAxis, ControllerButton
from viscarelay import ViscaRelay
from win_print import win_print, win_print_init

Windows = platform.system() == 'Windows'

UsePsgTray = True
if Windows and UsePsgTray:
    from psgtray import SystemTray

# from visca_over_ip import Camera
# from visca_over_ip.exceptions import ViscaException

cam: Optional[Camera] = None
current_cam = "Unknown"
current_cam_num = 0

# ------------------------------------------------------------------
# Phil Rose (2026-06-24)
# Tracks whether the Xbox/gamepad should currently control PTZ.
# /setcam enables this; /clearcam disables it for non-camera sources.
# ------------------------------------------------------------------
gamepad_enabled = True

main_window:Optional[Sg.Window] = None
config: Config = Config()
bitfocus: Companion = Companion()
visca_relay: ViscaRelay = ViscaRelay(rcv_port=config.visca_relay_port)
controller_list: Optional[ControllerList]  = None

pygame_thread_lock: threading.Lock = threading.Lock()

def pygame_lock(f):
    """ Acquire exclusive access to the pygame code. This prevents race conditions
        between the pygame event thread and the main thread accessing, e.g., the joystick
        data structures """
    with pygame_thread_lock:
        f()

def handle_brightness_up(button: ControllerButton):
    handle_brightness(button, True)

def handle_brightness_down(button: ControllerButton):
    handle_brightness(button, False)

def handle_brightness(button: ControllerButton, up):
    """ Change the camera exposure
        increment or decrement the brightness by one step for each push
    """
    global cam

    if cam is None or button is None:
        return

    if not button.is_down:
        # only act on button push
        return

    try:
        #
        # change brightness only works when in auto exposure mode?
        #
        cam.autoexposure_mode('auto')
        if up:
            cam.increase_exposure_compensation()
            win_print("increase brightness")
        else:
            cam.decrease_exposure_compensation()
            win_print("decrease brightness")

    except ViscaException:
        win_print("brightness change failed")

def connect_to_camera(cam_num) -> Optional[Camera]:
    """Connects to the camera specified by cam_index and returns it"""
    global cam, current_cam, current_cam_num, main_window

    win = main_window

    if cam is not None:
        try:
            cam.zoom(0)
            cam.pantilt(0, 0)
        except ViscaException:
            # Probably indicates an issue with the VISCA connection
            win_print(f'Camera {current_cam} reset pan/tilt/zoom failed')
            pass

        cam.close_connection()

        cam = None

    newcam = None
    cam_ip, cam_port = config.cam_address(cam_num - 1)
    if cam_ip is not None:
        try:
            newcam = Camera(cam_ip, cam_port)
        except Exception as exc:
            win_print(f'Camera {cam_num} not available: {exc}')
            pass

    cam = newcam
    if newcam is None:
        cam_name = "Camera Unknown"
    else:
        # ------------------------------------------------------------------
        # Phil Mod (2026-06-21)
        # Display configured camera names instead of numeric identifiers.
        # ------------------------------------------------------------------
        cam_name = config.cam_name(cam_num)

        # Bitfocus Companion (row 0, camera_number), should be configured to set Preview
        # to the selected camera
        bitfocus.pushbutton(* config.companion(0, cam_num))

        # Switch the VISCA relay to the new camera
        # noinspection PyTypeChecker
        visca_relay.ptz_set(ptz=cam_ip, ptz_port=cam_port)

    win_print(f'{cam_name}')
    current_cam = cam_name
    current_cam_num = cam_num

    if UsePsgTray:
        tray = win.metadata
        if tray is not None:
            tray.set_tooltip(f"{config.progname}: Camera {cam_name}")
    
    return cam

def handle_select_cam(button: Optional[ControllerButton] = None):
    """
    Handle a button push to select a camera
    activates on button uup. Long press selects 2nd bank of cameras
    """
    # Phil Rose - added gamepad_enabled
    global cam, gamepad_enabled

    gamepad_enabled = True

    if button is None or button.is_down:
        return

    cam_num = button.value
    if button.long_press:
        cam_num += 4
    if cam_num < 1 or cam_num > config.num_cams:
        win_print(f"Bad camera number {cam_num}")
    else:
        cam = connect_to_camera(cam_num)

def osc_select_cam(cam_num):
    """
    Handle a select camera event via OSC
    """
    global cam, current_cam_num

    if cam_num == current_cam_num:
        return # filter duplicate selects

    if cam_num < 1 or cam_num > config.num_cams:
        win_print(f"OSC set camera: bad camera number {cam_num}")
    else:
        cam = connect_to_camera(cam_num)

def handle_tbar(axis: ControllerAxis):
    """ Handle a change to a t-bar axis.
        a T-BAR is a special sort of axis in that the range is 0 - 100 and reaching the extreme causes
        the preview to finish transition to program and inverts the sense of
        the axis
        Relay the change to a custom variable
        """
    if axis is None:
        return

    pos = axis.get_position()
    # convert -1 to 1 to 0 - 1 and reduce precision to 2 decimal places
    pos = int(round((pos + 1) / 2, 2) * 100)

    if pos == 100:
        axis.invert *= -1  # flip axis
    bitfocus.t_bar(pos, config.companion_host())

def handle_prev2prog(button: Optional[ControllerButton]=None):
    """"
    Handle a push on the button to switch Preview and Program windows
    """
    if button is None or not button.is_down:
        return
    # Bitfocus companion row 1, column 1 should be configured to fade Preview to Program
    win_print("Preview to Program")
    bitfocus.pushbutton(*config.companion(1, 1))


def handle_preset(button: ControllerButton):
    """
    Handle push on one of the presets
    button.value == preset number
    Activates on button release, distinguishes between short  press(call preset)
    and long press (save preset)
    """
    global cam
    if cam is None or button is None:
        return
    #
    # Activate on button up
    #
    if button.is_down:
        return

    #
    # Long press = set preset
    # Short press = recall preset
    preset_num = button.value
    try:
        if button.long_press:
            win_print(f"Setting preset {preset_num}")
            cam.save_preset(preset_num-1)
        else:
            win_print(f"Preset {preset_num}")
            cam.recall_preset(preset_num-1)
    except ViscaException:
        win_print("Preset failed")


def joy_pos_to_cam_speed(axis_position: float, table_name: str, invert=True) -> int:
    """Converts from a joystick axis position to a camera speed using the given mapping

    :param axis_position: the raw value of an axis of the joystick -1 to 1
    :param table_name: one of the keys in sensitivity_tables
    :param invert: if True, the sign of the output will be flipped
    :return: an integer which can be fed to a Camera driver method
    """
    sign = 1 if axis_position >= 0 else -1
    if invert:
        sign *= -1

    table = config.sensitivity(table_name)

    # noinspection PyTypeChecker
    val =sign * round(
        interp(abs(axis_position), table['joy'], table['cam'])
    )
    if config.debug:
        win_print(f"joystick: {axis_position} -> {val}")
    return val

def handle_focus_near(axis: ControllerAxis):
    handle_focus(axis, False)

def handle_focus_far(axis: ControllerAxis):
    handle_focus(axis, True)

def handle_focus(axis: ControllerAxis, far):
    """ Handle a movement of a focus controlling joystick
        Either select autofocus, or start/stop the focus movement
    """
    global cam

    if cam is None or axis is None:
        return

    #
    # select manual focus and start camera movement
    cam.set_focus_mode('manual')
    focus_pos = axis.get_position()
    # convert -1:1 to 0:1
    focus_pos = (focus_pos + 1) / 2
    focus_speed = joy_pos_to_cam_speed(focus_pos, 'focus', far)
    if axis.moving or focus_speed != 0:
        if focus_speed == 0:
            # Stop camera fovus movement
            cam.manual_focus(0)
            win_print("Manual focus: stop")
        else:
            # start or change focus speed
            if far:
                msg = "Manual focus far: start"
            else:
                msg = "Manual focus near: start"
            cam.manual_focus(focus_speed)
            if not axis.moving:
                win_print(msg)

    axis.set_moving(focus_speed != 0)

def handle_autofocus(button: ControllerButton):
    """
    Handle a push o9n the autofocus button
    """
    global cam

    if cam is None or button is None:
        return

    if not button.is_down:
        return

    cam.set_focus_mode('auto')
    win_print("AutoFocus mode")

# Phil Rose (2026-06-24)
# Companion OSC command to explicitly disable PTZ control.
def osc_clear_cam():
    """
    Handle the Companion /clearcam OSC command.

    Disables gamepad PTZ control until another camera is selected
    with /setcam.
    """
    global gamepad_enabled, current_cam

    gamepad_enabled = False
    current_cam = "No Active Camera"

    win_print(current_cam)

    if UsePsgTray:
        tray = main_window.metadata
        if tray is not None:
            tray.set_tooltip(f"{config.progname}: {current_cam}")

class FocusEnum(IntEnum):
    NEAR=0
    FAR=1
    AUTO=2
# each button correspondence to a focus direction and a virtual axis position
focus_map = {
    8: (FocusEnum.FAR, .3),
    1: (FocusEnum.FAR, .5),
    2: (FocusEnum.FAR, .8),
    3: (FocusEnum.AUTO, 0),
    7: (FocusEnum.AUTO, 0),
    6: (FocusEnum.NEAR, .3),
    5: (FocusEnum.NEAR, .5),
    4: (FocusEnum.NEAR, .8)
}
def handle_focus_hat(button: ControllerButton):
    """
    For devices that use a HAT to control the focus. Translate the current hat position (1-8) into
    either a manual focus command or autofocus. Upward positions (8, 1, 2) map to  "focus far",
    downward (4, 5, 6) to"focus near", side to side (3, 7) to autofocus
    """
    global cam

    if cam is None or button is None:
        return

    focus_command, focus_pos = focus_map[button.value]
    if not button.is_down:
        focus_pos = 0

    # note that the position value for autofocus mode is 0,
    # so we can fall through  and stop any ongoing manual
    # focus movement before executing the autofocus command
    far = focus_command == FocusEnum.FAR
    focus_speed = joy_pos_to_cam_speed(focus_pos, 'focus', far)
    if button.moving or focus_speed != 0:
        cam.set_focus_mode('manual')
        if focus_speed == 0:
            # Stop camera focus movement
            cam.manual_focus(0)
            win_print("Manual focus: stop")
            button.moving = False
        else:
            # start or change focus speed
            if far:
                msg = "Manual focus far: start"
            else:
                msg = "Manual focus near: start"
            cam.manual_focus(focus_speed)
            if not button.moving:
                win_print(msg)
                button.moving = True

    if focus_command == FocusEnum.AUTO:
        handle_autofocus(button)

def handle_white_balance(button:ControllerButton):
    global cam

    if cam is None or button is None:
        return

    if button.is_down:
        # Activate on release
        return
    #
    # Short press == ONE PUSH white balance
    # Long press == Auto
    if button.long_press:
        win_print("Auto white balance")
        cam.white_balance_mode('auto')
    else:
        win_print("One Push white balance")
        cam.white_balance_mode('one push')
        cam.white_balance_mode('one push trigger')


def handle_pantilt(axis: Optional[ControllerAxis]=None):
    """
    Handle motion of one of the pan/tilt axes.
    We need to set both at once, so we don't care which one moved
    """
    # Phil Rose added gamepad_enabled
    global cam, gamepad_enabled

    if not gamepad_enabled:
        return

    if cam is None or axis is None:
        return

    pan_axis = axis.controller.pan_axis
    tilt_axis = axis.controller.tilt_axis

    pan_speed = joy_pos_to_cam_speed(pan_axis.get_position(),
                                 'pan', config.swap_pan)
    tilt_speed = joy_pos_to_cam_speed(tilt_axis.get_position(),
                                  'tilt', config.invert_tilt)
    #
    # It is possible (depending on controller?) to get a string of axis events after the
    # joystick has returned to 0. Filter these out to avoid excess 'stop' commands
    # We cache the motion state in the pan_axis
    if pan_axis.moving or (pan_speed != 0) or (tilt_speed != 0):
        cam.pantilt(pan_speed=pan_speed, tilt_speed=tilt_speed)
    pan_axis.set_moving((pan_speed != 0) or (tilt_speed != 0))


def handle_zoom(axis:ControllerAxis):
    """
    Handle motion of the zoom axis
    """
    # Phil rose added gamepad_enabled
    global cam, gamepad_enabled

    if not gamepad_enabled:
        return

    if cam is None or axis is None:
        return

    zoom = joy_pos_to_cam_speed(axis.get_position(), 'zoom')
    if axis.moving or (zoom != 0):
            cam.zoom(zoom)
    axis.set_moving(zoom != 0)

def handle_pygame_event(ev:pygame.event.Event):
    """
    Handle a single pygame event. This is called as a closure via pygame_lock(), to make
    sure that the serialization lock is properly released
    """
    if ev.type == pygame.JOYDEVICEADDED:
        controller_list.add(ev.device_index)
    elif ev.type == pygame.JOYDEVICEREMOVED:
        controller = controller_list.lookup(ev.instance_id)
        if controller is not None:
            joystick = controller.get_pygame_joystick()
            if joystick is not None:
                win_print(f'{joystick.get_name()} removed')
            controller_list.remove(ev.instance_id)
    else:
        try:
            controller = controller_list.lookup(ev.instance_id)
        except AttributeError:
            controller = None
        if controller is not None:
            controller.pygame_event(ev)

# Excessive unnecessary consecutive AXIS events, while the joystick is still moving,
# slow things down.
# Set this to True to cause a flush of pending AXIS events.
pygame_flush_axis = False
def flush_axis_events():
    """ Callback function to trigger axis event flush"""
    global pygame_flush_axis
    pygame_flush_axis = True

#
# Mapping of controller functions to program functions
#
controller_callbacks = {
    "select_cam" : handle_select_cam,
    "focus" : handle_focus_hat,
    "focus_far":handle_focus_far,
    "focus_near":handle_focus_near,
    "brightness_up":handle_brightness_up,
    "brightness_down":handle_brightness_down,
    "white_balance":handle_white_balance,
    "pantilt":handle_pantilt,
    "zoom":handle_zoom,
    "autofocus":handle_autofocus,
    "prev2prog":handle_prev2prog,
    "preset":handle_preset,
    "tbar":handle_tbar,
    "flushaxis":flush_axis_events
}

def main_loop():
    """
    Main program loop
    return to exit program
    """
    global main_window, controller_list

    controller_list = ControllerList(callbacks=controller_callbacks,
                                     long_press=config.long_press_time,
                                     dead_zone=config.dead_zone)

    win = main_window
    tray = win.metadata

    while True:
        event, values = win.read()

        if tray and event == tray.key:
            # use the System Tray's event as if was from the window
            try:
                event = values[event]
            except IndexError:
                event = values[0]

        if event == '-PRINT-':
            # noinspection PyTypeChecker
            Sg.cprint(values[event], window=win, key="OUTPUT", c=('black', 'white'))

        elif event in ('Show Window', 'Center Window', Sg.EVENT_SYSTEM_TRAY_ICON_ACTIVATED,
                     Sg.EVENT_SYSTEM_TRAY_ICON_DOUBLE_CLICKED):
            win.hide()  # in case it was minimized, not hidden
            if event == 'Center Window':
                # emergency feature, in case window is moved off-screen, or saved location puts it off-screen
                win.move_to_center()
            if win.is_hidden:
                win.un_hide()
            win.bring_to_front()

        elif event in ('Minimize', Sg.WIN_CLOSE_ATTEMPTED_EVENT):
            if tray:
                win.hide()
                tray.show_icon()  # if hiding window, better make sure the icon is visible
            elif event == 'Minimize':
                win.minimize()
            else:
                return False

        elif event == 'Help':
            # Display help for each controller
            # noinspection PyTypeChecker
            for instance_id in controller_list:
                controller = controller_list.lookup(instance_id)
                if controller is not None:
                    joystick = controller.get_pygame_joystick()
                    if joystick is not None:
                        joystick_name = joystick.get_name()
                        Sg.popup(f"{config.progname}({config.progvers})\n{joystick_name}{controller.help_text}",
                             title="Help", keep_on_top=True, line_width=70,
                             image=search_path(controller.help_image))

# Phil Rose (2026-06-24)
# Companion OSC integration help for camera-name selection and /clearcam support.
        elif event == 'Companion Help':
            Sg.popup_scrolled(
                f"""{config.progname} ({config.progvers})

Companion / OSC Integration

The application listens for OSC messages on UDP port 9999 on 127.0.0.1

Select a camera with the Generic: OSC Connection
----------------
OSC Path:
/setcam

Value:
Either a camera name or a configured camera number.

Examples:
/setcam Front
/setcam Left
/setcam Over
/setcam Tail

or

/setcam 1
/setcam 2

Selecting a camera automatically enables gamepad PTZ control.

Disable PTZ control
-------------------
OSC Path:
/clearcam

No value is required.

Example:
/clearcam

Use /clearcam when switching to a non-camera
source such as PowerPoint, video playback,
or screen sharing.

This disables gamepad PTZ movement until
another /setcam command is received.

Tip:
Using configured camera names (e.g. Front, Left, Over, Tail)
is recommended instead of camera numbers, since names remain
consistent even if camera assignments change.
-------------------
OSC Path:
/setcamname

Values:
- A camera number (string)
- The name to associate with a camera

Example:
/setcamname 1 "House L"

Tip:
This command allows the camera names to be reflected, by Companion, from a BlackMagic
ATEM or other switching device that supports configurable display names. 
Hint:
If using the Companion Action "osc: Send message with multiple arguments" make sure to
enclose the camera name string in double quotes (as above), in case it contains spaces
""",
            title="Companion Help",
            keep_on_top=True,
            size=(80, 25)
        )
        
        elif event == 'Credits':
            Sg.popup(config.credits_text, title="Credits", keep_on_top=True, line_width=80)

        elif event == 'Configure':
            config.configure()

        elif event == Sg.WINDOW_CLOSED or event == 'Exit':
            Sg.user_settings_set_entry('-location-', win.current_location())
            Sg.user_settings_set_entry('-hidden-', win.is_hidden())
            return False

        elif event == 'PYGAME_EVENT':
            # Handle Pygame events
            # For reasons I don't yet understand, sometimes values is a hash table, and
            # sometimes it's just an array
            try:
                ev = values[event]
            except IndexError:
                ev = values[0]

            pygame_lock(lambda: handle_pygame_event(ev))

# Companion /clearcam support
        elif event == "OSC_CLEAR_CAMERA":
            pygame_lock(lambda: osc_clear_cam())

        elif event == "OSC_SET_CAMERA":
            pygame_lock(lambda: osc_select_cam(values['OSC_SET_CAMERA']))

        elif event == "OSC_SET_CAMERA_NAME":
            config.set_cam_name(*values['OSC_SET_CAMERA_NAME'])

pygame_task_exit = False
pygame_thread: Optional[threading.Thread] = None

def pygame_task(win):
    """
    Retrieve and pass on pygame events
    NOTE: it is VERY important to only call into the pygame module from
    this task. Doing otherwise can cause PIL crashes and other unexpected
    behavior
    """
    global pygame_flush_axis, pygame_task_exit

#   pygame.init()
# To reduce startup time: call only the init() functions that we need
    pygame.display.init()
    pygame.joystick.init()
    if pygame.joystick.get_count() == 0:
        win_print("No Joystick")

    while not pygame_task_exit:
        if pygame_flush_axis:
            pygame.event.clear(pygame.JOYAXISMOTION)
            pygame_flush_axis = False

        try:
            ev = pygame.event.wait(100)

        except Exception as e:
            # sometime the wait() call "returns a result with exception set"
            # this seems to be a transient error, maybe related to initialization?
            win_print(f'unexpected exception {e}')
            continue

        pass_event = False
        if ev.type == pygame.NOEVENT:
            pass
        else:
            pass_event = True

        if pass_event:
            win.write_event_value('PYGAME_EVENT', ev)

    # exited loop, return to terminate task
    pygame.quit()

def pygame_task_start(win: Sg.Window):
    """
    Task to handle pygame events
    :param win: main window
    """
    global pygame_thread

    pygame_thread = threading.Thread(target=lambda: pygame_task(win))
    pygame_thread.daemon = True
    pygame_thread.start()

def pygame_task_end():
    """
    Terminate and wait for the pygame thread
    :return:
    """
    global pygame_thread, pygame_task_exit

    pygame_task_exit = True

def main():
    """
    Main program
    :return: None
    """
    global cam, main_window

    settings = Sg.UserSettings()
    window_location = settings.get('-location-')
    window_hidden = settings.get('-hidden-')

    if config.debug:
        # Bigger window when debugging
        output_size = (50, 25)
    else:
        output_size = (30, 5)

    output = Sg.Multiline(  reroute_cprint=True,
                            reroute_stderr=False,
                            reroute_stdout=False,
                            autoscroll=True,
                            auto_refresh=True,
                            write_only=True,
                            size=output_size,
                            key='OUTPUT')

    menu_def = [['Menu', ['Minimize', 'Configure', 'Help', 'Companion Help', 'Credits', 'Exit']]]
    layout = [[Sg.Menu(menu_def)], [output]]

    window = Sg.Window( title=config.progname, layout=layout,
                        no_titlebar=True, grab_anywhere=True, location=window_location,
                        enable_close_attempted_event=True,
                        alpha_channel=0.75, keep_on_top=True,
                        icon=controller_icon())

    if UsePsgTray:
        tooltip = f"Control the {config.progname} app"
        traymenu = ['', ['Show Window', 'Center Window', 'Exit']]
        tray = SystemTray(traymenu,  tooltip=tooltip, window=window,
                          icon=controller_icon())
        window.metadata = tray
    else:
        tray = None

    window.finalize()
    if window_hidden:
        window.hide()
    win_print_init(window)

    main_window = window

    win_print(f'{config.progname}({config.progvers})')

    cam = connect_to_camera(1)

    pygame_task_start(window)

    osc_task = OSCTask(window)

    while True:
        if config.debug:
            if not main_loop():
                break
        else:
            try:
                if not main_loop():
                    break
            except Exception as exc:
                win_print(exc)

#    window.timer_stop(timer_id)

    osc_task.shutdown()

    pygame_task_end()

    if not window.is_closed():
        window.close()

    if tray:
        tray.close()

    pass # spot for a breakpoint

if __name__ == "__main__":
    main()
    pass