#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2017 Christoph Reiter
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import io
import os
import sys
import codecs

from hypothesis import given, find, settings

from hypothesis_fspaths import fspaths


PY3 = sys.version_info[0] == 3
text_type = type(u"")
encoding = sys.getfilesystemencoding()
is_win = (os.name == "nt")


def norm_encoding(name):
    """Normalizes an encoding name"""

    return codecs.lookup(name).name


def single_byte_full_encoding(encoding):
    """Whether the encoding can decode all byte values (e.g. latin1)"""

    if PY3:
        bytes_ = map(lambda i: bytes([i]), range(0, 256))
    else:
        bytes_ = map(chr, range(0, 256))

    for byte in bytes_:
        try:
            byte.decode(encoding)
        except UnicodeDecodeError:
            return False
    return True


@given(fspaths())
@settings(max_examples=1000)
def test_open(path):
    try:
        with open(path):
            pass
    except IOError:
        pass

    try:
        io.open(path)
    except IOError:
        pass


def test_find():

    def fspath(p):
        try:
            return os.fspath(p)
        except AttributeError:
            return p

    def only_if(condition):
        def wrap(func):
            def wrapper(*args):
                if not condition:
                    return True
                return func(*args)
            return wrapper
        return wrap

    def is_empty(p):
        p = fspath(p)
        return not p

    def is_not_too_short(p):
        p = fspath(p)
        return len(p) > 20

    def is_bytes(p):
        p = fspath(p)
        return isinstance(p, bytes)

    def is_text(p):
        p = fspath(p)
        return isinstance(p, text_type)

    @only_if(not is_win and PY3)
    def text_with_surrogateescape(p):
        p = fspath(p)
        if not isinstance(p, text_type):
            return False

        try:
            p.encode(encoding)
        except UnicodeEncodeError:
            p.encode(encoding, "surrogateescape")
            return True
        else:
            return False

    @only_if(is_win and PY3)
    def text_with_surrogatepass(p):
        p = fspath(p)
        if not isinstance(p, text_type):
            return False

        try:
            p.encode("utf-8")
        except UnicodeEncodeError:
            p.encode("utf-8", "surrogatepass")
            return True
        else:
            return False

    @only_if(not single_byte_full_encoding(encoding) and not is_win)
    def bytes_has_non_decodable(p):
        p = fspath(p)
        if not isinstance(p, bytes):
            return False

        try:
            p.decode(encoding)
        except UnicodeDecodeError:
            return True
        return False

    @only_if(not is_win and PY3 and
             norm_encoding("utf-8") == norm_encoding(encoding))
    def text_surrogates_merge_in_bytes_form(p):
        p = fspath(p)
        if not isinstance(p, text_type):
            return False

        return p.encode(encoding, "surrogateescape").decode(
            encoding, "surrogateescape") != p

    # utf-16 + surrogatepass is broken under Python 3.3
    @only_if(is_win and PY3 and sys.version_info[:2] != (3, 3))
    def text_contains_unmerged_surrogates_pairs(p):
        p = fspath(p)
        if not isinstance(p, text_type):
            return False

        return p.encode("utf-16-le", "surrogatepass").decode(
            "utf-16-le", "surrogatepass") != p

    @only_if(hasattr(os, "PathLike"))
    def is_pathlike(p):
        if isinstance(p, (bytes, text_type)):
            return False
        os.fspath(p)
        return True

    find(fspaths(), is_bytes)
    find(fspaths(), is_text)
    find(fspaths(), is_empty)
    find(fspaths(), is_not_too_short)
    find(fspaths(), bytes_has_non_decodable)
    find(fspaths(), text_with_surrogateescape)
    find(fspaths(), text_with_surrogatepass)
    find(fspaths(), text_contains_unmerged_surrogates_pairs)
    find(fspaths(), text_surrogates_merge_in_bytes_form)
