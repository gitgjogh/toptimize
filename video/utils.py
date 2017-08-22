# !/usr/bin/python
# -*- coding: utf-8 -*-
"""
Copyright
    2017 Jeff <163jogh@163.com>

License
    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    S the License for the specific language governing permissions and
    limitations under the License.

Brief
    utils
"""

import os
import logging
import logger


module_name = "v.rd.collect"
log = logging.getLogger(module_name)


def prepare_save_path(save_name, save_dir=None):
    if save_name is None:
        raise IOError()
    save_dir = "." if save_dir is None else save_dir
    save_path = os.path.join(save_dir, save_name)
    if not os.path.isdir(os.path.dirname(save_path)):
        os.makedirs(os.path.dirname(save_path))
    return save_path
