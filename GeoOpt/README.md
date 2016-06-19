`gopt` – geometry optimisation monitoring
======================

This is a small script which allows for monitoring of a **Cfour/Orca**
 SCF/MP2/CCSD/CCSD(T)/DFT geometry optimisation or a vibrational calculations.
Since they usually take a while, one might use this little programme to check
 on a calculation.

**Requirements:** Python3.5 or newer, MolecularToolbox, ChemPhysConst


Usage
-----

Gathering information over a cfour output file is straight forward:

```
gopt <outputfile>
```

There are additional options:

```
 gopt [-h] [-s] [-o] [-v] <outputfile>

Script which monitors SCF/MP2/CCSD/CCSD(T) as well as DFT geometry
optimisations for Cfour and Orca.

positional arguments:
  <outputfile>   Cfour/Orca Output file

optional arguments:
  -s, --short    Keeps the output to a minimum [default: False].
  -o, --opt      Writes an opt.xyz file containing the geometry of each
                 iteration (default: False)
  -v, --verbose  Prints extra output for debugging [default: False].
  -h, --help     show this help message and exit
```

One could use a short bash command to automate the request spiced up with some
 additional information:

```
watch -t -c -n10 "pwd && gopt -s <outputfile> && echo '\nLast 10 lines of the OUTPUT file:\n' && tail -n10 <outputfile>
```

Roadmap
-------

Features for the next version update:

- [ ] Cfour Toolbox support
- [ ] fix basis special
- [ ] add DPT and DBOC support
- [ ] add mrcc support
