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
    pick plot data from raw data that collected by collect.collect_task_data()
    plot picked data
"""

import copy
import json
import logging
import subprocess
import video.utils as utils
import cfg.tools

FFMPEG = cfg.tools.ffmpeg
FONT_MSYH = cfg.tools.font_msyh
module_name = "v.rd.plot"
log = logging.getLogger(module_name)

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
plt.rcParams['axes.unicode_minus']=False                #用来正常显示负号
from matplotlib.font_manager import FontProperties
chsfont = FontProperties(fname=FONT_MSYH)


# class DotDict(dict):
#     def __getattr__(self, key):
#         return self[key]


def pick_data_for_task_for_axles(raw_line_array, axcfg):
    """
    pick 2d-data from @raw_line_array accroding to @axcfg
    :return: axles data for plot
    """
    xprop = axcfg["xprop"]
    yprop = axcfg["yprop"]

    dst_axles = copy.deepcopy(axcfg)
    dst_axles.update({
        "xlabel": axcfg.get("xlabel", xprop),
        "ylabel": axcfg.get("ylabel", yprop),
        "line_array": []
    })
    #
    for raw_line in raw_line_array:
        dst_line = {
            "label": raw_line["label"],
            "tlist": [],
            "xlist": [],
            "ylist": []
        }
        for raw_point in raw_line["point_array"]:
            dst_line["xlist"].append(raw_point[xprop])
            dst_line["ylist"].append(raw_point[yprop])
            dst_line["tlist"].append(raw_point["label"])
        dst_axles["line_array"].append(dst_line)
    return dst_axles


def pick_data_for_task_for_figure(task_cfg, raw_graph, axles_cfgs):
    """
    convert multi-dimensional line to 2d-alxes according to @alxes_cfgs
    :return: figure data for plot
    """
    try:
        assert raw_graph["data_format"] == "raw_data"
        dst_graph = copy.deepcopy(raw_graph)
        dst_graph.update({
            "data_format": "plot_data",
            "axles_array": []
        })
        #
        raw_line_array = raw_graph["line_array"]
        for axcfg in axles_cfgs:
            dst_axles = pick_data_for_task_for_axles(raw_line_array, axcfg)
            dst_graph["axles_array"].append(dst_axles)
        if dst_graph.get("save_plot_json") is not None:
            save_path = utils.prepare_save_path(
                save_name=dst_graph.get("save_plot_json"),
                save_dir=task_cfg.get("data_save_dir")
            )
            with open(save_path, "w") as f:
                json.dump(dst_graph, fp=f, indent=4)
        return dst_graph
    except Exception as e:
        log.error("Exception = `%s`", repr(e))
        raise e


def pick_data_for_task(raw_task):
    """
    convert collected data to plotable data
    the mainly work is separate curve into axles
    :param collected_data:
    :return:
    """
    try:
        assert raw_task["data_format"] == "raw_data"
        dst_task = copy.deepcopy(raw_task)
        dst_task.update({
            "data_format": "plot_data",
            "graph_array": []
        })
        #
        task_cfg = raw_task
        axles_cfgs = task_cfg["axles_cfg_list"]

        for raw_graph in raw_task["graph_array"]:
            dst_graph = pick_data_for_task_for_figure(task_cfg, raw_graph, axles_cfgs)
            dst_task["graph_array"].append(dst_graph)
        #
        if dst_task.get("save_plot_json") is not None:
            save_path = utils.prepare_save_path(
                save_name=dst_task.get("save_plot_json"),
                save_dir=task_cfg.get("data_save_dir")
            )
            with open(save_path, "w") as f:
                json.dump(dst_task, fp=f, indent=4)
        #
        return dst_task
    except Exception as e:
        log.error("Exception = `%s`", repr(e))
        raise e


def plot_axles_data(fig, gs, dst_axles):
    subpos = gs[dst_axles["suby"], dst_axles["subx"]]
    ax = fig.add_subplot(subpos)
    ax.set_title(dst_axles["title"], fontproperties=chsfont)
    ax.set_xlabel(dst_axles["xlabel"], fontproperties=chsfont)
    ax.set_ylabel(dst_axles["ylabel"], fontproperties=chsfont)
    #
    for dst_line in dst_axles["line_array"]:
        p = ax.plot(dst_line["xlist"], dst_line["ylist"], '-*', label=dst_line["label"])
        if dst_axles.get("show_point_label") is True:
            for idx, val in enumerate(dst_line["tlist"]):
                x,y = dst_line["xlist"][idx], dst_line["ylist"][idx]
                ax.annotate(val, xy=(x, y), color=p[0].get_color())
    #
    ax.legend(fontsize=10, loc=0, prop=chsfont)
    ax.grid(True)
    return ax


def plot_figure_data(task_cfg, dst_graph):
    try:
        assert dst_graph["data_format"] == "plot_data"
        log.info(json.dumps(dst_graph, indent=4))
        #
        figsize = (dst_graph["width"], dst_graph["height"])
        figure = plt.figure(dst_graph["title"], figsize=figsize)
        gs = gridspec.GridSpec(dst_graph["subh"], dst_graph["subw"])
        for dst_axles in dst_graph["axles_array"]:
            plot_axles_data(figure, gs, dst_axles)
        figure.tight_layout()
        #
        if dst_graph.get("save_pic") is not None:
            save_path = utils.prepare_save_path(
                save_name=dst_graph.get("save_pic"),
                save_dir=task_cfg.get("data_save_dir")
            )
            figure.savefig(save_path)
        if dst_graph.get("show_pic") is True:
            plt.show(figure)
        return figure
    except Exception as e:
        log.error("Exception = `%s`", repr(e))
        raise e


def plot_task_data(dst_task):
    assert dst_task["data_format"] == "plot_data"
    for graph_data in dst_task["graph_array"]:
        plot_figure_data(dst_task, graph_data)


def _main_test(json_file):
    try:
        with open(json_file, "r") as f:
            raw_task_data = json.loads(f.read())
            dst_task_data = pick_data_for_task(raw_task_data)
            plot_task_data(dst_task_data)
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
    logger.log2stdout(module_name, logfmt=logger.DEFAULT_LOGFMT)

if __name__ == "__main__":
    import sys
    import time
    reload(sys)
    sys.setdefaultencoding('utf-8')     # <! 中文设置
    timestr = time.strftime('%y%m%d_%H%M', time.localtime(time.time()))
    #
    _create_module_log()
    parser = _main_parser()
    (opt, args) = parser.parse_args()
    _main_test(opt.json_file)
    log.info("done")