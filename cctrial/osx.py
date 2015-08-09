try:
    from pync import Notifier
except ImportError:
    Notifier = None
from subprocess import call


def notify(title, message):
    if Notifier is not None:
        Notifier.notify(message, title=title)
    else:
        call(["terminal-notifier", "-title", title, '-message', message])
