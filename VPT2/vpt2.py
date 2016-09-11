#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""VPT2 analysis for an Orca calculation"""
import argparse
from moleculartoolbox import VPT2_ForceFields
from moleculartoolbox import VPT2
from moleculartoolbox import Harmonic
from moleculartoolbox import printfunctions as PF
from moleculartoolbox import OrcaOutput
from moleculartoolbox import CfourOutput
from moleculartoolbox import Atom
import os
import sys


# parser set-up
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('outfile',
                    metavar='Output file',
                    type=str, help='Cfour/Orca Output file')
parser.add_argument('-b', "--basename",
                    action='store',
                    type=str, default="",
                    dest="basename",
                    help=('Provide the Orca basename if there is more than one'
                          ' calculation.'))

ARGS = parser.parse_args()


if __name__ == '__main__':
    if not os.path.exists(ARGS.outfile):
        sys.exit("Cannot find {}.".format(ARGS.outfile))
    base_dir = os.path.dirname(ARGS.outfile)
    base_dir = base_dir if base_dir else os.getcwd()

    orca_output = OrcaOutput(base_dir, ARGS.basename)
    geometry = orca_output.geometries[0]
    # dip_der = orca_output.read_orca_dipole_derivative()
    harmonic = Harmonic(geometry,
                        orca_output.hessian)
    moI = geometry.rot_prop.moment_of_inertia_tensor()
    print("Moment-of-inertia tensor\n")
    print(PF.print_np_2Dmatrix(moI))
    print(PF.print_rigid_rotational_constants(geometry.rot_prop))
    print(PF.print_harmonics(harmonic))
    
    for output_str in harmonic.displaced_geometries(True, "Bohr", 9, False):
        print(output_str)


    # We need the displaced Hessians
    disp_Hessians = orca_output.get_displaced_Hessians("hess files")
    # initiate the force_fields class
    force_fields = VPT2_ForceFields(base_dir, harmonic)
    # transform the Hessians into normal coordinates
    nc_Hessians = force_fields.transform_displaced_Hessians(disp_Hessians)
    # Get the cubic and semi-quartic FF
    force_fields.calculate_cubic_force_field(nc_Hessians)
    force_fields.calculate_semiquartic_force_field(nc_Hessians)

    print_more = True
    if print_more:
        print("Cubic")
        print(PF.print_force_constants(force_fields.cubic,
                                       geometry,
                                       "cubic"))
        print("Semi-quartic")
        print(PF.print_force_constants(force_fields.semiquartic,
                                       geometry,
                                       "semi-quartic"))
        print("Coriolis Zeta")
        print(PF.print_coriolis_zeta(harmonic.coriolis_zeta()))
    vpt2 = VPT2(harmonic, force_fields.cubic, force_fields.semiquartic, 
                print_level=1)
    # Vibrational-Rotational constants  -alpha
    alpha = vpt2.vibRot_constants()[0]
    if print_more:
        print(PF.print_VibRot_constants(alpha, geometry))
    # Anharmonic constants  chi
    chi = vpt2.anharmonic_constants()
    print(PF.print_anharmonic_constants(chi))
    print(harmonic.rot_const_inv_cm)
    # sys.exit('stop')
    # equilibrium rotational constants B_0
    # b_e = vpt2.b_0(alpha)
    # # fundamental transitions
    # fund_trans = vpt2.fundamental_transitions(chi)
    # harm_trans = harmonic.freq_inv_cm[geometry.nTransRot():].real
    # for i, trans in enumerate(fund_trans):
    #     print trans, trans - harm_trans[i]

    # vpt2_derivatives = vpt2.mat_D
    # print PrintFunctions.print_harmonic_VPT2_derivatives(vpt2_derivatives,
    #                                                      harmonic)

    # print "ZPE:", vpt2.zero_point_energy(chi)
    # print vpt2.detect_Fermi_resonances(vpt2_derivatives)
    # vpt2.effective_hamiltonian(chi)