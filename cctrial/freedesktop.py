from subprocess import call


def notify(title, message):
    call(["notify-send", title, message])
