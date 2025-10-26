#
# win_print
# send print-out to the main window
#
import PySimpleGUI as Sg
from typing import Optional

print_window: Optional[Sg.Window] = None

def win_print_init(win):
    global print_window
    print_window = win

def win_print(string):
    """ Send string to the main window for printout """
    global print_window

    win = print_window
    win.write_event_value("-PRINT-", string)
