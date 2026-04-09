#
# Abstract the game controller for Visca Joystick
#
from enum import IntEnum
import time
from typing import Union, Dict

import pygame
import pygame.event
import platform
from file_paths import file_path
from win_print import win_print
from controller_map import controller_map

Windows = platform.system() == 'Windows'
Linux = platform.system() == 'Linux'

class ControllerList:
    def __init__(self, callbacks, long_press, dead_zone):
        self.dict: Dict[int, Controller] = {}
        self.callbacks = callbacks
        self.long_press = long_press
        self.dead_zone = dead_zone

    def __iter__(self):
        return iter(self.dict)

    def add(self, index):
        joy = pygame.joystick.Joystick(index)
        instance_id = joy.get_instance_id()
        self.remove(instance_id)
        controller = Controller(self.callbacks,
                                long_press_limit=self.long_press,
                                dead_zone=self.dead_zone)
        controller.set_callbacks(self.callbacks)
        controller.set_pygame_joystick(joy)
        self.dict[instance_id] = controller
        return controller

    def remove(self, instance_id):
        try:
            controller = self.dict.pop(instance_id)
        except KeyError:
            controller = None
        if controller is not None:
            flush_controller(controller)
            del controller

    def lookup(self, instance_id):
        return self.dict.get(instance_id)

help_text_controller = """

Pan & Tilt    
                Left stick
Zoom
                Right stick
Brightness    
                Left bumper : Decrease, 
                Right: Increase
Manual Focus
                Left trigger: Near, 
                Right: Far
Select Camera 
                A, B, X, Y: 1-4; 
                Long press: 5-8 
                Puts selected camera in Preview
Fade Preview to Program 
                Push left or right stick
AutoFocus mode
                "Next" button
White Balance  
                Back button
                short press: one push white balance
                long press: auto white balance
Presets 1-8   
                Hat, direction selects preset number 
                Short press: recall
                long press: set
"""

help_text_joystick = """

Pan & Tilt     
                Joystick L/R/U/D
Zoom
                Twist joystick
Manual Focus
                Hat
                up: focus far 
                down: focus near 
                left/right: autofocus
Select Camera
                Top buttons: 1-4
                long press: 5-8
                puts selected camera in Preview
Fade Preview to Program 
                Front trigger
White Balance
                Side trigger
                short press: one push white balance 
                long press: auto white balance
Presets 1-6    
                Base buttons. 
                short press: recall
                long press: set
"""

help_text_homebrew = """

Pan & Tilt     
                Joystick L/R/U/D
Zoom
                Twist joystick
Fade Preview to Program 
                Top button
"""
#
# Types of controls
class ControlType(IntEnum):
    BUTTON=0
    AXIS=1
    HAT=2

#
# Define the possible actions associated with controller inputs
class ControlFunc(IntEnum):
    NONE=0
    CAMERA_SELECT=1
    BRIGHTNESS_UP=2
    BRIGHTNESS_DOWN=3
    PRESET=4
    PREV2PROG=5
    AUTOFOCUS=6
    WHITE_BALANCE=7

    # joystick/hat functions
    PANTILT=10
    ZOOM=11
    FOCUS_NEAR=12
    FOCUS_FAR=13
    FOCUS=14
    TBAR=15

class BaseControllerDef:
    def __init__(self, init_dict=None):
        if init_dict is None:
            self.dict = {}
        else:
            self.dict = init_dict

    def set(self, key, t, v):
        self.dict[key] = (t, v)

    def type(self, key):
        try:
            return self.dict[key][0]
        except KeyError:
            return None

    def value(self, key):
        try:
            return self.dict[key][1]
        except KeyError:
            return None

    def get_dict(self):
        return self.dict

def controller_type(joystick) -> BaseControllerDef | None:
    """ Find the controller definition for a given joystick type.
        This tries to load a configuration JSON file based on the joystick name
        """
    controller_dict = controller_map(joystick.get_name())
    if controller_dict is not None:
        controller_def = BaseControllerDef(controller_dict)
        return controller_def
    else:
        win_print(f'ERROR: controller config not found')
        return None

def null_function():
    return None

class Controller:
    def __init__(self, joy:pygame.joystick.JoystickType,
                 doubleclick_limit=0, long_press_limit=2, dead_zone=None):
        self.doubleclick_limit = doubleclick_limit
        self.long_press_limit = long_press_limit
        self.help_text = ""
        self.help_image = ""
        #
        # per-controller variables
        #
        self.joystick = joy
        self.pan_axis = None
        self.tilt_axis = None
        self.dead_zone = dead_zone # override device default

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
        self.flush_axis_events = null_function

    def set_callbacks(self, callbacks):
        self.button_funcs[ControlFunc.CAMERA_SELECT] = callbacks.get("select_cam", null_function)
        self.button_funcs[ControlFunc.FOCUS] = callbacks.get("focus", null_function)
        self.axis_funcs[ControlFunc.FOCUS_NEAR] = callbacks.get("focus_near", null_function)
        self.axis_funcs[ControlFunc.FOCUS_FAR] = callbacks.get("focus_far", null_function)
        self.button_funcs[ControlFunc.BRIGHTNESS_UP] = callbacks.get("brightness_up", null_function)
        self.button_funcs[ControlFunc.BRIGHTNESS_DOWN] = callbacks.get("brightness_down", null_function)
        self.axis_funcs[ControlFunc.PANTILT] = callbacks.get("pantilt", null_function)
        self.axis_funcs[ControlFunc.ZOOM] = callbacks.get("zoom", null_function)
        self.axis_funcs[ControlFunc.TBAR] = callbacks.get("tbar", null_function)
        self.button_funcs[ControlFunc.PREV2PROG] = callbacks.get("prev2prog", null_function)
        self.button_funcs[ControlFunc.AUTOFOCUS] = callbacks.get("autofocus", null_function)
        self.button_funcs[ControlFunc.WHITE_BALANCE] = callbacks.get("white_balance", null_function)
        self.button_funcs[ControlFunc.PRESET] = callbacks.get("preset", null_function)
        self.flush_axis_events = callbacks.get("flushaxis", null_function)

    def flush_axis_events(self):
        self.flush_axis_events()

    def set_pygame_joystick(self, joystick:pygame.joystick.JoystickType):
        self.joystick = joystick
        if joystick is not None:
            setup_controller(self)

    def get_pygame_joystick(self):
        return self.joystick

    def pygame_event(self, ev:pygame.event.Event):
        handle_pygame_event(self, ev)

    def help_text(self):
        return self.help_text

    def set_help_text(self, text):
        self.help_text = text

    def help_image(self):
        return self.help_image

    def set_help_image(self, f):
        self.help_image = f

#
# Handle a controller button push or release
# Buttons can either activate when pushed, or when released.
# In the latter case the time since last push is available
class ControllerButton:
    def __init__(self,
                 controller : Controller,
                 controller_func : ControlFunc,
                 value: int = 0,
                 ctype: ControlType= ControlType.BUTTON):
        self.time_down = 0
        self.double_click = False
        self.long_press = False
        self.time_down = 0
        self.is_down = False
        self.value = value
        self.moving = False # state variable
        self.isdown = False
        self.controller = controller
        self.controller_func = controller_func
        self.type = ctype

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
        self.long_press = (time.time() - self.time_down) > self.controller.long_press_limit
        handle_button(self)


class ControllerAxis:
    def __init__(self, controller, control_func: ControlFunc, value=0, invert=1, dead_zone=0):
        self.controller = controller
        self.control_func = control_func
        self.type = ControlType.AXIS
        self.value = value
        self.moving = False # state variable
        self.position = 0
        self.invert = invert
        self.dead_zone = dead_zone

    def value(self):
        return self.value

    def get_position(self):
        self.position = self.controller.joystick.get_axis(self.value)*self.invert
        return self.position

    def set_moving(self, v):
        self.moving = v

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
        self.button = ControllerButton(controller, control_func, 0, ControlType.HAT)

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
    device = controller_type(joystick)
    if device is None:
        return

    null_button = ControllerButton(controller, ControlFunc.NONE)
    controller.buttons = [null_button] * joystick.get_numbuttons()

    null_axis = ControllerAxis(controller, ControlFunc.NONE)
    controller.axes = [null_axis] * joystick.get_numaxes()

    null_hat = ControllerHat(controller, ControlFunc.NONE, 0)
    controller.hats = [null_hat] * joystick.get_numhats()

    dead_zone = device.value("DEAD_ZONE")
    if controller.dead_zone is not None:
        dead_zone = controller.dead_zone # configuration override default
    controller.set_help_text(device.value("HELP"))
    controller.set_help_image(file_path(device.value("HELP_IMAGE")))

    try:
        controller.buttons[device.value("CAMERA_SELECT_1")] =  ControllerButton(controller,
                                                                                ControlFunc.CAMERA_SELECT, 1)
        controller.buttons[device.value("CAMERA_SELECT_2")] = ControllerButton(controller,
                                                                               ControlFunc.CAMERA_SELECT, 2)
        controller.buttons[device.value("CAMERA_SELECT_3")] = ControllerButton(controller,
                                                                               ControlFunc.CAMERA_SELECT, 3)
        controller.buttons[device.value("CAMERA_SELECT_4")] = ControllerButton(controller, ControlFunc.CAMERA_SELECT, 4)
    except TypeError:
        pass

    t = device.type("BRIGHTNESS_UP")
    if t == "button":
        v = device.value("BRIGHTNESS_UP")
        controller.buttons[v] = ControllerButton(controller, ControlFunc.BRIGHTNESS_UP)
    t = device.type("BRIGHTNESS_DOWN")
    if t == "button":
        v = device.value("BRIGHTNESS_DOWN")
        controller.buttons[v] = ControllerButton(controller, ControlFunc.BRIGHTNESS_DOWN)

    t = device.type("AUTO_FOCUS")
    if t == "button":
        v = device.value("AUTO_FOCUS")
        controller.buttons[v] = ControllerButton(controller, ControlFunc.AUTOFOCUS)

    t = device.type("WHITE_BALANCE")
    if t == "button":
        controller.buttons[device.value("WHITE_BALANCE")] = ControllerButton(controller,
                                                                             ControlFunc.WHITE_BALANCE)
    t = device.type("PREV2PROG")
    if t == "button":
        controller.buttons[device.value("PREV2PROG")] = ControllerButton(controller,
                                                                         ControlFunc.PREV2PROG)

    v = device.value("PREV2PROG2")
    if v is not None:
        controller.buttons[v] = ControllerButton(controller, ControlFunc.PREV2PROG)

    v = device.value("PAN")
    if v is not None:
        axis = ControllerAxis(controller, ControlFunc.PANTILT, v, dead_zone=dead_zone)
        controller.axes[v] = axis
        controller.pan_axis = axis

    v = device.value("TILT")
    if v is not None:
        axis = ControllerAxis(controller, ControlFunc.PANTILT, v, dead_zone=dead_zone)
        controller.axes[v] = axis
        controller.tilt_axis = axis

    v = device.value("ZOOM")
    if v is not None:
        axis = ControllerAxis(controller, ControlFunc.ZOOM, v,
                              invert=device.value("INVERT_ZOOM"), dead_zone=dead_zone)
        controller.axes[v] = axis

    v = device.value("TBAR")
    if v is not None:
        axis = ControllerAxis(controller, ControlFunc.TBAR, v, dead_zone=0)
        controller.axes[v] = axis

    t = device.type("FOCUS_NEAR")
    if t == "axis":
        v = device.value("FOCUS_NEAR")
        axis = ControllerAxis(controller, ControlFunc.FOCUS_NEAR, v, dead_zone=dead_zone)
        controller.axes[v] = axis

    t = device.type("FOCUS_FAR")
    if t == "axis":
        v = device.value("FOCUS_FAR")
        axis = ControllerAxis(controller, ControlFunc.FOCUS_FAR, v, dead_zone=dead_zone)
        controller.axes[v] = axis

    t = device.type("FOCUS")
    if t == "hat":
        v = device.value("FOCUS")
        controller.hats[v] = ControllerHat(controller, ControlFunc.FOCUS, 0)

    t = device.type("PRESETS")
    if t == "hat":
        v = device.value("PRESETS")
        controller.hats[v] = ControllerHat(controller, ControlFunc.PRESET, v)
    elif t == "button":
        button_num = device.value("PRESETS")
        for v in range(device.value("NUM_PRESETS")):
            controller.buttons[button_num + v] = ControllerButton(controller, ControlFunc.PRESET, v+1)


#
# Handle a pygame event
def handle_pygame_event(controller: Controller, ev: pygame.event.Event):

    if ev.type == pygame.JOYAXISMOTION:
        axis = controller.axes[ev.axis]
        dead_zone = axis.dead_zone
        try:
            if ev.value < 0:
                sign = -1
            else:
                sign = 1
            v = abs(ev.value)
            if not axis.moving and v <= dead_zone:
                # Flush excess axis events that slow things down
                controller.flush_axis_events()
                return
            else:
                v = (1.0-dead_zone)/(v - dead_zone) * sign
                ev.value = v
        except ZeroDivisionError:
            ev.value = 0

        # Flush excess axis events that slow things down
        controller.flush_axis_events()
        axis.event()

    elif ev.type == pygame.JOYBUTTONDOWN or ev.type == pygame.JOYBUTTONUP:
        button = controller.buttons[ev.button]
        if ev.type == pygame.JOYBUTTONDOWN:
            button.button_down()
        else:
            button.button_up()
    elif ev.type == pygame.JOYHATMOTION:
        hat = controller.hats[ev.hat]
        # flush excess events
        controller.flush_axis_events()
        hat.event()


