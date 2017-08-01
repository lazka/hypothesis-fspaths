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

import os
import sys

from hypothesis.strategies import composite, binary, one_of, characters, \
    text, permutations
from hypothesis.errors import InvalidArgument

PY3 = (sys.version_info[0] == 3)


class _PathLike(object):
    """A class implementing the os.PathLike protocol available since Python
    3.6.

    See https://www.python.org/dev/peps/pep-0519/ for more details.
    """

    def __init__(self, value):
        self._value = value

    def __fspath__(self):
        return self._value

    def __repr__(self):
        return 'pathlike(%r)' % self._value


@composite
def fspaths(draw, allow_pathlike=None, allow_existing=False):
    """A strategy which generates filesystem path values.

    The generated values include everything which the builtin
    :func:`python:open` function accepts i.e. which won't lead to
    :exc:`ValueError` or :exc:`TypeError` being raised.

    Note that the range of the returned values depends on the operating
    system, the Python version, and on the filesystem encoding as returned by
    :func:`sys.getfilesystemencoding`.

    :param allow_pathlike:
        By default makes the strategy also include objects implementing the
        :class:`python:os.PathLike` interface when Python >= 3.6 is used. If
        :obj:`python:False` no pathlike objects will be generated. If
        :obj:`python:True` pathlike will be generated (Python >= 3.6 required)

    :type allow_pathlike: :obj:`python:bool` or :obj:`python:None`

    :param bool allow_existing:
        If paths which exist on the filesystem should be generated as well.

    .. versionadded:: 3.15
    """

    has_pathlike = hasattr(os, "PathLike")

    if allow_pathlike is None:
        allow_pathlike = has_pathlike
    if allow_pathlike and not has_pathlike:
        raise InvalidArgument(
            "allow_pathlike: os.PathLike not supported, use None instead "
            "to enable it only when available")

    strategies = []

    if os.name == 'nt':  # pragma: no cover
        # Windows paths can contain all surrogates and even surrogate pairs
        # if two paths are concatenated. This makes it more likely for them to
        # be generated.
        surrogate = characters(
            min_codepoint=0xD800, max_codepoint=0xDFFF)
        uni_char = characters(min_codepoint=0x1)
        windows_path_text = text(alphabet=one_of(uni_char, surrogate))
        strategies.append(windows_path_text)

        def text_to_bytes(path):
            fs_enc = sys.getfilesystemencoding()
            try:
                return path.encode(fs_enc, 'surrogatepass')
            except UnicodeEncodeError:
                return path.encode(fs_enc, 'replace')

        windows_path_bytes = windows_path_text.map(text_to_bytes)
        strategies.append(windows_path_bytes)
    else:
        unix_path_bytes = binary().map(lambda b: b.replace(b"\x00", b" "))
        strategies.append(unix_path_bytes)

        unix_path_text = unix_path_bytes.map(
            lambda b: b.decode(
                sys.getfilesystemencoding(),
                'surrogateescape' if PY3 else 'ignore'))

        # Two surrogates generated through surrogateescape can generate
        # a valid utf-8 sequence when encoded and result in a different
        # code point when decoded again. Can happen when two paths get
        # concatenated. Shuffling makes it possible to generate such a case.
        shuffled_unix_text = permutations(draw(unix_path_text)).map(u"".join)
        strategies.append(shuffled_unix_text)

    main_strategy = one_of(*strategies)

    if not allow_existing:
        main_strategy = main_strategy.filter(lambda p: not os.path.exists(p))

    if allow_pathlike and hasattr(os, 'fspath'):
        pathlike_strategy = main_strategy.map(lambda p: _PathLike(p))
        main_strategy = one_of(main_strategy, pathlike_strategy)

    return draw(main_strategy)
