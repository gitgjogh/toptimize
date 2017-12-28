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
    choose the best encoding size
"""

import logging
import sys
import time
from video import info,trans,score

module_name = "toptimize"
log = logging.getLogger(module_name)


# class CSizeOpt:
#     def __init__(self):
#         self.original = trans.Format()
#         self.anchor = trans.Format()
#         self.better = trans.Format()
#         self.b_use_better = False
#         self.search_size = []
#
#     def get_anchor_rd(self):
#         pass


def search_crf_in_other_size(original, anchor, size):
    """
    search for a encoding crf in other size that has the same video quality
    as the anchor out video.
    :param original: original video <trans.Format>
    :param anchor: anchor out video <trans.Format>
    :param size: <trans.CTransSize>
    :return: <trans.Format>
    """
    if anchor.vmaf is None or anchor.vmaf == 0:
        log.error("no vmaf score for the anchor video")
        return None
    if size == anchor.size:
        return None

    crf1 = anchor.crf
    trans1 = trans.Format(size=size, crf=crf1)
    score.trans_and_get_score(original, trans1)

    target_crf = None
    crf_delta = 1 if size > anchor.size else - 1
    while trans1.crf in range(20, 37):
        ''' search in [20, crf1] or [crf1 ,37] 
        '''
        crf2 = trans1.crf + crf_delta
        trans2 = trans.Format(size=size, crf=crf2)
        score.trans_and_get_score(original, trans2)
        if (trans1.vmaf - anchor.vmaf) * (trans2.vmaf - anchor.vmaf) <= 0:
            '''
            (crf0 - crf1) / (crf1 - crf2) = (vmaf0 - vmaf1) / (vmaf1 - vmaf2)
            crf0 = crf1 + (crf1 - crf2) * (vmaf0 - vmaf1) / (vmaf1 - vmaf2)
            '''
            target_crf = trans1.crf + (trans1.crf - trans2.crf) * (anchor.vmaf - trans1.vmaf) / (trans1.vmaf - trans2.vmaf)
            break
        trans1 = trans2

    if target_crf is not None:
        candi = trans.Format(size=size, crf=target_crf)
        score.trans_and_get_score(original, candi)
        log.info("search crf @" + str(size) + " = " + str(candi))
        return candi
    return None


def search_better_size(original, anchor, search_size=[]):
    """
    search for a encoding size that has lower bit-rate but keep the same video quality
    as the anchor out video.
    :param original: original video <trans.Format>
    :param anchor: anchor out or target (to be out) video <trans.Format>
    :param search_size: candidated video size to be searched <[trans.CTransSize,...]>
    :return: out video that has lower bit-rate but keep the same video quality
    as the anchor out video <trans.CTransSize>
    """
    score.trans_and_get_score(original, anchor)
    better1 = anchor
    b_get_better = False

    for size in search_size:
        better2 = search_crf_in_other_size(original, anchor, size)
        if better2 is not None and better1.br < better2.br:
            better1 = better2
            b_get_better = True

    if b_get_better:
        log.info("better = " + str(better1))

    return better1 if b_get_better is True else None


def sizeopt_test(path, anchor_size, anchor_crf, search_size):
    mi = info.Media(path, probe=True)
    source_fmt = trans.Format().from_mediainfo(mi)
    anchor_res = trans.TSize().from_string(anchor_size)
    anchor_fmt = trans.Format(size=anchor_res, crf=anchor_crf)
    search_res = [trans.TSize().from_string(size) for size in search_size.split(",")]
    return search_better_size(source_fmt, anchor_fmt, search_res)


def _main_parser():
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-i", "--input", dest="input", help=r"input video path")
    parser.add_option("-s", "--anchor-size", dest="anchor_size", help=r"anchor shorter size")
    parser.add_option("-q", "--anchor-crf", dest="anchor_crf", help=r"anchor crf")
    parser.add_option("-d", "--search-size", dest="search_size", help=r"candidate shorter size separated by comma")
    return parser


def _create_module_log():
    import logger
    logger.log2file(module_name + ".log", logging.DEBUG)
    logger.log2stdout()


if __name__ == "__main__":
    reload(sys)
    sys.setdefaultencoding('utf-8')     # <! 中文设置
    timestr = time.strftime('%y%m%d_%H%M', time.localtime(time.time()))
    #
    _create_module_log()
    parser = _main_parser()
    (opt, args) = parser.parse_args()
    sizeopt_test(opt.input, opt.anchor_size, opt.anchor_crf, opt.search_size)
    log.info("done")
