import os
from logging.config import dictConfig

from vistas.ui.app import App

try:
    import BUILD_CONSTANTS
except ImportError:
    BUILD_CONSTANTS = None

profile = getattr(BUILD_CONSTANTS, 'VISTAS_PROFILE', 'dev')

if profile == 'dev':
    dictConfig({
        'version': 1,
        'formatters': {
            'verbose': {
                'format': '[%(levelname)s] [%(asctime)s:%(msecs).0f] %(message)s\n',
                'datefmt': '%Y/%m/%d %H:%M:%S'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'verbose',
                'level': 'DEBUG',
                'stream': 'ext://sys.stdout'
            }
        },
        'loggers': {
            'vistas': {
                'level': 'DEBUG',
                'handlers': ['console']
            }
        }
    })

else:
    if not os.path.exists(os.path.join(os.getcwd(), 'logs')):
        os.mkdir(os.path.join(os.getcwd(), 'logs'))

    dictConfig({
        'version': 1,
        'formatters': {
            'verbose': {
                'format': '[%(levelname)s] [%(asctime)s:%(msecs).0f] %(message)s\n',
                'datefmt': '%Y/%m/%d %H:%M:%S'
            }
        },
        'handlers': {
            'file': {
                'class': 'logging.handlers.TimedRotatingFileHandler',
                'formatter': 'verbose',
                'level': 'DEBUG',
                'filename': os.path.join(os.getcwd(), 'logs', 'log.txt'),
                'when': 'D',
                'interval': 7
            }
        },
        'loggers': {
            'vistas': {
                'level': 'DEBUG',
                'handlers': ['file']
            }
        }
    })

app = App.get()
app.MainLoop()
