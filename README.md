cfour monitoring – c4
======================

This is a small script which allows for monitoring of a Cfour
 SCF/MP2/CCSD/CCSD(T) geometry optimisation or a vibrational calculations.
Since they usually take a while, one might use this little programme to check
 on a calculation.

Installation
------------

**Requirements:** Python 2.6, cfour

Simply put the executable c4 script in a folder reached by your `$PATH` variable.

Usage
-----

Gathering information over a cfour output file is straight forward:

    $ c4 <outputfile>

For an overview over additional options check the help:

    $ c4 --help

One could use a short bash command to automate the request spiced up with some
 additional information:

    $  watch -t -c -n10 "pwd && c4 -s OUT && echo '\nLast 10 lines of the OUTPUT file:\n' && tail -n10 OUT"

Roadmap
-------

Features for the next version update:

- [ ] fix basis special
- [ ] add DPT and DBOC support
- [ ] add mrcc support
- [ ] add FINDIF support
- [ ] add VPT2 support
- [ ] add routine that prints out optimisation summary with specific parameter
