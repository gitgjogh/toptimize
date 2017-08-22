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
    video transcoding
"""

import logging
import os
import subprocess
import info
import cfg.tools

FFMPEG = cfg.tools.ffmpeg
module_name = "v.trans"
log = logging.getLogger(module_name)


class TSize:
    def __init__(self, w=0, h=0, shorter=0, string=None):
        self.w = int(w)
        self.h = int(h)
        self.shorter = int(shorter)
        if string is not None:
            self.from_string(string)

    def __cmp__(self, other):
        return self.w * self.h - other.w * other.h

    def __str__(self):
        return str(self.__dict__)

    def s(self):
        return self.w * self.h

    def wxh(self):
        return "{:d}x{:d}".format(self.w, self.h)

    def tostring(self, sep="x"):
        return "{:d}{:s}{:d}".format(self.w, sep, self.h)

    def from_string(self, string):
        import re
        self = TSize()
        if re.match(r'\d+[x:]\d+', string):
            s = string.split(r'[x:]', string)
            self.w, self.h = s[0], s[1]
        elif re.match(r'\d+[pP]', string):
            self.shorter = int(string[:-1])
        else:
            log.error(string + " is not valid size pattern")
        return self

    def get_shorter(self):
        return self.w if self.w < self.h else self.h

    def shorter2wxh(self, isize):
        """
        update size according to iszie in case shorter is used
        :param isize: <TSize>
        :return:
        """
        if (self.w * self.h == 0) and (self.shorter != 0):
            if isize.w < isize.h:
                self.w = self.shorter
                self.h = isize.h * self.w / isize.w
            else:
                self.h = self.shorter
                self.w = isize.w * self.h / isize.h
            self.w = self.w / 4 * 4
            self.h = self.h / 4 * 4
        return self


class Format:
    def __init__(self, path=None, size=TSize(), crf=0, br=0, psnr=0, ssim=0, vmaf=0, probe=False):
        self.path = path
        self.size = size
        self.crf = float(crf)
        self.br = int(br)
        self.psnr = float(psnr)
        self.ssim = float(ssim)
        self.vmaf = float(vmaf)
        self.info = None
        if probe is True:
            self.probe_info()

    def __str__(self):
        return str({k: str(v) for k, v in self.__dict__.items()})

    def from_mediainfo(self, mi):
        self.path = mi.path
        self.size = TSize(mi.video.w, mi.video.h)
        self.br = mi.video.br
        self.info = mi
        return self

    def probe_info(self):
        self.from_mediainfo(info.Media(path=self.path, probe=True))

    def get_save_name(self, basename, ext="mp4"):
        suffix = "{wxh:s}_crf_{crf:f}".format(wxh=self.size.wxh(), crf=self.crf)
        self.path = basename + "." + suffix + "." + ext
        return self.path

def run_command(cmdargs):
    """
    video transcoding
    :return: process returncode
    """
    try:
        log.info("subprocess = " + ' '.join(cmdargs))
        process = subprocess.Popen(cmdargs, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
        output, error = process.communicate()
        log.debug("\n" + output + error)
        if process.returncode:
            log.error("error[{:d}]: \n{:s}".format(process.returncode, error))
        return process.returncode
    except Exception as e:
        log.error("Exception = `%s`", str(e))
        return -1
    return 0

def trans_by_ioparam(input, iparam, oparam, output):
    """
    video transcoding
    :param original: original video info <Format>
    :param iparam: parameters passed to ffmpeg for input [...<string>...]
    :param oparam: parameters passed to ffmpeg for output [...<string>...]
    :param save_path: path for out video <string>
    :return: process returncode
    """
    command = [FFMPEG, "-hide_banner"] + iparam + ["-i", input] + oparam + [output]
    return run_command(command)


def to_264_by_size_crf(original, tsize, crf, save_path=None, _iparam=[]):
    """
    :return: path for the transcoded video
    """
    tsize.shorter2wxh(original.size)
    iparam = "-y -threads 0".split(" ") + _iparam
    oparam = "-s {w:d}x{h:d} -crf {crf:f}".format(w=tsize.w, h=tsize.h, crf=crf).split(" ")
    oparam += "-c:v libx264 -preset veryslow -vcodec libx264".split(" ")
    oparam += ["-x264opts", "psy=0:ref=5:keyint=90:min-keyint=9:chroma_qp_offset=0:aq_mode=2:threads=36:lookahead-threads=4"]
    oparam += "-maxrate 2500k -bufsize 5M".split(" ")
    oparam += "-async 1 -b:a 48k -ar 44100 -ac 2 -acodec libfdk_aac".split(" ")
    oparam += "-movflags faststart".split(" ")
    if save_path is None:
        save_path = os.path.basename(original.path) + ".[" + tsize.wxh() + "].[" + str(crf) + "].mp4"
    ret = trans_by_ioparam(original.path, iparam, oparam, save_path)
    if ret is not 0:
        log.error("transcoding failed")
        return None
    return save_path


def to_yuv_by_size(original, tsize, save_path=None, _iparam=[], _oparam=[]):
    """
    :return: path for the raw yuv
    """
    tsize.shorter2wxh(original.size)
    iparam = "-y -threads 0".split(" ") + _iparam
    oparam = ["-an", "-s", tsize.wxh()] + _oparam + ["-f", "rawvideo"]
    if save_path is None:
        save_path = os.path.basename(original.path) + ".[" + tsize.wxh() + "].yuv"
    ret = trans_by_ioparam(original.path, iparam, oparam, save_path)
    if ret is not 0:
        log.error("transcoding failed")
        return None
    return save_path


def _main_test(path, size, crf):
    ori_fmt = Format(path, probe=True)
    tsize = TSize().from_string(size)
    #log.info("ori=" + str(ori_fmt))
    #log.info("tsize=" + str(tsize))
    iparam = "-t 6".split()
    avc_path = to_264_by_size_crf(ori_fmt, tsize, crf, _iparam=iparam)
    yuv_path = to_yuv_by_size(ori_fmt, tsize, _iparam=iparam)
    dis_fmt = info.Media(avc_path, probe=True)
    log.info("ori_fmt = " + str(ori_fmt))
    log.info("dis_fmt = " + str(dis_fmt))
    log.info("dis_yuv = " + str(yuv_path))


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
    logger.log2stdout(module_name)


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