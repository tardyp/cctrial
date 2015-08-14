from subprocess import call


def notify(title, message, is_pass):
    call(["notify-send", title, message])
