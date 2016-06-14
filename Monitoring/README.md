`mon` – monitoring
======================

This is a small script which allows for monitoring of a **Cfour/Orca**
 SCF/MP2/CCSD/CCSD(T)/DFT geometry optimisation or a vibrational calculations.
Since they usually take a while, one might use this little programme to check
 on a calculation.

**Requirements:** Python3.4 or newer, MolecularToolbox, ChemPhysConst

Usage
-----

Gathering information over a cfour output file is straight forward:

```
mon <outputfile>
```

For an overview over additional options check the help:

```
mon --help
```

One could use a short bash command to automate the request spiced up with some
 additional information:

```
watch -t -c -n10 "pwd && c4 -s OUT && echo '\nLast 10 lines of the OUTPUT file:\n' && tail -n10 <OUT>
```

Roadmap
-------

Features for the next version update:

- [ ] add Orca and DFT support
- [ ] fix basis special
- [ ] add DPT and DBOC support
- [ ] add mrcc support
- [ ] add FINDIF support
- [ ] add VPT2 support
- [ ] add routine that prints out optimisation summary with specific parameter
