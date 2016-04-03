#!/usr/bin/python

import re
import sys
import math
import argparse
import os
import subprocess
from collections import OrderedDict

program_description = """
Script which allows for monitoring of a Cfour SCF/MP2/CCSD/CCSD(T)
geometry optimisation or a vibrational calculation.
This is a small standalone version separated from all the large classes.
"""

# parser set-up
parser = argparse.ArgumentParser(description=program_description)
parser.add_argument('out_File',
                    metavar='Output file',
                    type=str, default="OUT",
                    help='cfour output file [default: OUT]')
parser.add_argument('-s', "--short",
                    action="store_true",
                    default=False,
                    dest="short_flag",
                    help='Keeps the output to a minimum (default: False)')
parser.add_argument('-o', '--opt',
                    action="store_true",
                    default=False,
                    dest="opt_write_flag",
                    help='Writes an opt.xyz file containing the ' +
                    'geometry of each iteration (default: False)')
parser.add_argument('-v', '--vib',
                    action="store_true",
                    default=False,
                    dest="vib_write_flag",
                    help='Writes an vib.xyz file containing the ' +
                    'displacement vectors of each vibration (default: False)')

args = parser.parse_args()

bohr2angstrom = 1.0 / 0.52917721092
outfile = args.out_File
short_flag = args.short_flag
opt_write_flag = args.opt_write_flag
vib_write_flag = args.vib_write_flag

outfile_directory = os.path.dirname(outfile)


def simon_asks(command):
    '''
    Routine to get an output of a unix command.
    '''
    proc = subprocess.Popen(command,
                            stdout=subprocess.PIPE,
                            shell=True)
    (out, err) = proc.communicate()
    if err:
        sys.exit(err)
    return out


def check_if_finished():
    '''
    Returns true if the calculation finished
    '''
    check_string = simon_asks('tail -n 3 {0}'.format(outfile))

    if ('xprops finished' in check_string or
            "Zero-point vibrational energy" in check_string):
        print "Calculation terminated successfully."
        return True
    else:
        print "Calculation is not finished yet..."
        return False


def time_info():
    '''
    Retrieves time details
    '''
    import time
    import datetime

    if not os.path.exists(os.path.join(outfile_directory, 'FILES')):
        print "No timing information (FILES file missing)"
        return
    start_time = os.path.getmtime(os.path.join(outfile_directory, 'FILES'))
    last_change = os.path.getmtime(outfile)
    running_time = last_change - start_time
    print "Start time:  {0}".format(time.strftime("%d/%m/%Y %H:%M:%S",
                                                  time.localtime(start_time)))

    print "Last Change: {0} (running for {1})".format(
        time.strftime("%d/%m/%Y %H:%M:%S",
                      time.localtime(last_change)),
        datetime.timedelta(seconds=running_time))


def get_calc_info():
    '''
    Reads basic calculational details from the output file
    '''
    try:
        out = open(outfile, 'r')
    except:
        sys.exit('No output file to process.')

    infodict = {"level":    ["CALCLEVEL", "ICLLVL", ""],
                "basis":    ["BASIS", "IBASIS", ""],
                "charge":   ["CHARGE", "ICHRGE", ""],
                "mult":     ["MULTIPLICTY", "IMULTP", ""],
                "ref":      ["REFERENCE", "IREFNC", ""],
                "geomet":   ["GEO_METHOD", "INR", ""],
                "geoconv":  ["GEO_CONV", "ICONTL", ""],
                "vib":      ["VIBRATION", "IVIB", ""],
                "anharm":   ["ANHARMONIC", "IANHAR", ""],
                "frozen":   ["FROZEN_CORE", "IFROCO", ""],
                "dropmo":   ["DROPMO", "IDRPMO", ""]
                }
    # filling the empty fields
    for line in out:
        for k in infodict.keys():
            if re.search("\s+{0}\s+{1}\s+".format(infodict[k][0],
                                                  infodict[k][1]), line):
                # BOOM, Magic
                infodict[k][2] = [
                    x for x in line.strip().split('   ') if x][2].strip()
            elif "Job Title" in line:
                break
    return infodict


def calc_analyser():
    '''
    Analyses the calculation and decides what to do next
    '''
    infodict = get_calc_info()

    if not short_flag:
        time_info()

    if infodict['vib'][2] != 'NO':
        # calc_type = "VIB"
        print "\nCalculation type: Frequency Analysis"
        if infodict['anharm'][2] == "OFF":
            print "Method: Double harmonic approximation"
        else:
            print "Method: %s" % infodict['anharm'][2]

    elif (infodict['geomet'][2] == "NR" or infodict['geomet'][2] == "TS"):
        print "\nCalculation type: Optimisation (geometric convergens" + \
            " crit.: 10E-{0} H)".format(infodict['geoconv'][2])
        # calc_type = "OPT"

    elif "SINGLE_POINT" in infodict['geomet'][2]:
        print "\nCalculation type: Single Point Energy"
        # calc_type = "SINGLE_POINT"
    else:
        print "Infodict:"
        for key, value in infodict.iteritems():
            print key, value[2]
        sys.exit("Calculation type unknown")

    print "Level of theory: {0}/{1} with {2} ".format(infodict['level'][2],
                                                      infodict['basis'][2],
                                                      infodict['ref'][2]) + \
        "reference"
    print "Charge: %s, Multiplicity: %s\n" % (infodict['charge'][2],
                                              infodict['mult'][2])

    if (infodict['frozen'][2] != 'ON' and infodict['dropmo'][2] == 'NONE'):
        print "No Frozen Core setting detected." + \
            "ARE YOU SURE THIS IS WHAT YOU WANT?\n"

    energies = cFour_energies(infodict)
    return infodict, energies


def cFour_energies(infodict):
    '''
    Harvests the cfour energy terms
    '''
    energies = []
    iter_energy = []
    SCF_converged_flag = False

    # RegEx definitions
    if infodict['ref'][2] == 'ROHF':
        key_E_SCF = re.compile(
            r"\s+\d+\s+([-0-9]+\.\d+)\s+[0-9]+\.[0-9]+D[-0-9]+")
    else:
        key_E_SCF = re.compile(r"E\(SCF\)\s*=\s*([-0-9]+\.\d*)")
    # "CCSD energy             -238.831886924899"
    if infodict['level'][2] == 'CCSD':
        key_E_CCSD = re.compile(r"Total CCSD energy\s+:\s+([-0-9]+\.\d+)")
    else:
        key_E_CCSD = re.compile(r"CCSD energy\s*([-0-9]+\.\d*)")
    # "CCSD(T) energy          -238.851462847707"
    key_E_CCSD_T = re.compile(r"CCSD\(T\) energy\s*([-0-9]+\.\d*)")

    # Process major outputfile
    out = open(outfile, 'r')
    for line in out:
        if "SCF has converged." in line:
            if iter_energy:
                if (len(iter_energy) < 3 and len(iter_energy) > 1):
                    iter_energy.append(0.0)
                if len(iter_energy) < 3:
                    iter_energy.append(0.0)
                if len(iter_energy) > 3:
                    print 'Check energy parsing: iter_energy =', iter_energy
                    sys.exit()
                energies.append(iter_energy)
                iter_energy = []
            SCF_converged_flag = True
            continue
        if SCF_converged_flag:
            if key_E_SCF.search(line):
                iter_energy.append(float(key_E_SCF.search(line).group(1)))
                SCF_converged_flag = False
                continue

        if ("CCSD" in infodict["level"][2] and key_E_CCSD.search(line)):
            iter_energy.append(float(key_E_CCSD.search(line).group(1)))
            continue
        if ("CCSD(T)" in infodict["level"][2] and key_E_CCSD_T.search(line)):
            iter_energy.append(float(key_E_CCSD_T.search(line).group(1)))
            continue
    energies.append(iter_energy)

    return energies


def cFour_geometries():
    '''
    Obtains geometry for each iteration.
    dXSC1  -0.0001834151    0.0169752612  179.1069710534  179.1239463146
    '''
    geometries = []
    iter_geometry = []
    iter_geometry_old = []
    geometry_flag = False
    key_geometry = re.compile('([a-zA-Z0-9]+)' +
                              '\s+[-0-9]+\.\d+\s+[-0-9]+\.\d+\s+' +
                              '([-0-9]+\.\d+)\s+([-0-9]+\.\d+)')
    with open(outfile, 'r') as cfour_main_output_file:
        for line in cfour_main_output_file:
            if ('Parameter     dV/dR           ' +
                    'Step          Rold            Rnew' in line):
                geometry_flag = True
                continue
            if geometry_flag:
                if 'Minimum force:' in line:
                    if (not geometries and iter_geometry_old):
                        geometries.append(iter_geometry_old)
                        iter_geometry_old = []
                    geometries.append(iter_geometry)
                    geometry_flag = False
                    iter_geometry = []
                    continue
                if key_geometry.match(line.strip()):
                    if not geometries:
                        iter_geometry_old.append(
                            [key_geometry.match(line.strip()).group(1),
                             float(key_geometry.match(line.strip()).group(2))])
                        iter_geometry.append(
                            [key_geometry.match(line.strip()).group(1),
                             float(key_geometry.match(line.strip()).group(3))])
                    else:
                        iter_geometry.append(
                            [key_geometry.match(line.strip()).group(1),
                             float(key_geometry.match(line.strip()).group(3))])
    return geometries


def get_vibrations():
    '''
    Reads the Quadrature file, which contains the frequencies and normal
     coordinates (in bohr).
    Combines with the xyz geometry and returns a displacement vector
     dictionary.

    Relationship between cfour's normal coordinates A and the
    'back transformed dimensionless normal coordinates (in bohr)' B
    bohr2angstrom = 0.5291772109
    N_A = 6.02214129E+023   # 1/mol
    h   = 6.2606957E-034    # J*s
    c   = 299792458         # m/s
    B = (h*N_A*1000/
        (4*PI^2*wavnumber_in_inverse_cm *100*c*
            Molecular_weight_of_atom_in_g_per_mol)*bohr2angstrom*1E910*A
    '''
    quadrature_path = os.path.join(outfile_directory, "QUADRATURE")
    if not os.path.exists(quadrature_path):
        return

    def extend_matrices(matrix_1, matrix_2):
        '''
        joins two matrices of the same length
        '''
        new_mat, vec = [], []
        if len(matrix_1) == len(matrix_2):
            for i, row in enumerate(matrix_1):
                vec = []
                for element in row:
                    vec.append(element)
                for element in matrix_2[i]:
                    vec.append(element)
                new_mat.append(vec)
        return new_mat

    geometry = cFour_xyz_geometries()[-1]
    vibrations = OrderedDict()
    re_Frequency = re.compile('\s+([-0-9]+\.\d+i*)\s*\n')
    re_Coordinates = re.compile(
        '([-0-9]+\.\d+)\s+([-0-9]+\.\d+)\s+([-0-9]+\.\d+)')

    normal_coordinates_B = []
    frequency = ""
    frequency_count = 1

    with open(quadrature_path) as quadrature:
        for line in quadrature:
            if (re_Frequency.match(line)):
                if (frequency and normal_coordinates_B):
                    vibrations[frequency_count] = [
                        frequency, extend_matrices(geometry,
                                                   normal_coordinates_B)]
                    normal_coordinates_B = []
                    frequency_count += 1
                frequency = re_Frequency.match(line).group(1)
            if re_Coordinates.match(line.strip()):
                vector = []
                for j in range(3):
                    vector.append(
                        bohr2angstrom *
                        float(re_Coordinates.match(line.strip()).group(j + 1)))
                normal_coordinates_B.append(vector)
    vibrations[frequency_count] = [frequency,
                                   extend_matrices(geometry,
                                                   normal_coordinates_B)]

    return vibrations


def cFour_xyz_geometries():
    '''
    Finds xyz geometries for each iteration
    '''
    geometries = []
    iter_geometry = []
    geometry_flag = False
    key_geometry = re.compile('([a-zA-Z]+)\s+[-0-9]+\s+' +
                              '([-0-9]+\.\d+)\s+' +
                              '([-0-9]+\.\d+)\s+' +
                              '([-0-9]+\.\d+)')
    with open(outfile, 'r') as cfour_main_output_file:
        for line in cfour_main_output_file:
            if "Z-matrix   Atomic            Coordinates (in bohr)" in line:
                geometry_flag = True
                continue
            if geometry_flag:
                if 'Interatomic distance matrix (Angstroms)' in line:
                    geometries.append(iter_geometry)
                    geometry_flag = False
                    iter_geometry = []
                if key_geometry.search(line.strip()):
                    element = key_geometry.search(
                        line.strip()).group(1).title()
                    coordinates = [element, 0.0, 0.0, 0.0]
                    for j in range(3):
                        coordinates[j + 1] = \
                            1 / bohr2angstrom * \
                            float(key_geometry.search(
                                line.strip()).group(j + 2))
                    iter_geometry.append(coordinates)
    return geometries


def get_molecular_gradient_norms():
    '''
    Obtains Molecular gradient norm for each iteration.
    e.g. 3-1-1-0/2-1-1-0@C_S
    '''
    molecular_gradient_norms = []
    with open(outfile, 'r') as cfour_main_output_file:
        for line in cfour_main_output_file:
            if "Molecular gradient norm" in line:
                molecular_gradient_norms.append(float(line.split()[-1]))

    return molecular_gradient_norms


def get_zero_point_energy():
    '''
    Obtains the Zero-point energy from the out file
    '''
    with open(outfile, 'r') as cfour_main_output_file:
        for line in cfour_main_output_file:
            if 'Zero-point energy:' in line:
                zpe = float(line.split()[5])
                break
            if 'Zero-point vibrational energy:' in line:
                zpe = float(line.split()[-2])
                break
    return zpe


def opt_energy_output(energies, molecular_gradient_norms):
    '''
    formats energies to a nice list output
    '''
    if not energies:
        print "No energies found as of yet."
        return
    if energies and not energies[0]:
        print "No energies found as of yet."
        return

    columns = ["Iter"]
    s_E_SCF = "E(SCF)/a.u."
    s_E_CCSD = "E(CCSD)/a.u."
    s_E_CCSD_T = "E(CCSD(T))/a.u."

    s_p_Diff = u"-lg|\u0394E|"  # -lg(DeltaE)
    s_MolGrad = "|Grad|/a.u."

    # What do we have in energies
    max_e = 0
    for energy_array in energies:
        for i, energy in enumerate(energy_array):
            if (energy != 0.0 and i > max_e):
                max_e = i

    possible_middle_columns = [s_E_SCF, s_E_CCSD, s_E_CCSD_T]

    # How many columns?
    for i, header_string in enumerate(possible_middle_columns):
        if i > max_e:
            break
        else:
            columns.append(header_string)
    if len(columns) > 1:
        columns.append(s_p_Diff)
        columns.append(s_MolGrad)
    else:
        print "No energy information."
        return

    number_of_data_columns = len(columns) - 3

    # Write header and deco
    header = u"{:<4}%s {:>7} {:>10}" % ("  {:>14}" * number_of_data_columns)
    header = header.format(*columns)
    deco = ""
    for i in range(len(header)):
        deco += u"\u2014"
    print header.encode('utf-8')

    # fset up iterations range

    if (short_flag and len(energies) > 6):
        iterations = [0, 1, 2, -3, -2, -1]
    else:
        iterations = range(len(energies))

    # let's build the energy output
    energy_output_string = deco

    for it, i in enumerate(iterations):
        # In case we use the shortened list
        if (short_flag and i == -3):
            intermission = u"\n{0:^4}%s {0:^7} {0:^10}" % (
                "  {0:^14}" * number_of_data_columns)
            energy_output_string += intermission.format(u"\u22EE")

        # Here comes the stuff that is the same for everything
        line = "\n{:< 4,d}%s" % ("  {:> 14,.9f}" * number_of_data_columns)
        e_list = energies[i][:number_of_data_columns]

        # Now the first line has no difference yet
        if i == 0:
            log_diff = " -   "
        else:
            if len(energies[i]) < number_of_data_columns:
                log_diff = " -  "
                e_list = energies[i]
            else:
                diff = math.fabs(energies[i][number_of_data_columns - 1] -
                                 energies[i - 1][number_of_data_columns - 1])
                if diff != 0.0:
                    log_diff = "{:.2f} ".format(-1 * math.log10(diff))
                else:
                    log_diff = " N/A "
        # Let's fix the iterations
        if i < 0:
            iteration = len(energies) + i + 1
        else:
            iteration = i + 1
        # Finally, we write it out
        try:
            try:
                if (i < 0 and len(molecular_gradient_norms) < len(energies)):
                    grad = "  {:>8,.7f}".format(molecular_gradient_norms[i+1])
                else:
                    grad = "  {:>8,.7f}".format(molecular_gradient_norms[i])
            except:
                grad = " {0:>7}".format("   -  ")
            energy_output_string += line.format(iteration, *e_list) + \
                u"  {0:>7}".format(log_diff) + \
                grad
        except:
            line = "\n{:< 4,d}  {:>14,.9f}%s" % (
                "  {:^14}" * (number_of_data_columns - 1))
            empties_list = []
            for g in range(number_of_data_columns - 1):
                empties_list.append("  -  ")
            energy_output_string += line.format(iteration,
                                                energies[i][0],
                                                *empties_list) + \
                " {0:>7}".format(log_diff) +  \
                " {0:>7}".format("   -  ")

    print energy_output_string.encode('utf-8')
    print deco.encode('utf-8') + '\n'


def opt_geometry_output(geometries):
    '''
    generates an output for the overall geometry change
    '''
    output_array = []

    if len(geometries) < 1:
        return

    for i, valuepair in enumerate(geometries[0]):
        output_array.append([valuepair[0], valuepair[1], geometries[-1][i][1]])

    print "Change of geometry during the optimisation:\n"
    header = u"{0:<10} {1:>12} \u27F6 {2:>12}".format(
        "Parameter", "Old value", "New value")
    print header.encode('utf-8')
    deco = u"\u2014" * len(header)
    print deco.encode('utf-8')

    row_format = u"{0:<10} {1: > 12,.6f} \u27F6 {2: > 12,.6f}"
    for element in output_array:
        print row_format.format(*element).encode('utf-8')
    print deco.encode('utf-8') + "\n"


def sp_energy_output(energies):
    '''
    prints the Energy components of a single point calculation
    '''
    print 'Energies:'
    energy_array = [x for x in energies[0] if x != 0.0]
    if len(energy_array) > 0:
        print "SCF energy E[SCF]         = {:.10f}".format(energy_array[0])
    if len(energy_array) > 1:
        print "CCSD energy E[CCSD]       = {:.10f}".format(energy_array[1])
    if len(energy_array) > 2:
        print "CCSD(T) energy E[CCSD(T)] = {:.10f}".format(energy_array[2])


def vib_output(vibrations):
    '''
    prints harmonic vibrations
    '''
    print "\nVibrations:"
    for key, value in vibrations.iteritems():
        imaginary_flag = False
        vib = value[0]
        if "i" in vib:
            imaginary_flag = True
            vib = re.sub("i", "", vib)
        vib = "{0:.2f}".format(float(vib))
        if imaginary_flag:
            vib += "i"
        vib = vib.split(".")
        print u" \u03BD_{:02d} = {:>5}.{:<3} cm\u207B\u00B9".format(int(key),
                                                                    *vib)


def check_vib_progress():
    '''
    Reports the amount of displacements already done.
    '''
    disp = int(
        simon_asks('grep "CPHF coefficients" %s | wc -l' % outfile).strip())
    print "\n%i displacements were done." % disp


def cpu_temperature():
    '''
    obtains the current cpu load from
    /sys/class/hwmon/hwmonX/device/temp1_input
    '''
    temp_folder = ""
    temperature_path = "/sys/class/hwmon/hwmon{0:d}/device/temp3_label"
    temperature_folder = "/sys/class/hwmon/hwmon{0:d}/device/"
    for number in range(6):
        if os.path.exists(temperature_path.format(number)):
            if "Core" in simon_asks("cat " + temperature_path.format(number)):
                temp_folder = temperature_folder.format(number)
                break

    if temp_folder:
        temp1_input = float(
            simon_asks("cat %stemp1_input" % temp_folder)) / 1000.0
        temp1_crit = float(
            simon_asks("cat %stemp1_crit" % temp_folder)) / 1000.0
        return u"{0:.0f}\u00B0C ".format(temp1_input) + \
            u"(Critical temp.: {0:.0f}\u00B0C)".format(temp1_crit)
    else:
        return "unknown"


def used_mem():
    '''
    obtains the current used and total mem from
    free -m
    '''
    re_mem = re.compile('Mem:\s+(\d+)\s+(\d+)')
    raw = simon_asks('free -m').split('\n')[1]
    total = re_mem.search(raw).group(1)
    free = re_mem.search(raw).group(2)
    return "{0:,d} MB of {1:,d} MB".format(int(free), int(total))


def write_opt_file(geometries, energies):
    '''
    writes an opt.xyz file, containing each geometry and energy.
    '''
    if not (len(energies[0]) > 1 and len(energies) > 1):
        return False
    with open(os.path.join(outfile_directory, "opt.xyz"), 'w') as opt_file:
        for i, energy_set in enumerate(energies):
            opt_file.write(
                '{0:d}\nE = {1:.9f} Hartree\n'.format(
                    len(geometries[i]), energy_set[-1]))
            for coordinates in geometries[i]:
                opt_file.write(
                    '{0:<3} {1:>13,.9f} ' +
                    '{2:>13,.9f} {3:>13,.9f}\n'.format(*coordinates))
    return True


def write_vib_file(vibrations):
    '''
    writes an vib.xyz file, containing each vibration and frequency.
    '''
    if not vibrations:
        return False
    format_string = '{:<3} ' + 6 * '{:>13,.9f} ' + '\n'
    with open(os.path.join(outfile_directory, "vib.xyz"), 'w') as vib_file:
        for key, value in vibrations.iteritems():
            geometry = value[1]
            vib_file.write(
                '{0:d}\nv{1:d} = {2} cm**-1\n'.format(len(geometry),
                                                      key, value[0]))
            for vector in geometry:
                vib_file.write(format_string.format(*vector))
    return True

# iupac 1997 (externalise!)
periodic_table = {
    1:      ['Hydrogen',
             'H',
             1,
             [1.0078250321,
              2.0141017780],
             [0.999885,
                 0.0001157]],
    2:      ['Helium',
             'He',
             0,
             [3.0160293097,
              4.0026032497],
             [0.00000137,
                 0.99999863]],
    3:      ['Lithium',
             'Li',
             1,
             [6.0151233,
              7.0160040],
             [0.0759,
                 0.9241]],
    4:      ['Beryllium',
             'Be',
             2,
             [9.0121821],
             [1.0]],
    5:      ['Boron',
             'B',
             3,
             [10.0129370,
              11.0093055],
             [0.199,
                 0.801]],
    6:      ['Carbon',
             'C',
             4,
             [12.0,
              13.0033548378],
             [0.9893,
                 0.0107]],
    7:      ['Nitrogen',
             'N',
             5,
             [14.0030740052,
              15.0001088984],
             [0.99632,
                 0.00368]],
    8:      ['Oxygen',
             'O',
             -2,
             [15.9949146221,
              16.9991315,
              17.9991604],
             [0.99757,
                 0.00038,
                 0.00205]],
    9:      ['Fluorine',
             'F',
             -1,
             [18.99840320],
             [1.0]],
    10:     ['Neon',
             'Ne',
             0,
             [19.9924401759,
              20.99384674,
              21.99138551],
             [0.9048,
                 0.0027,
                 0.0925]],
    11:     ['Sodium',
             'Na',
             1,
             [22.98976967],
             [1.0]],
    12:     ['Magnesium',
             'Mg',
             2,
             [23.98504190,
              24.98583702,
              25.98259304],
             [0.7899,
                 0.1,
                 0.1101]],
    13:     ['Aluminum',
             'Al',
             3,
             [26.98153844],
             [1.0]],
    14:     ['Silicon',
             'Si',
             4,
             [27.9769265327,
              28.97649472,
              29.97377022],
             [0.92297,
                 0.046832,
                 0.030872]],
    15:     ['Phosphorus',
             'P',
             5,
             [30.97376151],
             [1.0]],
    16:     ['Sulfur',
             'S',
             -2,
             [31.97207069,
              32.9714585,
              33.96786683,
              35.96708088],
             [0.9493,
                 0.0076,
                 0.0429,
                 0.0002]],
    17:     ['Chlorine',
             'Cl',
             -1,
             [34.96885271,
              36.96590260],
             [0.7578,
                 0.2422]],
    18:     ['Argon',
             'Ar',
             0,
             [35.96754628,
              37.9627322,
              39.962383123],
             [0.003365,
                 0.000632,
                 0.996003]],
    19:     ['Potassium',
             'K',
             1,
             [38.9637069,
              39.96399867,
              40.96182597],
             [0.932581,
                 0.000117,
                 0.067302]],
    20:     ['Calcium',
             'Ca',
             2,
             [39.9625912,
              41.9586183,
              42.9587668,
              43.9554811,
              45.9536928,
              47.952534],
             [0.96941,
                 0.00647,
                 0.00135,
                 0.02086,
                 0.00004,
                 0.00187]],
    21:     ['Scandium',
             'Sc',
             3,
             [44.9559102],
             [1.0]],
    22:     ['Titanium',
             'Ti',
             4,
             [45.9526295,
              46.9517638,
              47.9479471,
              48.9478708,
              49.9447921],
             [0.0825,
                 0.0744,
                 0.7372,
                 0.0541,
                 0.0518]],
    23:     ['Vanadium',
             'V',
             5,
             [49.9471628,
              50.9439637],
             [0.00250,
                 0.99750]],
    24:     ['Chromium',
             'Cr',
             2,
             [49.9460496,
              51.9405119,
              52.9406538,
              53.9388849],
             [0.04345,
                 0.83789,
                 0.09501,
                 0.02365]],
    25:     ['Manganese',
             'Mn',
             2,
             [54.9380496],
             [1.0]],
    26:     ['Iron',
             'Fe',
             3,
             [53.9396148,
              55.9349421,
              56.9353987,
              57.9332805],
             [0.05845,
                 0.91754,
                 0.02119,
                 0.00282]],
    27:     ['Cobalt',
             'Ni',
             3,
             [57.9353479,
              59.9307906,
              60.9310604,
              61.9283488,
              63.9279696],
             [0.680769,
                 0.262231,
                 0.011399,
                 0.036345,
                 0.009256]],
    28:     ['Nickel',
             'Co',
             2,
             [58.933195],
             [1.0]],
    29:     ['Copper',
             'Cu',
             2,
             [62.9296011,
              64.9277937],
             [0.6917,
                 0.3083]],
    30:     ['Zinc',
             'Zn',
             2,
             [63.9291466,
              65.9260368,
              66.9271309,
              67.9248476,
              69.925325],
             [0.4863,
                 0.279,
                 0.041,
                 0.1875,
                 0.0062]],
    31:     ['Gallium',
             'Ga',
             3,
             [68.925581,
              70.9247050],
             [0.60108,
                 0.39892]],
    32:     ['Germanium',
             'Ge',
             2,
             [69.9242504,
              71.9220762,
              72.9234594,
              73.9211782,
              75.9214027],
             [0.2084,
                 0.2754,
                 0.0773,
                 0.3628,
                 0.0761]],
    33:     ['Arsenic',
             'As',
             3,
             [74.9215964],
             [1.0]],
    34:     ['Selenium',
             'Se',
             4,
             [73.9224766,
              75.9192141,
              76.9199146,
              77.9173095,
              79.9165218,
              81.9167000],
             [0.0089,
                 0.0937,
                 0.0763,
                 0.2377,
                 0.4961,
                 0.0873]],
    35:     ['Bromine',
             'Br',
             -1,
             [78.9183376,
              80.916291],
             [0.5069,
                 0.4931]],
    36:     ['Krypton',
             'Kr',
             0,
             [77.920386,
              79.916378,
              81.9134846,
              82.914136,
              83.911507,
              85.9106103],
             [0.0035,
                 0.0228,
                 0.1158,
                 0.1149,
                 0.57,
                 0.1730]],
    37:     ['Rubidium',
             'Rb',
             1,
             [84.9117893,
              86.9091835],
             [0.7217,
                 0.2783]],
    38:     ['Strontium',
             'Sr',
             2,
             [83.913425,
              85.9092624,
              86.9088793,
              87.9056143],
             [0.0056,
                 0.0986,
                 0.07,
                 0.8258]],
    39:     ['Yttrium',
             'Y',
             3,
             [88.9058479],
             [1.0]],
    40:     ['Zirconium',
             'Zr',
             4,
             [89.9047037,
              90.905645,
              91.9050401,
              93.9063158,
              95.908276],
             [0.5145,
                 0.1122,
                 0.1715,
                 0.1738,
                 0.0280]],
    41:     ['Niobium',
             'Nb',
             5,
             [92.9063775],
             [1.0]],
    42:     ['Molybdenum',
             'Mo',
             6,
             [91.906810,
              93.9050876,
              94.9058415,
              95.9046789,
              96.906021,
              97.9054078,
              99.907477],
             [0.1484,
                 0.0925,
                 0.1592,
                 0.1668,
                 0.0955,
                 0.2413,
                 0.0963]],
    43:     ['Technetium',
             'Tc',
             2,
             [96.906365,
              97.907216,
              98.9062546],
             [1.0]],
    44:     ['Ruthenium',
             'Ru',
             3,
             [95.907598,
              97.905287,
              98.9059393,
              99.9042197,
              100.9055822,
              101.9043495,
              103.905430],
             [0.0554,
                 0.0187,
                 0.1276,
                 0.126,
                 0.1706,
                 0.3155,
                 0.1862]],
    45:     ['Rhodium',
             'Rh',
             2,
             [102.905504],
             [1.0]],
    46:     ['Palladium',
             'Pd',
             2,
             [101.905608,
              103.904035,
              104.905084,
              105.903483,
              107.903894,
              109.905152],
             [0.0102,
                 0.1114,
                 0.2233,
                 0.2733,
                 0.2646,
                 0.1172]],
    47:     ['Silver',
             'Ag',
             1,
             [106.905093,
              108.904756],
             [0.51839,
                 0.48161]],
    48:     ['Cadmium',
             'Cd',
             2,
             [105.906458,
              107.904183,
              109.903006,
              110.904182,
              111.9027572,
              112.9044009,
              113.9033581,
              115.904755],
             [0.0125,
                 0.0089,
                 0.1249,
                 0.128,
                 0.2413,
                 0.1222,
                 0.2873,
                 0.0749]],
    49:     ['Indium',
             'In',
             3,
             [112.904061,
              114.903878],
             [0.0429,
                 0.9571]],
    50:     ['Tin',
             'Sn',
             4,
             [111.904821,
              113.902782,
              114.903346,
              115.901744,
              116.902954,
              117.901606,
              118.903309,
              119.9021966,
              121.9034401,
              123.9052746],
             [0.0097,
                 0.0066,
                 0.0034,
                 0.1454,
                 0.0768,
                 0.2422,
                 0.0859,
                 0.3258,
                 0.0463,
                 0.0579]],
    51:     ['Antimony',
             'Sb',
             3,
             [120.9038180,
              122.9042157],
             [0.5721,
                 0.4279]],
    52:     ['Tellurium',
             'Te',
             4,
             [119.904020,
              121.9030471,
              122.904273,
              123.9028195,
              124.9044247,
              125.9033055,
              127.9044614,
              129.9062228],
             [0.0009,
                 0.0255,
                 0.0089,
                 0.0474,
                 0.0707,
                 0.1884,
                 0.3174,
                 0.3408]],
    53:     ['Iodine',
             'I',
             -1,
             [126.904468],
             [1.0]],
    54:     ['Xenon',
             'Xe',
             0,
             [123.9058958,
              125.904269,
              127.9035304,
              128.9047795,
              129.9035079,
              130.9050819,
              131.9041545,
              133.9053945,
              135.907220],
             [0.0009,
                 0.0009,
                 0.0192,
                 0.2644,
                 0.0408,
                 0.2118,
                 0.2689,
                 0.1044,
                 0.0887]],
    55:     ['Cesium',
             'Cs',
             1,
             [132.905447],
             [1.0]],
    56:     ['Barium',
             'Ba',
             2,
             [129.906310,
              131.905056,
              133.904503,
              134.905683,
              135.90457,
              136.905821,
              137.905241],
             [0.00106,
                 0.00101,
                 0.02417,
                 0.06592,
                 0.07854,
                 0.11232,
                 0.71698]],
    57:     ['Lanthanum',
             'La',
             3,
             [137.907107,
              138.906348],
             [0.00090,
                 0.99910]],
    58:     ['Cerium',
             'Ce',
             3,
             [135.907140,
              137.905986,
              139.905434,
              141.909240],
             [0.00185,
                 0.00251,
                 0.8845,
                 0.11114]],
    59:     ['Praseodymium',
             'Pr',
             3,
             [140.907648],
             [1.0]],
    60:     ['Neodymium',
             'Nd',
             3,
             [141.907719,
              142.90981,
              143.910083,
              144.912569,
              145.913112,
              147.916889,
              149.920887],
             [0.272,
                 0.122,
                 0.238,
                 0.083,
                 0.172,
                 0.057,
                 0.056]],
    61:     ['Promethium',
             'Pm',
             3,
             [144.91270],
             [1.0]],
    62:     ['Samarium',
             'Sm',
             3,
             [143.911995,
              146.914893,
              147.914818,
              148.91718,
              149.917271,
              151.919728,
              153.922205],
             [0.0307,
                 0.1499,
                 0.1124,
                 0.1382,
                 0.0738,
                 0.2675,
                 0.2275]],
    63:     ['Europium',
             'Eu',
             3,
             [150.919846,
              152.921226],
             [0.4781,
                 0.5219]],
    64:     ['Gadolinium',
             'Gd',
             3,
             [151.919788,
              153.920862,
              154.922619,
              155.92212,
              156.923957,
              157.924101,
              159.927051],
             [0.0020,
                 0.0218,
                 0.148,
                 0.2047,
                 0.1565,
                 0.2484,
                 0.2186]],
    65:     ['Terbium',
             'Tb',
             4,
             [158.925343],
             [1.0]],
    66:     ['Dysprosium',
             'Dy',
             3,
             [155.924278,
              157.924405,
              159.925194,
              160.92693,
              161.926795,
              162.928728,
              163.929171],
             [0.0006,
                 0.001,
                 0.0234,
                 0.1891,
                 0.2551,
                 0.249,
                 0.2818]],
    67:     ['Holmium',
             'Ho',
             3,
             [164.930319],
             [1.0]],
    68:     ['Erbium',
             'Er',
             3,
             [161.928775,
              163.929197,
              165.93029,
              166.932045,
              167.932368,
              169.935460],
             [0.0014,
                 0.0161,
                 0.3361,
                 0.2293,
                 0.2678,
                 0.1493]],
    69:     ['Thulium',
             'Tm',
             3,
             [168.934211],
             [1.0]],
    70:     ['Ytterbium',
             'Yb',
             3,
             [167.933894,
              169.934759,
              170.936322,
              171.9363777,
              172.9382068,
              173.9388581,
              175.942568],
             [0.0013,
                 0.0304,
                 0.1428,
                 0.2183,
                 0.1613,
                 0.3183,
                 0.1276]],
    71:     ['Lutetium',
             'Lu',
             3,
             [174.9407679,
              175.9426824],
             [0.9741,
                 0.0259]],
    72:     ['Hafnium',
             'Hf',
             4,
             [173.940040,
              175.9414018,
              176.94322,
              177.9436977,
              178.9458151,
              179.9465488],
             [0.0016,
                 0.0526,
                 0.186,
                 0.2728,
                 0.1362,
                 0.3508]],
    73:     ['Tantalum',
             'Ta',
             5,
             [179.947466,
              180.947996],
             [0.00012,
                 0.99988]],
    74:     ['Tungsten',
             'W',
             6,
             [179.946704,
              181.9482042,
              182.950223,
              183.9509312,
              185.9543641],
             [0.0012,
                 0.265,
                 0.1431,
                 0.3064,
                 0.2843]],
    75:     ['Rhenium',
             'Re',
             2,
             [184.9529557,
              186.9557508],
             [0.3740,
                 0.6260]],
    76:     ['Osmium',
             'Os',
             4,
             [183.952491,
              185.953838,
              186.9557479,
              187.955836,
              188.9581449,
              189.958445,
              191.961479],
             [0.0002,
                 0.0159,
                 0.0196,
                 0.1324,
                 0.1615,
                 0.2626,
                 0.4078]],
    77:     ['Iridium',
             'Ir',
             4,
             [190.960591,
              192.962924],
             [0.373,
                 0.627]],
    78:     ['Platinum',
             'Pt',
             4,
             [189.959930,
              191.961035,
              193.962664,
              194.964774,
              195.964935,
              197.967876],
             [0.00014,
                 0.00782,
                 0.32967,
                 0.33832,
                 0.25242,
                 0.07163]],
    79:     ['Gold',
             'Au',
             3,
             [196.966552],
             [1.0]],
    80:     ['Mercury',
             'Hg',
             2,
             [195.965815,
              197.966752,
              198.968262,
              199.968309,
              200.970285,
              201.970626,
              203.973476],
             [0.0015,
                 0.0997,
                 0.1687,
                 0.231,
                 0.1318,
                 0.2986,
                 0.0687]],
    81:     ['Thallium',
             'Tl',
             1,
             [202.972329,
              204.974412],
             [0.29524,
                 0.70476]],
    # ,
    82:     ['Lead',
             'Pb',
             2,
             [203.973029,
              205.974449,
              206.975881,
              207.976636],
             [0.014,
                 0.241,
                 0.221,
                 0.524]],
    83:     ['Bismuth',
             'Bi',
             3,
             [208.980383],
             [1.0]],
    84:     ['Polonium',
             'Po',
             4,
             [209.0],
             [1.0]],
    85:     ['Astatine',
             'At',
             7,
             [210.0],
             [1.0]],
    86:     ['Radon',
             'Rn',
             0,
             [220.0],
             [1.0]],
    87:     ['Francium',
             'Fr',
             1,
             [223.0],
             [1.0]],
    88:     ['Radium',
             'Ra',
             2,
             [226.0],
             [1.0]],
    89:     ['Actinium',
             'Ac',
             3,
             [227.0],
             [1.0]],
    90:     ['Thorium',
             'Th',
             4,
             [232.0380504],
             [1.0]],
    91:     ['Protactinium',
             'Pa',
             4,
             [231.03588],
             [1.0]],
    92:     ['Uranium',
             'U',
             6,
             [234.0409456,
              235.0439231,
              236.0455619,
              238.0507826],
             [0.000055,
                 0.0072,
                 0,
                 0.992745]],
    93:     ['Neptunium',
             'Np',
             5,
             [237.0],
             [1.0]],
    94:     ['Plutonium',
             'Pu',
             3,
             [244.0],
             [1.0]],
    95:     ['Americium',
             'Am',
             2,
             [243.0],
             [1.0]],
    96:     ['Curium',
             'Cm',
             3,
             [247.0],
             [1.0]],
    97:     ['Berkelium',
             'Bk',
             3,
             [247.0],
             [1.0]],
    98:     ['Californium',
             'Cf',
             0,
             [251.0],
             [1.0]],
    99:     ['Einsteinium',
             'Es',
             0,
             [252,
              .0],
             [1.0]],
    100:    ['Fermium',
             'Fm',
             0,
             [257.0],
             [1.0]],
    101:    ['Mendelevium',
             'Md',
             0,
             [258.0],
             [1.0]],
    102:    ['Nobelium',
             'No',
             0,
             [259.0],
             [1.0]],
    103:    ['Lawrencium',
             'Lr',
             0,
             [262.0],
             [1.0]],
    104:    ['Rutherfordium',
             'Rf',
             0,
             [261.0],
             [1.0]],
    105:    ['Dubnium',
             'Db',
             0,
             [262.0],
             [1.0]],
    106:    ['Seaborgium',
             'Sg',
             0,
             [266.0],
             [1.0]]
}


if __name__ == '__main__':
    test = False
    infodict, energies = calc_analyser()
    if 'SINGLE_POINT' not in infodict['geomet'][2]:
        opt_energy_output(energies, get_molecular_gradient_norms())
        opt_geometry_output(cFour_geometries())
        test = check_if_finished()
        if opt_write_flag:
            write_opt_file(cFour_xyz_geometries(), energies)
    else:
        sp_energy_output(energies)
        if infodict['vib'][2] != 'NO':
            check_vib_progress()
            test = check_if_finished()
            vibrations = get_vibrations()
            if vibrations:
                vib_output(vibrations)
                if vib_write_flag:
                    write_vib_file(vibrations)
                print "\nZero-point Energy: " + \
                    "{0:.2f} kJ/mol".format(get_zero_point_energy())
                test = True
    if not test:
        print "\nCurrent CPU status:"
        print u"Temp:     {0}".format(cpu_temperature()).encode('utf-8')
        # print "Load:     {.1f}\%".format(cpu_load())
        print "used Mem: {}".format(used_mem())