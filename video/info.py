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
    probe video infos
"""

import os,time,sys
import subprocess
import json
import logging
import cfg.tools

FFPROBE = cfg.tools.ffprobe
module_name = "v.info"
log = logging.getLogger(module_name)


def ffprobe_test(ffprobe):
    import subprocess
    command = ffprobe + " -version"
    process = subprocess.Popen(command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
    output, error = process.communicate()
    #
    if process.returncode:
        log.error("Fail to run \"{:s}\"".format(command))
        log.error("[[[[\n", error, "]]]]")
        return False
    return True


def probe_info(video):
    # incase of netstream
    '''
    if not os.path.exists(video):
        log.error("Can't found video [{:s}]".format(video))
        return None
    '''
    try:
        command = [FFPROBE] + "-hide_banner -show_streams -of json".split() + [video]
        log.debug("subprocess = " + str(command))
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
        output, error = process.communicate()
        if process.returncode:
            log.error("error[{:d}]: \n{:s}".format(process.returncode, error))
            return None
        log.debug("\n" + output + error)
        vinfo = json.loads(output)
        return vinfo
    except Exception as e:
        log.error("Exception = `%s`", str(e));
        raise e

    return None


class Audio:
    def __init__(self):
        self.codec = ""
        self.ar = 0
        self.ch = 0
        self.br = 0
        self.ts = 0

    def __str__(self):
        return str({k: str(v) for k, v in self.__dict__.items()})


class Video:
    def __init__(self):
        self.codec = ""
        self.w = 0
        self.h = 0
        self.br = 0
        self.frame = 0
        self.fps = 0.0
        self.ts = 0

    def __str__(self):
        return str({k: str(v) for k, v in self.__dict__.items()})


class Media:
    def __init__(self, path=None, probe=False):
        self.path = path
        self.t = 0.0                # time in ms
        self.audio = Audio()
        self.video = Video()
        self.probe_obj = None

        if path is not None and probe is not False:
            self.probe_info()

    def __str__(self):
        return str({"video": str(self.video), "audio": str(self.audio)})

    def _set_ffprobe_audio(self, stream_obj):
        self.audio.codec = stream_obj.get("codec_name")
        self.audio.ar = stream_obj.get("sample_rate")
        self.audio.ch = stream_obj.get("channels")
        self.audio.br = stream_obj.get("bit_rate")
        self.audio.ts = stream_obj.get("duration")

    def _set_ffprobe_video(self, stream_obj):
        self.video.codec = stream_obj.get("codec_name")
        self.video.w = stream_obj.get("coded_width")
        self.video.h = stream_obj.get("coded_height")
        self.video.br = stream_obj.get("bit_rate")
        self.video.frames = stream_obj.get("nb_frames")
        self.video.fps = stream_obj.get("r_frame_rate")
        self.video.ts = stream_obj.get("duration")

    def _set_ffprobe_info(self, ffprobe_obj):
        """
        set media info from a ffprobe object, see data_format/ffprobe_example.json
        """
        get_video = False
        get_audio = False
        for strm in ffprobe_obj.get("streams"):
            if not get_video and strm.get("codec_type", "") == "video":
                self._set_ffprobe_video(strm)
            if not get_audio and strm.get("codec_type", "") == "audio":
                self._set_ffprobe_audio(strm)

    def probe_info(self):
        self.probe_obj = probe_info(self.path)
        if self.probe_obj is not None:
            self._set_ffprobe_info(self.probe_obj)
        else:
            log.error("fail to probe " + self.path)
        return self.probe_obj


def _main_parser():
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-v", "--video", dest="video", help=r"video path")
    parser.add_option("-i", "--input", dest="video", help=r"video path")
    return parser


def _create_module_log():
    import logger
    logger.log2file(module_name + ".log", logging.INFO)
    logger.log2stdout(module_name)

if __name__ == "__main__":
    reload(sys)
    sys.setdefaultencoding('utf-8')     # <! 中文设置
    timestr = time.strftime('%y%m%d_%H%M', time.localtime(time.time()))
    #
    _create_module_log()
    parser = _main_parser()
    (opt, args) = parser.parse_args()
    mi = Media(opt.video)
    probe_obj = mi.probe_info()
    print json.dumps(probe_obj, indent=4)
    print str(mi)
    log.info("done")
