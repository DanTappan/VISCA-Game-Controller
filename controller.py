#
# Abstract the game controller for Visca Joystick
#
from enum import IntEnum
import time
from idlelib.help import HelpText
from typing import Union
import pygame.event
import platform

Windows = platform.system() == 'Windows'
Linux = platform.system() == 'Linux'

help_text = """
VISCA Controller - control IP PTZ cameras using a Game Controller

Pan & Tilt: Left stick
Zoom: Right stick
Brightness: Left bumper : Decrease, Right: Increase
Manual Focus: Left trigger: Near, Right: Far
Select Camera: A, B, X, Y = 1:4; Long press = 5:8 (selects camera in Preview)
Fade Preview to Program: Push left or right stick
Next button: AutoFocus
Back button: short press = one push white balance, long press = auto white balance
D-pad: short press = recall preset 1-8, long press = set preset 1-8
"""
#
# Define the possible actions associated with controller inputs
class ControlFunc(IntEnum):
    NONE=0
    CAMERA_SELECT=1
    BRIGHTNESSUP=2
    BRIGHTNESSDOWN=3
    PRESET=4
    PREV2PROG=5
    AUTOFOCUS=6
    WHITEBALANCE=7

    # joystick/hat functions
    PANTILT=10
    ZOOM=11
    FOCUSNEAR=12
    FOCUSFAR=13

if Windows:
    class ControllerInput(IntEnum):
        # Buttons
        CAMERA_SELECT_1=0
        CAMERA_SELECT_2=1
        CAMERA_SELECT_3=2
        CAMERA_SELECT_4=3

        BRIGHTNESS_UP=4
        BRIGHTNESS_DOWN=5

        AUTO_FOCUS=6
        WHITE_BALANCE=7
        PREV2PROG=8     # left stick
        PREV2PROG2=9    # right stick

        # Axes
        PAN=0
        TILT=1
        ZOOM=3
        FOCUS_NEAR=4
        FOCUS_FAR=5

        # Hats
        PRESET_HAT=0
elif Linux:
    class ControllerInput(IntEnum):
        # Buttons
        CAMERA_SELECT_1 = 0
        CAMERA_SELECT_2 = 1
        CAMERA_SELECT_3 = 2
        CAMERA_SELECT_4 = 3

        BRIGHTNESS_UP = 4
        BRIGHTNESS_DOWN = 5

        AUTO_FOCUS = 6
        WHITE_BALANCE=7
        PREV2PROG = 8
        PREV2PROG2=9

        # Axes
        PAN = 0
        TILT = 1
        ZOOM = 4
        FOCUS_NEAR = 2
        FOCUS_FAR = 5

        # Hats
        PRESET_HAT=0

class Controller:
    def __init__(self, doubleclick_limit=0, longpress_limit=2):
        self.doubleclick_limit = doubleclick_limit
        self.longpress_limit = longpress_limit

        #
        # per-controller variables
        #
        self.joystick = None
        self.pan_axis = None
        self.tilt_axis = None
        #
        # lists of defined buttons/axes/hats per controller
        #
        self.buttons: list[Union[ControllerButton, None]] = []
        self.axes: list[Union[ControllerAxis, None]] = []
        self.hats: list[Union[ControllerHat, None]] = []

        #
        # map button functions to actions
        self.button_funcs = {}

        # map axis functions to actions
        self.axis_funcs = {}

        # Hat functions act as buttons, so no map required

    def set_callbacks(self, select_cam=None,  focusnear=None, focusfar=None,
                    brightnessup=None, brightnessdown=None,
                      pantilt=None, zoom=None, whitebalance=None, autofocus=None, prev2prog=None, preset=None):
        if select_cam is not None:
            self.button_funcs[ControlFunc.CAMERA_SELECT] = select_cam
        if focusnear is not None:
            self.axis_funcs[ControlFunc.FOCUSNEAR] = focusnear
        if focusfar is not None:
            self.axis_funcs[ControlFunc.FOCUSFAR] = focusfar
        if brightnessup is not None:
            self.button_funcs[ControlFunc.BRIGHTNESSUP] = brightnessup
        if brightnessdown is not None:
            self.button_funcs[ControlFunc.BRIGHTNESSDOWN] = brightnessdown
        if pantilt is not None:
            self.axis_funcs[ControlFunc.PANTILT] = pantilt
        if zoom is not None:
            self.axis_funcs[ControlFunc.ZOOM] = zoom
        if prev2prog is not None:
            self.button_funcs[ControlFunc.PREV2PROG] = prev2prog
        if autofocus is not None:
            self.button_funcs[ControlFunc.AUTOFOCUS] = autofocus
        if whitebalance is not None:
            self.button_funcs[ControlFunc.WHITEBALANCE] = whitebalance
        if preset is not None:
            self.button_funcs[ControlFunc.PRESET] = preset


    def set_pygame_joystick(self, joystick:pygame.joystick.JoystickType):
        #
        # handle a controller add/remove event
        if self.joystick is not None or joystick is None:
            flush_controller(self)

        self.joystick = joystick
        if joystick is not None:
            setup_controller(self)

    def get_pygame_joystick(self):
        return self.joystick

    def pygame_event(self, ev:pygame.event.Event):
        handle_pygame_event(self, ev)

    @staticmethod
    def help_text():
        return HelpText

#
# Handle a controller button push or release
# Buttons can either activate when pushed, or when released.
# In the latter case the time since last push is available
class ControllerButton:
    def __init__(self,
                 controller : Controller,
                 controller_func : ControlFunc,
                 value: int = 0):
        self.time_down = 0
        self.double_click = False
        self.long_press = False
        self.time_down = 0
        self.is_down = False
        self.value = value

        self.isdown = False
        self.controller = controller
        self.controller_func = controller_func

    def button_down(self):
        # debounce
        if self.is_down:
            return
        self.is_down = True
        self.double_click = (time.time() - self.time_down) < self.controller.doubleclick_limit
        self.time_down = time.time()
        self.long_press = False
        handle_button(self)

    def button_up(self):
        if not self.is_down:
            return
        self.is_down = False
        self.long_press = (time.time() - self.time_down) > self.controller.longpress_limit
        handle_button(self)


class ControllerAxis:
    def __init__(self, controller, control_func: ControlFunc, value=0):
        self.controller = controller
        self.control_func = control_func
        self.value = value

    def value(self):
        return self.value

    def event(self):
        try:
            f = self.controller.axis_funcs[self.control_func]
            f(axis=self)
        except KeyError:
            pass


# Handle a HAT event
# HATs are treated as a button with 8 values
#
hat_value = {(0, 1):1, (1, 1):2, (1, 0):3, (1, -1):4, (0, -1):5, (-1, -1):6, (-1, 0):7, (-1, 1):8}
class ControllerHat:
    def __init__(self, controller, control_func, value):
        self.controller = controller
        self.value = value
        self.is_down = False
        self.button = ControllerButton(controller, control_func, 0)

    def event(self):
        try:
            joystick = self.controller.get_pygame_joystick()
            if joystick is None:
                return
            time.sleep(0.1) # sleep a tick to debounce the hat
            val = joystick.get_hat(self.value)
            btn_value = hat_value[val]
            btn_down = True
        except KeyError:
            btn_value = 0
            btn_down = False

        if self.is_down and not btn_down:
            self.is_down = False
            self.button.button_up()
        elif btn_down:
            self.button.value = btn_value
            if not self.is_down:
                self.is_down = True
                self.button.button_down()

def handle_button(button: ControllerButton):
    """
    Handle a button press or release
    :param button:
    :return: None
    """
    try:
        f = button.controller.button_funcs[button.controller_func]
        f(button=button)
    except KeyError:
        pass

#
# flush_controller - clear dictionaries after a hot swap removal
def flush_controller(controller:Controller):
    del controller.buttons
    del controller.axes
    del controller.hats
    controller.pan_axis = None
    controller.tilt_axis = None

#
# setup_controller - handle a newly attached controller
def setup_controller(controller: Controller):
    joystick = controller.get_pygame_joystick()

    null_button = ControllerButton(controller, ControlFunc.NONE)
    controller.buttons = [null_button] * joystick.get_numbuttons()
    controller.buttons[ControllerInput.CAMERA_SELECT_1] = ControllerButton(controller, ControlFunc.CAMERA_SELECT, 1)
    controller.buttons[ControllerInput.CAMERA_SELECT_2] = ControllerButton(controller, ControlFunc.CAMERA_SELECT, 2)
    controller.buttons[ControllerInput.CAMERA_SELECT_3] = ControllerButton(controller, ControlFunc.CAMERA_SELECT, 3)
    controller.buttons[ControllerInput.CAMERA_SELECT_4] = ControllerButton(controller, ControlFunc.CAMERA_SELECT, 4)

    controller.buttons[ControllerInput.BRIGHTNESS_UP] = ControllerButton(controller, ControlFunc.BRIGHTNESSUP)
    controller.buttons[ControllerInput.BRIGHTNESS_DOWN] = ControllerButton(controller, ControlFunc.BRIGHTNESSDOWN)
    controller.buttons[ControllerInput.AUTO_FOCUS] = ControllerButton(controller, ControlFunc.AUTOFOCUS)
    controller.buttons[ControllerInput.WHITE_BALANCE] = ControllerButton(controller, ControlFunc.WHITEBALANCE)
    controller.buttons[ControllerInput.PREV2PROG] = ControllerButton(controller, ControlFunc.PREV2PROG)
    controller.buttons[ControllerInput.PREV2PROG2] = ControllerButton(controller, ControlFunc.PREV2PROG)

    null_axis = ControllerAxis(controller, ControlFunc.NONE)
    controller.axes = [null_axis] * joystick.get_numaxes()

    axis = ControllerAxis(controller, ControlFunc.PANTILT, ControllerInput.PAN)
    controller.axes[ControllerInput.PAN] = axis
    controller.pan_axis = axis
    axis = ControllerAxis(controller, ControlFunc.PANTILT, ControllerInput.TILT)
    controller.axes[ControllerInput.TILT] = axis
    controller.tilt_axis = axis

    axis = ControllerAxis(controller, ControlFunc.ZOOM, ControllerInput.ZOOM)
    controller.axes[ControllerInput.ZOOM] = axis

    axis = ControllerAxis(controller, ControlFunc.FOCUSNEAR, ControllerInput.FOCUS_NEAR)
    controller.axes[ControllerInput.FOCUS_NEAR] = axis
    axis = ControllerAxis(controller, ControlFunc.FOCUSFAR, ControllerInput.FOCUS_FAR)
    controller.axes[ControllerInput.FOCUS_FAR] = axis

    # TODO - define hats
    #
    null_hat = ControllerHat(controller, ControlFunc.NONE, 0)
    controller.hats = [null_hat] * joystick.get_numhats()
    controller.hats[ControllerInput.PRESET_HAT] = ControllerHat(controller, ControlFunc.PRESET, ControllerInput.PRESET_HAT)


#
# Handle a pygame event
def handle_pygame_event(controller: Controller, ev: pygame.event.Event):

    if ev.type == pygame.JOYBUTTONDOWN or ev.type == pygame.JOYBUTTONUP:
        button = controller.buttons[ev.dict['button']]
        if ev.type == pygame.JOYBUTTONDOWN:
            button.button_down()
        else:
            button.button_up()

    elif ev.type == pygame.JOYAXISMOTION:
        axis = controller.axes[ev.dict['axis']]
        axis.event()

    elif ev.type == pygame.JOYHATMOTION:
        hat = controller.hats[ev.dict['hat']]
        hat.event()


