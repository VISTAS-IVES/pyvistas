import platform


def get_platform():
    return 'macos' if platform.uname().system == 'Darwin' else 'windows'
