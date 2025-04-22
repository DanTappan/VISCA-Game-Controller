
import platform
import threading
from typing import Optional

from exceptions import ViscaException
from icons import controller_icon
import PySimpleGUI as Sg
from camera import Camera
# from exceptions import ViscaException
import pygame
from numpy import interp
from config import Config
from companion import Companion
from controller import Controller, ControllerAxis, ControllerButton

Windows = platform.system() == 'Windows'

UsePsgTray = True
if Windows and UsePsgTray:
    from psgtray import SystemTray

# from visca_over_ip import Camera
# from visca_over_ip.exceptions import ViscaException

cam: Optional[Camera] = None
main_window:Optional[Sg.Window] = None
bitfocus: Companion = Companion()
config: Config = Config()
#
# For now assume only a single controller, though the module can handle
# multiple
controller: Controller = Controller(longpress_limit=config.long_press_time)

pygame_thread_lock: threading.Lock = threading.Lock()

def pygame_lock(f):
    """ Acquire exclusive access to the pygame code. This prevents race conditions
        between the pygame event thread and the main thread accessing, e.g., the joystick
        data structures """
    with pygame_thread_lock:
        f()

def joystick_init():
    """Initializes pygame and the joystick.
    """
    global controller

    joystick = controller.get_pygame_joystick()

    if joystick is not None:
        del joystick

    try:
        joystick = pygame.joystick.Joystick(0)

    except pygame.error:
        joystick = None

    controller.set_pygame_joystick(joystick)

    return joystick

def handle_brightness_up(button: ControllerButton):
    handle_brightness(button, True)

def handle_brightness_down(button: ControllerButton):
    handle_brightness(button, False)

def handle_brightness(button: ControllerButton, up):
    """ Change the camera exposure
        increment or decrement the brightness by one step for each push
    """
    global cam

    if button is None:
        return

    if cam is None:
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
            print("increase brightness")
        else:
            cam.decrease_exposure_compensation()
            print("decrease brightness")

    except ViscaException:
        print("brightness change failed")

def connect_to_camera(cam_num) -> Camera:
    """Connects to the camera specified by cam_index and returns it"""
    global cam, main_window

    win = main_window

    if cam is not None:
        cam.zoom(0)
        cam.pantilt(0, 0)
        cam.close_connection()
        cam = None

    newcam = None
    cam_ip, cam_port = config.cam_address(cam_num - 1)
    if cam_ip is not None:
        try:
            newcam = Camera(cam_ip, cam_port)
        except Exception as exc:
            print(f'Camera {cam_num} not available:', exc)
            pass

    cam = newcam
    if newcam is None:
        cam_name = "Unknown"
    else:
        cam_name = str(cam_num)
        # Bitfocus Companion (row 0, camera_number), should be configured to set Preview
        # to the selected camera
        bitfocus.pushbutton(* config.companion(0, cam_num))
    print(f"Camera {cam_name}")

    if UsePsgTray:
        tray = win.metadata
        if tray is not None:
            tray.set_tooltip(f"{config.progname}: Camera {cam_name}")
    
    return cam

def handle_select_cam(button: ControllerButton = None):
    """
    Handle a button push to select a camera
    activates on button uup. Long press selects 2nd bank of cameras
    """
    global cam, main_window

    if button is None or button.is_down:
        return

    cam_num = button.value
    if button.long_press:
        cam_num = cam_num + 4
    if cam_num < 1 or cam_num > config.num_cams:
        print(f"Bad camera number {cam_num}")
    else:
        cam = connect_to_camera(cam_num)

def handle_prev2prog(button: ControllerButton=None):
    """"
    Handle a push on the button to switch Preview and Program windows
    """
    if button is None or not button.is_down:
        return
    # Bitfocus companion row 1, column 1 should be configured to fade Preview to Program
    print("Preview to Program")
    bitfocus.pushbutton(*config.companion(1, 1))


def handle_preset(button: ControllerButton):
    """
    Handle push on one of the presets
    button.value == preset number
    Activates on button release, distinguishes between short  press(call preset)
    and long press (save preset)
    """
    global cam
    if cam is None:
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
            print(f"Setting preset {preset_num}")
            cam.save_preset(preset_num-1)
        else:
            print(f"Preset {preset_num}")
            cam.recall_preset(preset_num-1)
    except ViscaException:
        print("Preset failed")


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

    val =sign * round(
        interp(abs(axis_position), table['joy'], table['cam'])
    )
    if config.debug:
        print(f"joystick: {axis_position} -> {val}")
    return val

focusing = False
def handle_focus_near(axis: ControllerAxis):
    handle_focus(axis, False)

def handle_focus_far(axis: ControllerAxis):
    handle_focus(axis, True)

def handle_focus(axis: ControllerAxis, far):
    """ Handle a push/release on one of the focus related buttons
        Either select autofocus, or start/stop the focus movement
    """
    global cam, focusing

    if axis is None:
        return

    joystick = axis.controller.get_pygame_joystick()
    if joystick is None:
        return

    if cam is None:
        return

    #
    # select manual focus and start camera movement
    cam.set_focus_mode('manual')
    focus_pos = joystick.get_axis(axis.value)
    # convert -1:1 to 0:1
    focus_pos = (focus_pos + 1) / 2
    focus_speed = joy_pos_to_cam_speed(focus_pos, 'focus', far)
    if focusing or focus_speed != 0:
        if focus_speed == 0:
            # Stop camera fovus movement
            cam.manual_focus(0)
            print("Manual focus: stop")
        else:
            # start or change focus speed
            if far:
                msg = "Manual focus far: start"
            else:
                msg = "Manual focus near: start"
            cam.manual_focus(focus_speed)
            if not focusing:
                print(msg)

    focusing = focus_speed != 0

def handle_autofocus(button: ControllerButton):
    """
    Handle a push o9n the autofocus button
    """
    global cam

    if button is None or cam is None:
        return

    if not button.is_down:
        return

    cam.set_focus_mode('auto')
    print("AutoFocus mode")

def handle_white_balance(button:ControllerButton):
    global cam

    if not cam:
        return

    if button.is_down:
        # Activate on release
        return
    #
    # Short press == ONE PUSH white balance
    # Long press == Auto
    if button.long_press:
        print("Auto white balance")
        cam.white_balance_mode('auto')
    else:
        print("One Push white balance")
        cam.white_balance_mode('one push')
        cam.white_balance_mode('one push trigger')


moving = False
def handle_pantilt(axis: ControllerAxis=None):
    """
    Handle motion of one of the pan/tilt axes.
    We need to set both at once, so we don't care which one moved
    """
    global cam, moving

    if axis is None or cam is None:
        return

    joystick = axis.controller.get_pygame_joystick()
    if joystick is None:
        return

    pan_axis = axis.controller.pan_axis
    tilt_axis = axis.controller.tilt_axis

    pan_speed = joy_pos_to_cam_speed(joystick.get_axis(pan_axis.value),
                                 'pan', config.swap_pan)
    tilt_speed = joy_pos_to_cam_speed(joystick.get_axis(tilt_axis.value),
                                  'tilt', config.invert_tilt)
    #
    # It is possible (depending on controller?) to get a string of axis events after the
    # joystick has returned to 0. Filter these out to avoid excess 'stop' commands
    #
    if moving or (pan_speed != 0) or (tilt_speed != 0):
        cam.pantilt(pan_speed=pan_speed, tilt_speed=tilt_speed)
    moving = (pan_speed != 0) or (tilt_speed != 0)


zooming = False
def handle_zoom(axis:ControllerAxis):
    """
    Handle motion of the zoom axis
    """
    global cam, zooming

    if axis is None or cam is None:
        return

    joystick = axis.controller.get_pygame_joystick()
    if joystick is None:
        return

    zoom = joy_pos_to_cam_speed(joystick.get_axis(axis.value), 'zoom')
    if zooming or (zoom != 0):
            cam.zoom(zoom)
    zooming = zoom != 0

def handle_pygame_event(ev:pygame.event.Event):
    """
    Handle a single pygame event. This is called as a closure via pygame_lock(), to make
    sure that the serialization lock is properly released
    """
    global controller

    if ev.type == pygame.JOYDEVICEADDED or ev.type == pygame.JOYDEVICEREMOVED:
        joystick = controller.get_pygame_joystick()
        if joystick is not None:
            print(joystick.get_name())
        else:
            print("No joystick")
    else:
        controller.pygame_event(ev)


def main_loop():
    """
    Main program loop
    return to exit program
    """
    global main_window

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

        # Handle Tray events first
        if event in ('Show Window', 'Center Window', Sg.EVENT_SYSTEM_TRAY_ICON_ACTIVATED,
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
            Sg.popup(controller.help_text, title="Help", keep_on_top=True, line_width=80)

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


pygame_task_exit = False
pygame_thread: Optional[threading.Thread] = None

def pygame_task(win):
    """
    Retrieve and pass on pygame events
    """
    global controller

#   pygame.init()
# To reduce startup time: call only the init() functions that we need
    pygame.display.init()
    pygame.joystick.init()

    while not pygame_task_exit:
        # noinspection PyBroadException
        try:
            ev = pygame.event.wait(100)

        except:
            # sometime the wait() call "returns a result with exception set"
            # this seems to be a transient error, maybe related to initialization?
            # I haven't been able to figure out the exception type this returns
            continue

        pass_event = False
        if ev.type == pygame.NOEVENT:
            pass
        elif ev.type == pygame.JOYDEVICEREMOVED:
            pygame_lock(lambda: joystick_init())
            pass_event = True
        elif ev.type == pygame.JOYDEVICEADDED:
            joystick = controller.get_pygame_joystick()
            if joystick is None:
                pygame_lock(lambda: joystick_init())
                pass_event = True
        else:
            pass_event = True

        if pass_event:
            win.write_event_value('PYGAME_EVENT', ev)

#   pygame.display.quit()


def pygame_task_start(win: Sg.Window):
    """
    Task to handle pygame events
    :param win: main window
    """
    global pygame_thread

    pygame_thread = win.start_thread(lambda: pygame_task(win), None)


def pygame_task_end():
    """
    Terminate and wait for the pygame thread
    :return:
    """
    global pygame_thread, pygame_task_exit

    pygame_task_exit = True
    if pygame_thread is not None:
        pygame_thread.join()
    pygame_thread = None


def main():
    """
    Main program
    :return: None
    """
    global cam, controller, main_window

    controller.set_callbacks(select_cam=handle_select_cam,
                             focusfar=handle_focus_far,
                             focusnear=handle_focus_near,
                             brightnessup=handle_brightness_up,
                             brightnessdown=handle_brightness_down,
                             whitebalance=handle_white_balance,
                             pantilt=handle_pantilt,
                             zoom=handle_zoom,
                             autofocus=handle_autofocus,
                             prev2prog=handle_prev2prog,
                             preset=handle_preset)

    settings = Sg.UserSettings()
    window_location = settings.get('-location-')
    window_hidden = settings.get('-hidden-')

    if config.debug:
        output = Sg.Output(size=(50, 25)) # bigger window while debugging
    else:
        output = Sg.Output(size=(30, 5))

    menu_def = [['Menu', ['Minimize', 'Configure', 'Help', 'Credits', 'Exit']]]
    layout = [[Sg.Menu(menu_def)], [output]]

    window = Sg.Window( title=config.progname, layout=layout,
                        no_titlebar=True, grab_anywhere=True, location=window_location,
                        enable_close_attempted_event=True,
                        alpha_channel=0.75, keep_on_top=True,
                        icon=controller_icon())
    if window_hidden:
        window.hide()

    if UsePsgTray:
        tooltip = f"Control the {config.progname} app"
        traymenu = ['', ['Show Window', 'Center Window', 'Exit']]
        tray = SystemTray(traymenu,  tooltip=tooltip, window=window,
                          icon=controller_icon())
        window.metadata = tray
    else:
        tray = None

    window.finalize()
    main_window = window

    print(f'{config.progname}({config.progvers})')

    cam = connect_to_camera(1)

    pygame_task_start(window)

    while True:
        if config.debug:
            if not main_loop():
                break
        else:
            try:
                if not main_loop():
                    break
            except Exception as exc:
                print(exc)

    if tray:
        tray.close()

    pygame_task_end()

    if not window.is_closed():
        window.close()
    pygame.quit()



if __name__ == "__main__":
    main()
