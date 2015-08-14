try:
    from pync import Notifier
except ImportError:
    Notifier = None
from subprocess import call
import os


def notify(title, message, is_pass=True):
    if is_pass:
        icon = "pass"
    else:
        icon = "fail"
    icon = os.path.join(os.path.dirname(__file__), icon + ".png")
    if Notifier is not None:
        Notifier.notify(message, title=title)
    else:
        call(["terminal-notifier", "-title", title, '-message', message, '-appIcon', icon])
