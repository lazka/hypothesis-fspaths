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
import tempfile

import pytest

from hypothesis import given, find
from hypothesis_fspaths import fspaths, _path_exists
from hypothesis.errors import InvalidArgument

text_type = type(u'')
PY3 = (sys.version_info[0] == 3)
encoding = sys.getfilesystemencoding()
is_win = (os.name == 'nt')


def test_path_property_examples():
    if is_win:
        fspaths(allow_pathlike=False).filter(
            lambda p: os.path.normcase(p) != p).example()

        def is_valid_ascii_drive(p):
            if os.path.splitunc(p)[0]:
                return False

            drive = os.path.splitdrive(p)[0]
            if len(drive) != 2:
                return False

            return ord("A") <= ord(drive[0:1]) <= ord("z")

        fspaths(allow_pathlike=False).filter(is_valid_ascii_drive).example()

        fspaths(allow_pathlike=False).filter(
            lambda p: os.path.splitunc(p)[0]).example()

    fspaths(allow_pathlike=False).filter(
        lambda p: p and os.path.normpath(p) != p).example()
    fspaths(allow_pathlike=False).filter(
        lambda p: os.path.splitext(p)[1]).example()
    fspaths(allow_pathlike=False).filter(
        lambda p: os.path.basename(p) == p).example()
    fspaths(allow_pathlike=False).filter(os.path.isabs).example()
    fspaths(allow_pathlike=False).filter(os.path.dirname).example()
    fspaths(allow_pathlike=False).filter(os.path.basename).example()
    fspaths(allow_pathlike=False).filter(os.path.abspath).example()


def norm_encoding(name):
    """Normalizes an encoding name."""

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


def fspath(p):
    """Like os.fspath but for Python <= 3.6."""

    try:
        return os.fspath(p)
    except AttributeError:
        return p


@pytest.fixture(scope='module')
def tempdir_path():
    dir_ = tempfile.mkdtemp()
    try:
        yield dir_
    finally:
        os.rmdir(dir_)


@given(fspaths())
def test_path_join(path):
    assert type(fspath(path)) is type(os.path.join(path, path))


@given(fspaths(allow_existing=True).map(os.path.basename))
def test_open(tempdir_path, path):
    # To prevent side effects, only access a path in a temp directory we have
    # created
    if PY3 and isinstance(path, bytes):
        tempdir_path = os.fsencode(tempdir_path)
    path = os.path.join(tempdir_path, path)

    # The value range of fspaths() is limited by what open() accepts
    try:
        with open(path):
            pass
    except IOError:
        pass

    try:
        with io.open(path):
            pass
    except IOError:
        pass


def test_path_exists(tempdir_path):
    for l in range(1000, 10000, 100000):
        assert _path_exists(b"x" * l) is None
    assert not _path_exists(b"") and _path_exists(b"") is not None

    temp_file = os.path.join(tempdir_path, 'foo')
    open(temp_file, 'w').close()
    try:
        assert _path_exists(temp_file)
    finally:
        os.unlink(temp_file)


def test_avoids_existing(tempdir_path):

    def find_fresh_file_can_create():

        def is_filename_and_can_create(p):
            if os.path.basename(p) != fspath(p):
                return False

            try:
                with open(p, "w"):
                    pass
            except EnvironmentError:
                return False
            else:
                os.unlink(p)
                return True

        return find(fspaths(allow_existing=False), is_filename_and_can_create)

    old_cwd = os.getcwd()
    f1 = None
    try:
        os.chdir(tempdir_path)

        f1 = find_fresh_file_can_create()
        f2 = find_fresh_file_can_create()
        # checks replay is working correctly: find should find the same
        # thing twice.
        assert f1 == f2

        with open(f1, 'w'):
            pass

        # The file now exists, so we are forced to avoid it
        # and have to generate a new one.
        f3 = find_fresh_file_can_create()
        assert f3 != f1
    finally:
        if f1:
            os.unlink(f1)
        os.chdir(old_cwd)


@given(fspaths(allow_pathlike=False))
def test_allow_pathlike_false(path):
    assert isinstance(path, (bytes, text_type))


def test_allow_pathlike_fail_when_not_available():
    if not hasattr(os, 'PathLike'):
        with pytest.raises(InvalidArgument):
            fspaths(allow_pathlike=True).example()


@given(fspaths())
def test_no_allow_existing(path):
    try:
        os.lstat(path)
    except OSError:
        pass
    else:
        assert False


def test_example_basic():
    fspaths(allow_existing=True).filter(lambda p: not fspath(p)).example()
    fspaths(allow_existing=True).filter(
        lambda p: len(fspath(p)) > 20).example()


def test_example_types():

    def is_bytes(p):
        p = fspath(p)
        return isinstance(p, bytes)

    fspaths(allow_existing=True).filter(is_bytes).example()

    def is_text(p):
        p = fspath(p)
        return isinstance(p, text_type)

    fspaths(allow_existing=True).filter(is_text).example()

    def is_pathlike(p):
        # there should be values implementing os.PathLike
        if isinstance(p, (bytes, text_type)):
            return False
        os.fspath(p)
        return True

    if hasattr(os, 'PathLike'):
        value = fspaths(allow_existing=True).filter(is_pathlike).example()
        assert repr(value) == 'pathlike(%r)' % os.fspath(value)


@pytest.mark.skipif(is_win or not PY3, reason='PY3+Unix only')
def test_find_text_with_surrogateescape():
    # Python 3 str paths on Unix should contain surrogates due to the
    # surrogateescape handler at some point

    def text_with_surrogateescape(p):
        p = fspath(p)
        if not isinstance(p, text_type):
            return False

        try:
            p.encode(encoding)
        except UnicodeEncodeError:
            p.encode(encoding, 'surrogateescape')
            return True
        else:
            return False

    fspaths(allow_existing=True).filter(text_with_surrogateescape).example()


@pytest.mark.skipif(not is_win or not PY3, reason='PY3+Windows only')
def test_find_text_with_surrogatepass():
    # Windows str paths should contain surrogates at some point

    def text_with_surrogatepass(p):
        p = fspath(p)
        if not isinstance(p, text_type):
            return False

        try:
            p.encode('utf-8')
        except UnicodeEncodeError:
            p.encode('utf-8', 'surrogatepass')
            return True
        else:
            return False

    fspaths(allow_existing=True).filter(text_with_surrogatepass).example()


@pytest.mark.skipif(single_byte_full_encoding(encoding) or is_win,
                    reason='Unix+UTF-8 only')
def test_find_bytes_has_non_decodable():
    # In case the encoding doesn't accept all input it should fail
    # to decode binary paths on Unix at some point.

    def bytes_has_non_decodable(p):
        p = fspath(p)
        if not isinstance(p, bytes):
            return False

        try:
            p.decode(encoding)
        except UnicodeDecodeError:
            return True
        return False

    fspaths(allow_existing=True).filter(bytes_has_non_decodable).example()


@pytest.mark.skipif(
    is_win or not PY3 or norm_encoding('utf-8') != norm_encoding(encoding),
    reason='PY3+Unix+UTF-8 only')
def test_find_text_surrogates_merge_in_bytes_form():
    # These values can happen when two paths get concatenated under Unix.
    # os.listdir() will never return them, but open() will accept them.

    def text_surrogates_merge_in_bytes_form(p):
        p = fspath(p)
        if not isinstance(p, text_type):
            return False

        return p.encode(encoding, 'surrogateescape').decode(
            encoding, 'surrogateescape') != p

    fspaths(allow_existing=True).filter(
        text_surrogates_merge_in_bytes_form).example()


# utf-16 + surrogatepass is broken with <= Python 3.3, just skip it there.
@pytest.mark.skipif(not is_win or not PY3 or sys.version_info[:2] == (3, 3),
                    reason='PY3+Win only (PY3.3 broken)')
def test_text_contains_unmerged_surrogates_pairs():
    # These values can happen if two paths get concatenated on Windows.
    # os.listdir() will never return them, but open() will accept them.

    def text_contains_unmerged_surrogates_pairs(p):
        p = fspath(p)
        if not isinstance(p, text_type):
            return False

        return p.encode('utf-16-le', 'surrogatepass').decode(
            'utf-16-le', 'surrogatepass') != p

    fspaths(allow_existing=True).filter(
        text_contains_unmerged_surrogates_pairs).example()
