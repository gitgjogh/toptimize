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
    evaluate video quality for videos already transcoded
"""

import copy
import json
import logging
import utils
import trans
import score

module_name = "v.rd.collect"
log = logging.getLogger(module_name)


def _dict_copy(copydict, preload={}, overwrite={}):
    ret = copy.deepcopy(preload)
    ret.update(copydict)
    ret.update(overwrite)
    return ret


def collect_trans_quality(task_cfg, seq_cfg, trans_cfg):
    """
    quality evaluation for transcoded video
    """
    trans_data = copy.deepcopy(trans_cfg)
    try:
        ori_path = seq_cfg["reference"]["path"]
        dis_path = trans_cfg["path"]
        ori_fmt = trans.Format(ori_path, probe=True)
        dis_fmt = trans.Format(dis_path, probe=True)
        cmp_res = trans_cfg.get("cmp_res", seq_cfg.get("cmp_res"))
        cmp_frm = trans_cfg.get("cmp_frames", seq_cfg.get("cmp_frames"))
        psnr, ssim, vmaf = score.get_yuv_score(
            ori_fmt, dis_fmt, cmp_res,
            cmp_frames=cmp_frm,
            save_dir=seq_cfg.get("yuv_save_dir"))
        trans_data.update({
            "rate": dis_fmt.br,
            "psnr": psnr, "ssim": ssim, "vmaf": vmaf
        })
    except Exception as e:
        log.error("Exception = `%s`", repr(e))
        raise e
    #
    return trans_data


def collect_seq_data(task_cfg, seq_cfg):
    seq_data = copy.deepcopy(seq_cfg)
    seq_data.update({
        "trans_list": []
    })
    _preload = task_cfg.get("trans_default", {})
    _overwrite = task_cfg.get("trans_overwrite", {})
    for trans_item in seq_cfg["trans_list"]:
        trans_cfg = _dict_copy(trans_item, _preload, _overwrite)
        trans_data = collect_trans_quality(task_cfg, seq_cfg, trans_cfg)
        seq_data["trans_list"].append(trans_data)
    return seq_data


def collect_task_data(task_cfg):
    assert task_cfg["data_format"] == "video.eval.task.config"
    task_data = copy.deepcopy(task_cfg)
    task_data.update({
        "data_format": "video.eval.task.result",
        "seq_list": []
    })
    #
    _preload = task_cfg.get("seq_preload", {})
    _overwrite = task_cfg.get("seq_overwrite", {})
    for seq_item in task_cfg["seq_list"]:
        seq_cfg = _dict_copy(seq_item, _preload, _overwrite)
        seq_data = collect_seq_data(task_cfg, seq_cfg)
        task_data["seq_list"].append(seq_data)
    return task_data


def run_task(task_cfg_file):
    try:
        task_cfg = None
        with open(task_cfg_file, "r") as f:
            task_cfg = json.loads(f.read())
        if task_cfg is None:
            log.error("can't load task config")
        #
        task_data = collect_task_data(task_cfg)
        #
        if task_cfg.get("save_result_json") is not None:
            save_path = utils.prepare_save_path(
                save_name=task_cfg.get("save_result_json"),
                save_dir=task_cfg.get("data_save_dir")
            )
            with open(save_path, "w") as f:
                json.dump(task_data, fp=f, indent=4)
    except Exception as e:
        log.error("Exception = `%s`", repr(e))
        raise e


def _main_test(input):
    run_task(input)


def _main_parser():
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-i", "--input", dest="input", help=r"input json")
    # parser.add_option("-o", "--output", dest="output", help=r"output result")
    # parser.add_option("-f", "--format", dest="format", help=r"result format")
    return parser


def _create_module_log():
    import logger
    logger.log2file(module_name + ".log", logging.DEBUG)
    logger.log2stdout(None, logging.INFO)


if __name__ == "__main__":
    import sys,time
    reload(sys)
    sys.setdefaultencoding('utf-8')     # <! 中文设置
    timestr = time.strftime('%y%m%d_%H%M', time.localtime(time.time()))
    _create_module_log()
    #
    parser = _main_parser()
    (opt, args) = parser.parse_args()
    # _main_test(opt.input, opt.output, opt.format)
    _main_test(opt.input)
    log.info("#### done ####")