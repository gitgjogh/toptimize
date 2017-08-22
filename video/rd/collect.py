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
    video transcoding and then collect video quality scores
"""

import os
import json
import time
import copy
import logging
import subprocess
import video.info as info
import video.trans as trans
import video.score as score
import cfg.tools


FFMPEG = cfg.tools.ffmpeg
module_name = "v.rd.collect"
log = logging.getLogger(module_name)


def _append_param_to_name(name, param, value, sep="-"):
    cat = name + ".[" + param + sep + value + "]"
    return cat


def collect_point_data(graph_cfg, line_cfg, point_cfg):
    raw_point_data = {"label": point_cfg["label"]}
    input = graph_cfg["input"]
    output = os.path.basename(input)
    #
    # video transcoding
    iparam = line_cfg["input_param"]
    oparam = line_cfg["output_param"]
    output = _append_param_to_name(output, "label", line_cfg["label"])
    for param, value in point_cfg["params"].iteritems():
        iparam = iparam.replace("%" + param + "%", str(value))
        oparam = oparam.replace("%" + param + "%", str(value))
        output = _append_param_to_name(output, param, str(value))
    output += ".mp4"
    start_time = time.time()
    ret = trans.trans_by_ioparam(input, iparam.split(), oparam.split(), output)
    trans_time = time.time() - start_time
    #
    raw_point_data.update({
        "iparam": iparam,
        "oparam": oparam,
        "output": output,
        "trans_time": trans_time,
        "rate": 0,
        "psnr": 0.0, "ssim": 0.0, "vmaf": 0.0
    })
    # video quality evaluation
    if ret == 0:
        ori_fmt = trans.Format(input, probe=True)
        dis_fmt = trans.Format(output, probe=True)
        cmp_res = line_cfg.get("cmp_res")
        cmp_frm = line_cfg.get("cmp_frames")
        psnr, ssim, vmaf = score.get_yuv_score(ori_fmt, dis_fmt, cmp_res, cmp_frames=cmp_frm)
        raw_point_data.update({
            "rate": dis_fmt.br,
            "psnr": psnr, "ssim": ssim, "vmaf": vmaf
        })
    else:
        log.error("trans failed (" + str(ret) + ")")
    #
    return raw_point_data


def collect_line_data(graph_cfg, line_cfg, point_cfgs):
    raw_line = copy.deepcopy(line_cfg)
    raw_line.update({
        "point_array": []
    })
    #
    for point_cfg in point_cfgs:
        raw_point_data = collect_point_data(graph_cfg, line_cfg, point_cfg)
        raw_line["point_array"].append(raw_point_data)
    return raw_line


def collect_figure_data(graph_cfg, line_cfgs, point_cfgs):
    raw_graph = copy.deepcopy(graph_cfg)
    raw_graph.update({
        "data_format": "raw_data",
        "line_array": []
    })
    #
    for line_cfg in line_cfgs:
        raw_line = collect_line_data(graph_cfg, line_cfg, point_cfgs)
        raw_graph["line_array"].append(raw_line)
    #
    if raw_graph.get("save_raw_json") is not None:
        with open(raw_graph.get("save_raw_json"), "w") as f:
            json.dump(raw_graph, fp=f, indent=4)
    #
    return raw_graph


def collect_task_data(task_cfg):
    try:
        assert task_cfg["data_format"] == "cfg_data"
        raw_task = copy.deepcopy(task_cfg)
        raw_task.update({
            "data_format": "raw_data",
            "graph_array": []
        })
        #
        graph_cfgs = task_cfg["graph_cfg_list"]
        line_cfgs = task_cfg["line_cfg_list"]
        point_cfgs = task_cfg["point_cfg_list"]
        #
        for graph_cfg in graph_cfgs:
            raw_graph = collect_figure_data(graph_cfg, line_cfgs, point_cfgs)
            raw_task["graph_array"].append(raw_graph)
        #
        print raw_task.get("save_raw_json")
        if raw_task.get("save_raw_json") is not None:
            with open(raw_task.get("save_raw_json"), "w") as f:
                json.dump(raw_task, fp=f, indent=4)
        #
        return raw_task
    except Exception as e:
        log.error("Exception = `%s`", repr(e))
        raise e


def _main_test(input, output):
    try:
        with open(input, "r") as f:
            task_cfg = json.loads(f.read())
        raw_task = collect_task_data(task_cfg)
        with open(output, "w") as f:
            f.write(json.dumps(raw_task, indent=4))
    except Exception as e:
        log.error("Exception = `%s`", repr(e))
        raise e


def _main_parser():
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-i", "--input", dest="input", help=r"")
    parser.add_option("-o", "--output", dest="output", help=r"")
    return parser


def _create_module_log():
    import logger
    logger.log2file(module_name + ".log", logging.DEBUG)
    logger.log2stdout(None, logfmt=logger.DEFAULT_LOGFMT)


if __name__ == "__main__":
    import sys,time
    reload(sys)
    sys.setdefaultencoding('utf-8')     # <! 中文设置
    timestr = time.strftime('%y%m%d_%H%M', time.localtime(time.time()))
    #
    _create_module_log()
    parser = _main_parser()
    (opt, args) = parser.parse_args()
    _main_test(opt.input, opt.output)
    log.info("done")
