import os
from . import config

conf = config.load_config()

for k, v in conf.items():
    os.makedirs(v, exist_ok=True)

del os
del config
