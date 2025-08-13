#
# Abstract the game controller for Visca Joystick
#
from enum import IntEnum
import time
from typing import Union

import pygame
import pygame.event
import platform
from file_paths import file_path

Windows = platform.system() == 'Windows'
Linux = platform.system() == 'Linux'


help_text_controller = """
Control PTZ cameras using a Game Controller

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
Control PTZ cameras using a Flight Simulator Joystick

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

class BaseControllerInput:
    def __init__(self):
        self.dict = {}

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

class GameControllerInput(BaseControllerInput):
    def __init__(self):
        super().__init__()
        super().set("CAMERA_SELECT_1", "button", 0)
        super().set("CAMERA_SELECT_2", "button", 1)
        super().set("CAMERA_SELECT_3", "button", 2)
        super().set("CAMERA_SELECT_4", "button", 3)

        super().set("BRIGHTNESS_UP", "button", 4)
        super().set("BRIGHTNESS_DOWN", "button", 5)

        super().set("AUTO_FOCUS", "button", 6)
        super().set("WHITE_BALANCE", "button", 7)

        super().set("PREV2PROG", "button", 8) # left stick
        super().set("PREV2PROG2", "button", 9) # right stick

        # Axes
        if Windows:
            super().set("PAN", "axis", 0)
            super().set("TILT", "axis", 1)
            super().set("ZOOM", "axis", 3)
            super().set("FOCUS_NEAR", "axis", 4)
            super().set("FOCUS_FAR", "axis", 5)
        elif Linux:
            super().set("PAN", "axis", 0)
            super().set("TILT", "axis", 1)
            super().set("ZOOM", "axis", 4)
            super().set("FOCUS_NEAR", "axis", 2)
            super().set("FOCUS_FAR", "axis", 5)
        super().set("INVERT_ZOOM",  "number",1)
        # Hats
        super().set("PRESETS", "hat", 0)
        super().set("HELP", "string", help_text_controller)
        super().set("HELP_IMAGE", "file", 'GameController.png')
        super().set("DEAD_ZONE", "number", 0)


class JoystickControllerInput(BaseControllerInput):
    def __init__(self):
        super().__init__()
        super().set("CAMERA_SELECT_1", "button", 4)
        super().set("CAMERA_SELECT_2", "button", 2)
        super().set("CAMERA_SELECT_3", "button", 3)
        super().set("CAMERA_SELECT_4", "button", 5)

     #   No buttons for Brightness

        super().set("WHITE_BALANCE", "button", 1)# side
        super().set("PREV2PROG", "button", 0)  # trigger

        # Axes
        super().set("PAN", "axis", 0)
        super().set("TILT", "axis", 1)
        super().set("ZOOM", "axis", 2)
        super().set("INVERT_ZOOM", "number", -1)

        super().set("FOCUS", "hat", 0)

        super().set("PRESETS", "button", 6) # start at button 6
        super().set("NUM_PRESETS", "number", 6) #  number of preset buttons
        super().set("FOCUS", "hat", 0)

        super().set("HELP", "string", help_text_joystick)
        super().set("HELP_IMAGE", "file", 'LogitechJoystick.png')
        # Dead zone for filtering axis events
        # we need this because the Logitech joystick tends to moves the twist (zoom) axis
        # when moving left or right
        super().set("DEAD_ZONE", "number", 0.3)


class Controller:
    def __init__(self, doubleclick_limit=0, long_press_limit=2, dead_zone=None):
        self.doubleclick_limit = doubleclick_limit
        self.long_press_limit = long_press_limit
        self.help_text = ""
        self.help_image = ""
        #
        # per-controller variables
        #
        self.joystick = None
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

    def set_callbacks(self, select_cam=None,  focus = None, focus_near=None, focus_far=None,
                    brightness_up=None, brightness_down=None,
                      pantilt=None, zoom=None, white_balance=None, autofocus=None, prev2prog=None, preset=None):
        if select_cam is not None:
            self.button_funcs[ControlFunc.CAMERA_SELECT] = select_cam
        if focus is not None:
                self.button_funcs[ControlFunc.FOCUS] = focus
        if focus_near is not None:
            self.axis_funcs[ControlFunc.FOCUS_NEAR] = focus_near
        if focus_far is not None:
            self.axis_funcs[ControlFunc.FOCUS_FAR] = focus_far
        if brightness_up is not None:
            self.button_funcs[ControlFunc.BRIGHTNESS_UP] = brightness_up
        if brightness_down is not None:
            self.button_funcs[ControlFunc.BRIGHTNESS_DOWN] = brightness_down
        if pantilt is not None:
            self.axis_funcs[ControlFunc.PANTILT] = pantilt
        if zoom is not None:
            self.axis_funcs[ControlFunc.ZOOM] = zoom
        if prev2prog is not None:
            self.button_funcs[ControlFunc.PREV2PROG] = prev2prog
        if autofocus is not None:
            self.button_funcs[ControlFunc.AUTOFOCUS] = autofocus
        if white_balance is not None:
            self.button_funcs[ControlFunc.WHITE_BALANCE] = white_balance
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

    def help_text(self):
        return self.help_text

    def set_help_text(self, text):
        self.help_text = text

    def help_image(self):
        return self.help_image

    def set_help_image(self, f):
        self.help_image = f

# Algorithm for deciding what type of controller we have. Currently, this is  a heuristic
# based on the number of axis and buttons
def controller_type(controller: Controller):
    joystick = controller.get_pygame_joystick()

    num_axes = joystick.get_numaxes()
    if num_axes == 6:
        print("Game Controller")
        return GameControllerInput()
    elif num_axes == 4:
        print("Flight Controller Joystick")
        return JoystickControllerInput()
    else:
        return None

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
    device = controller_type(controller)
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

    controller.buttons[device.value("CAMERA_SELECT_1")] =  ControllerButton(controller, ControlFunc.CAMERA_SELECT, 1)
    controller.buttons[device.value("CAMERA_SELECT_2")] = ControllerButton(controller, ControlFunc.CAMERA_SELECT, 2)
    controller.buttons[device.value("CAMERA_SELECT_3")] = ControllerButton(controller, ControlFunc.CAMERA_SELECT, 3)
    controller.buttons[device.value("CAMERA_SELECT_4")] = ControllerButton(controller, ControlFunc.CAMERA_SELECT, 4)

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

    controller.buttons[device.value("WHITE_BALANCE")] = ControllerButton(controller, ControlFunc.WHITE_BALANCE)
    controller.buttons[device.value("PREV2PROG")] = ControllerButton(controller, ControlFunc.PREV2PROG)
    v = device.value("PREV2PROG2")
    if v is not None:
        controller.buttons[v] = ControllerButton(controller, ControlFunc.PREV2PROG)

    v = device.value("PAN")
    axis = ControllerAxis(controller, ControlFunc.PANTILT, v, dead_zone=dead_zone)
    controller.axes[v] = axis
    controller.pan_axis = axis
    v = device.value("TILT")
    axis = ControllerAxis(controller, ControlFunc.PANTILT, v, dead_zone=dead_zone)
    controller.axes[v] = axis
    controller.tilt_axis = axis

    v = device.value("ZOOM")
    axis = ControllerAxis(controller, ControlFunc.ZOOM, v, invert=device.value("INVERT_ZOOM"), dead_zone=dead_zone)
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
                return
            else:
                v = (1.0-dead_zone)/(v - dead_zone) * sign
                ev.value = v
        except ZeroDivisionError:
            ev .value = 0

        # flush the event queue to get rid of a flood of axis events
        # that slow things down
        pygame.event.clear(pygame.JOYAXISMOTION)

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
        pygame.event.clear(pygame.JOYAXISMOTION)
        hat.event()


