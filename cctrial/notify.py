import sys
notify = lambda _, __: None
if sys.platform == 'darwin':
    try:
        from .osx import notify
    except ImportError:
        pass
elif sys.platform != 'win32':
    try:
        from .freedesktop import notify
    except ImportError:
        pass

__all__ = ["notify"]
