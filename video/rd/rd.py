# !/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2017 Jeff <163jogh@163.com>

##############################################################################
 # Licensed under the Apache License, Version 2.0 (the "License");
 # you may not use this file except in compliance with the License.
 # You may obtain a copy of the License at
 #
 #     http://www.apache.org/licenses/LICENSE-2.0
 #
 # Unless required by applicable law or agreed to in writing, software
 # distributed under the License is distributed on an "AS IS" BASIS,
 # WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 # See the License for the specific language governing permissions and
 # limitations under the License.
##############################################################################

import os
import json
import logging
import subprocess
import cfg.tools
import collect
import plot


FFMPEG = cfg.tools.ffmpeg
FONT_MSYH = cfg.tools.font_msyh
RUN_VMAF = cfg.tools.run_vmaf
RUN_VMAF_PY = cfg.tools.run_vmaf_py
module_name = "v.rd.plot"
log = logging.getLogger(module_name)


_task_check_list = [
    "title", "desc",
    #"show_all", "save_raw_json", "save_plot_json",
    "graph_cfg_list",
    "axles_cfg_list",
    "line_cfg_list",
    "point_cfg_list"
]

_graph_check_list = [
    "title", "input",
    # "show_pic", "save_pic", "save_raw_json", "save_plot_json",
    "width", "height", "subw", "subh"
]

_axles_check_list = [
    "title", "subx", "suby", "xprop", "yprop"
]

_line_check_list = [
    "label", "cmp_res", "cmp_frames",
    "input_param", "output_param"
]

_point_check_list = [
    "label", "params"
]


def _missing_file(file):
    if not os.path.isfile(file):
        log.error("file not exist: " + file)
        return 1
    return 0


def _missing_tools():
    """
    :return: 0 for ok, else something problem
    """
    ret = 0
    ret += _missing_file(FFMPEG)
    ret += _missing_file(FONT_MSYH)
    ret += _missing_file(RUN_VMAF)
    ret += _missing_file(RUN_VMAF_PY)
    return ret


def _missing_inputs(task_cfg):
    """
    :return: 0 for ok, else something problem
    """
    ret = 0
    graph_cfg_list = task_cfg["graph_cfg_list"]
    for graph in graph_cfg_list:
        ret += _missing_file(graph["input"])
    return ret


def start_check(task_cfg):
    if _missing_tools() != 0:
        raise EnvironmentError("tool check failed")
    if _missing_inputs(task_cfg) != 0:
        raise IOError("input check failed")


def _copy_non_exist_key(cfg_list, cfg_base):
    """
    copy maps, of that not exist in @cfg_base, from @cfg_base to @cfg_list
    """
    for key in cfg_base:
        for entry in cfg_list:
            entry[key] = entry.get(key, cfg_base[key])


def config_parse(task_cfg):
    """
    turn user config to task config
    :param task_cfg:
    :return:
    """
    _copy_non_exist_key(task_cfg["graph_cfg_list"], task_cfg["graph_cfg_base"])
    _copy_non_exist_key(task_cfg["axles_cfg_list"], task_cfg["axles_cfg_base"])
    _copy_non_exist_key(task_cfg["line_cfg_list"], task_cfg["line_cfg_base"])
    cfg_array, cfg_base = task_cfg["point_cfg_list"], task_cfg["point_cfg_base"]
    for key in cfg_base:
        for entry in cfg_array:
            entry["params"][key] = entry["params"].get(key, cfg_base[key])


def _missing_keys(d, check_list, father_name):
    node_name = d.get("label", d.get("title", "unknown_node"))
    n_lost = 0
    for key in check_list:
        if key not in d:
            log.error("missing '{:s}' in node {:s}['{:s}']".format(key, father_name, node_name))
            n_lost += 1
    return n_lost


def config_check(task_cfg):
    log.info(json.dumps(task_cfg, indent=4))
    if _missing_keys(task_cfg, _task_check_list, "root"):
        raise KeyError()
    for graph_cfg in task_cfg["graph_cfg_list"]:
        if _missing_keys(graph_cfg, _graph_check_list, "graph_cfg_list"):
            raise KeyError()
    for axles_cfg in task_cfg["axles_cfg_list"]:
        if _missing_keys(axles_cfg, _axles_check_list, "axles_cfg_list"):
            raise KeyError()
    for line_cfg in task_cfg["line_cfg_list"]:
        if _missing_keys(line_cfg, _line_check_list, "line_cfg_list"):
            raise KeyError()
    for point_cfg in task_cfg["point_cfg_list"]:
        if _missing_keys(point_cfg, _point_check_list, "point_cfg_list"):
            raise KeyError()


def run_rd_task(task_cfg):
    start_check(task_cfg)
    config_parse(task_cfg)
    config_check(task_cfg)
    try:
        raw_task_data = collect.collect_task_data(task_cfg)
        dst_task_data = plot.pick_data_for_task(raw_task_data)
        plot.plot_task_data(dst_task_data)
    except Exception as e:
        log.error("Exception = `%s`", repr(e))
        raise e
    #
    return dst_task_data


def _main_test(json_file):
    import matplotlib.pyplot as plt
    try:
        with open(json_file, "r") as f:
            raw_task_data = json.loads(f.read())
            dst_task_data = run_rd_task(raw_task_data)
            if dst_task_data.get("show_all") is True:
                plt.show()
    except Exception as e:
        log.error("Exception = `%s`", repr(e))
        raise e


def _main_parser():
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-i", "--json", dest="json_file", help=r"input json data file")
    return parser


def _create_module_log():
    import logger
    logger.log2file(module_name + ".log", logging.INFO)
    logger.log2stdout(None, logfmt=logger.DEFAULT_LOGFMT)


if __name__ == "__main__":
    import sys
    reload(sys)
    sys.setdefaultencoding('utf-8')     # <! 中文设置
    #
    _create_module_log()
    parser = _main_parser()
    (opt, args) = parser.parse_args()
    _main_test(opt.json_file)
    log.info("done")
