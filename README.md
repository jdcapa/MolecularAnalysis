# Molecular Analysis

This is a collection of short Python3 scripts. These allow a quick analysis of some Quantum mechanical calculations (involving either the *Orca* or *Cfour* programme packages).

Using the [MolecularToolbox](https://github.com/jdcapa/MolecularToolbox) package, these scripts are example implementations for common routines such as harmonic frequency analysis, geometry optimisations, basis set extrapolations, geometry modifications, calculation set-up, et cetera.

## Installation

All scripts require a [Python3.5 set-up](https://jdcapa.github.io/python/science/coding/set-up/2016/06/06/scientific-python3.5.html) as well as the [MolecularToolbox](https://github.com/jdcapa/MolecularToolbox) and the [ChemPhysConst](https://github.com/jdcapa/ChemPhysConst) package.
To install clone this repository into your Source directory (I like to use `$HOME/.Source`):

```
cd $HOME/.Source
git clone https://github.com/jdcapa/MolecularAnalysis
cd MolecularAnalysis
```

Execute the install script with the path to your `bin` folder.

```
python3 install.py ~/.local/bin
```

This will copy the scripts to the specified folder which should be included in your $PATH environment. In the following, a short description of the scripts are provided. Access additional detail through the following command:

```
<script> --help
```

## gopt – geometry optimisation monitoring

This is a small script which allows for monitoring of an **Orca/Cfour**
 SCF/MP2/CCSD/CCSD(T)/DFT geometry optimisation.
Since they usually take a while, one might use this little programme to check
 on a calculation.


## xyz – extracts XYZ data for analysis/modification

This little program reads a geometry from an xyz, trj or orca/cfour output file, provides a rigid-rotor analysis can rotate the xyz coordinates into its principle axis frame or print a connection map (bonding) for pymol.

## harmonic – Hessian analysis

A set of routines that reads the Hessian of a frequency calculation. The output provides harmonic frequencies (incl. scaling), intensities, plotting of the normal modes, isotopic substitutions and a csv export functionality.

## corelevel – core-level molecular orbitals for analysis

Reports energy of filtered core molecular orbitals.
The analysis is based on an orca  Loewdin reduced orbital population analysis  which can be activated by including the following in the orca input file:

## inp_mult – creates different multiplicities of the same job

Takes an inputfile (currently only orca xyz) and spawnes jobs with different multiplicities. It also creates the neccesary folders.

```
%output
   Print[P_OrbPopMO_L]  1
end
```
