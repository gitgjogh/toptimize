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

import json
import logging
import re
import subprocess
import info
import trans
import cfg.tools

FFMPEG = cfg.tools.ffmpeg
RUN_VMAF = cfg.tools.run_vmaf
RUN_VMAF_PY = cfg.tools.run_vmaf_py
module_name = "v.score"
log = logging.getLogger(module_name)


def _get_psnr_ssim_from_command(cmd_args):
    """
    run @cmd_args which produce psnr and ssim, then filter the result
    :param cmd_args: "ffmpeg -i input1 -i input2 -lavfi psnr;[0:v][1:v]ssim -f null -"
    :return: psnr, ssim, ssim2
    """
    psnr, ssim, ssim2 = 0, 0, 0

    f_regex = r"([.0-9]+|inf)"
    psnr_regex = re.compile(
        r"\[Parsed_psnr_\d+ @ 0x[0-9a-f]+\] PSNR "
        + r"y:" + f_regex + " u:" + f_regex + " v:" + f_regex + " "
        + "average:(?P<psnr>[.0-9]+) .*")
    ssim_regex = re.compile(
        r"\[Parsed_ssim_\d+ @ 0x[0-9a-f]+\] SSIM "
        + r"Y:[.0-9]+ \(" + f_regex + "\) "
        + r"U:[.0-9]+ \(" + f_regex + "\) "
        + r"V:[.0-9]+ \(" + f_regex + "\) "
        + r"All:(?P<ssim>[.0-9]+) \((?P<ssim2>[.0-9]+)\)")

    try:
        process = subprocess.Popen(cmd_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   universal_newlines=True, shell=False)
        log.info("subprocess = " + ' '.join(cmd_args))
        while True:
            # ffmepg默认输出到stderr，这是个阻塞调用
            line = process.stderr.readline()
            if process.poll() is not None:
                log.info("...Process Ending...")
                break
            psnr_match = psnr_regex.search(line)
            ssim_match = ssim_regex.search(line)
            if psnr_match:
                psnr_dict = psnr_match.groupdict()
                psnr = float(psnr_dict["psnr"])
            if ssim_match:
                ssim_dict = ssim_match.groupdict()
                ssim = float(ssim_dict["ssim"])
                ssim2 = float(ssim_dict["ssim2"])
        if process.returncode:
            log.error("ffmpeg exit with error code " + str(process.returncode))
    except Exception as e:
        log.error("Exception = " + str(e))

    if psnr * ssim == 0:
        log.error("psnr/ssim == 0, please check psnr/ssim regex pattern ")
        log.error("psnr_regex=" + psnr_regex)
        log.error("ssim_regex=" + ssim_regex)

    log.info("psnr="+str(psnr)+", ssim="+str(ssim))
    return psnr, ssim


def _get_vmaf_from_command(cmd_args):
    """
    run @command_args which produce psnr and ssim, then filter the result
    :param command_arg: "run_vmaf yuv420p w h input1 input2 ..."
    :return: vmaf
    """
    try:
        log.info("subprocess = " + ' '.join(cmd_args))
        process = subprocess.Popen(cmd_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
        output, error = process.communicate()
        log.debug("\n" + output + error)
        if process.returncode:
            log.error("error[{:d}]: \n{:s}".format(process.returncode, error))
            return 0
        vmaf_obj = json.loads(output)
        vmaf = vmaf_obj["aggregate"]["VMAF_score"]
        return float(vmaf)
    except Exception as e:
        log.error("Exception = " + str(e))
    return 0


# def get_vmaf_score(original, out, cmp_res=None):
#     """
#     :param original: original video info <trans.Format>
#     :param out: out video info <trans.Format>
#     :param cmp_res: compare resolution <trans.CTransSize>. If None, use original resolution.
#     :return: netflix vmaf score <double>
#     """
#     vmaf = 0
#     return vmaf
#
#
# def get_psnr_ssim(original, out, cmp_res=None):
#     """
#     :param original: original video info <trans.Format>
#     :param out: out video info <trans.Format>
#     :param cmp_res: compare resolution <trans.CTransSize>. If None, use original resolution.
#     :return: (psnr,ssim) <double, double>
#     """
#     cmd_args = ["ffmpeg", "-i", original.path, "-s", str(cmp_res), "-i", out.path, "-s", str(cmp_res)]
#     cmd_args += ["-lavfi", "psnr;[0:v][1:v]ssim", "-f", "null", "-"]
#     return _get_psnr_ssim_from_command(cmd_args)


def get_yuv_score(ref_fmt, dis_fmt, cmp_res=None, cmp_frames=None, has_psnr=True, has_vmaf=True):
    """
    decoding to yuv and then calculate quality score like psnr,ssim,vmaf
    :param ref_fmt: original video info <trans.Format>
    :param dis_fmt: transcoded video info <trans.Format>
    :param cmp_res: compare resolution <trans.CTransSize>. If None, use original resolution.
    :return: (psnr,ssim) <double, double>
    """
    cmp_res = ref_fmt.size if (cmp_res is None or cmp_res.s() == 0) else cmp_res
    oparam = ["-vframes", str(cmp_frames)] if (cmp_frames is not None) else []
    ref_yuv = trans.to_yuv_by_size(ref_fmt, cmp_res, _oparam=oparam)
    dis_yuv = trans.to_yuv_by_size(dis_fmt, cmp_res, _oparam=oparam)
    if ref_yuv is None or dis_yuv is None:
        log.error("failed to get"
                  + (" ref_yuv" if ref_yuv is None else "")
                  + (" dis_yuv" if dis_yuv is None else ""))
        return 0, 0, 0

    psnr, ssim, vmaf = 0, 0, 0

    # get psnr and ssim
    if has_psnr is True:
        cmd_args = [FFMPEG]
        cmd_args += "-f rawvideo -pix_fmt yuv420p -s".split(" ") + [cmp_res.wxh(), "-i", ref_yuv]
        cmd_args += "-f rawvideo -pix_fmt yuv420p -s".split(" ") + [cmp_res.wxh(), "-i", dis_yuv]
        cmd_args += ["-lavfi", "psnr;[0:v][1:v]ssim", "-f", "null", "-"]
        psnr, ssim = _get_psnr_ssim_from_command(cmd_args)

    # get vmaf
    if has_vmaf is True:
        vmaf_args = ["python", RUN_VMAF, "yuv420p", str(cmp_res.w), str(cmp_res.h)]
        vmaf_args += [ref_yuv, dis_yuv, "--out-fmt", "json"]
        vmaf = _get_vmaf_from_command(vmaf_args)
    #
    return psnr, ssim, vmaf


def trans_and_get_score(ori_fmt, dis_fmt):
    """
    make video transcoding according to @trans, and then update video quality scores
    :param original: original video info <trans.Format>
    :param trans: transcoded video info <trans.Format>
    :return: @trans <trans.Format>
    """
    dis_fmt.path = trans.to_264_by_size_crf(ori_fmt, dis_fmt.size, dis_fmt.crf)
    if dis_fmt.path is not None:
        dis_fmt.probe_info()
        dis_fmt.psnr, dis_fmt.ssim, dis_fmt.vmaf = get_yuv_score(ori_fmt, dis_fmt)
        log.info("transcoded = " + str(dis_fmt))
    return dis_fmt


def _main_test(path, size, crf):
    ori_fmt = trans.Format(path, probe=True)
    tsize = trans.TSize().from_string(size)
    dis_fmt = trans.Format(size=tsize, crf=crf)
    trans_and_get_score(ori_fmt, dis_fmt)
    log.info("ori_fmt = " + str(ori_fmt))
    log.info("dis_fmt = " + str(dis_fmt))


def _main_parser():
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-i", "--input", dest="input", help=r"input video path")
    parser.add_option("-s", "--size", dest="size", help=r"wxh or ?p (ie. 480p)")
    parser.add_option("-q", "--crf", dest="crf", help=r"crf")
    return parser


def _create_module_log():
    import logger
    logger.log2file(module_name + ".log", logging.DEBUG)
    logger.log2stdout()


if __name__ == "__main__":
    import sys,time
    reload(sys)
    sys.setdefaultencoding('utf-8')     # <! 中文设置
    timestr = time.strftime('%y%m%d_%H%M', time.localtime(time.time()))
    _create_module_log()
    #
    parser = _main_parser()
    (opt, args) = parser.parse_args()
    _main_test(opt.input, opt.size, float(opt.crf))
    log.info("#### done ####")