******************
hypothesis-fspaths
******************

`Hypothesis <https://hypothesis.readthedocs.io/en/latest/>`_ extension for
generating filesystem paths. Anything the built-in Python function ``open()``
accepts can be generated.

Example
=======

.. code:: python

    from hypothesis import given
    from hypothesis_fspaths import fspaths

    @given(fspaths())
    def test_open_file(path):
        try:
            open(path).close()
        except IOError:
            pass


.. image:: https://travis-ci.org/lazka/hypothesis-fspaths.svg?branch=master
    :target: https://travis-ci.org/lazka/hypothesis-fspaths
