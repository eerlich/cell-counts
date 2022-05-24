#!/usr/bin/env python

"""Takes .csv files generated from FlowJo and generates a new .csv file with
cell counts for each gate in each tube.
version = 0.2
"""

import sys
import os.path
import csv
import itertools
import argparse
from decimal import Decimal, InvalidOperation

#global variables
grouping_bool = False
compact_bool = False

class TubeData:
    """Stores the data from each tube that was exported from FlowJo."""

    def __init__(self, tube_name, raw_percent_data_list):
        self.n = tube_name
        self.raw_percent = raw_percent_data_list
        self.group_id = ""
        self.cell_conc = 0
        self.percent_list = []
        self.count_list = []

        #the initiating functions
        self.convert_to_decimal()
        self.ask_cell_conc()

    def ask_cell_conc(self):
        """Ask the user for the cell concentrations of the samples."""
        while True:
            print("What's the cell concentration (10e4) for {}?".format(self.n))
            answer = input("> ")
            try:
                self.cell_conc = Decimal(answer)
                break
            except InvalidOperation:
                print("This isn't a number")
                yes_no()

    def convert_to_decimal(self):
        """Convert string values to Decimal and add to percent_list."""
        for percent in self.raw_percent:
            try:
                number = Decimal(percent) / 100
            except InvalidOperation:
                print("{} has an issue with an invalid number".format(self.n))
                sys.exit(0)
            self.percent_list.append(number)

    def calculate_cell_counts(self, calc_list):
        """Calculate the cell counts for this tube."""
        cell_conc = 0
        for n, i in enumerate(calc_list):
            if i == "start":
                cell_count = self.cell_conc * self.percent_list[n]
            elif i == "ignore":
                cell_count = ""
            else:
                cell_count = self.count_list[i] * self.percent_list[n]
            self.count_list.append(cell_count)

    def ask_group_id(self):
        """Ask the user and set the group identification."""
        print("What is the group for {}?".format(self.n))
        answer = input("> ")
        self.group_id = answer

def sys_arguments():
    """Deal with optional sys command flags called when starting the program."""
    parser = argparse.ArgumentParser(description = ("Takes .csv files generated"
    " from FlowJo and generates a new .csv file with cell counts for each gate "
    "in each tube."))

    parser.add_argument("-g", "--grouping", help="allows you to group tubes",
                        action="store_true")
    parser.add_argument("-c", "--compact", help="make a compact .csv output "
                        "file (default is long .csv file)", action="store_true")
    args = parser.parse_args()
    if args.grouping:
        global grouping_bool
        grouping_bool = True
    if args.compact:
        global compact_bool
        compact_bool = True

def yes_no():
    """Check to see if the user wants to try again or to quit."""
    print("Do you want to try again? Or quit?")
    answer = input("> ").lower()
    if answer in ["n", "no", "quit", "q"]:
        sys.exit(0)

def ask_path():
    """Ask the user for a .csv path."""
    while True:
        print("What is the path for the .csv file?")
        path = input("> ")
        path = path.strip('"')
        file_path, ext = os.path.splitext(path)
        if not os.path.isfile(path):
            print("This is not a valid path.")
            yes_no()
        elif not ext == ".csv":
            print("This isn't a .csv file. This program won't work with this.")
            yes_no()
        else:
            break
    return path

def process_csv(data):
    """Process a .csv file generated by FlowJo.

    gate_order is a list of the gate names cleaned up from FlowJo output.
    gates_dict is a dict where the keys are population names and the values are
    the number of gates that population has
    tube_list is a list of TubeData objects with one object per sample tube."""

    #first generate a dict of all of the gate names with the number of subgates
    gates_dict = {}
    gate_order = []
    #FlowJo adds a blank extra column at the end, it should be ignored
    for gate in data[0][1:-1]:
        #FlowJo does | Freq. of Parent (%) at the end of gate names that were
        #exported correctly
        if not " | " in gate:
            print("The gate {} doesn't have '|' in it. Is this file from "
            "FlowJo?".format(gate))
            sys.exit(0)
        cleaned_gate, test = gate.split(" | ")
        if not test == "Freq. of Parent (%)":
            print("{} isn't Freq. of Parent.".format(cleaned_gate))
        gate_order.append(cleaned_gate)

        #gates_dict is for ask_starting_gate's input
        #number_of_gates helps it find one of the shortest possible gates
        number_of_gates = len(cleaned_gate.split("/"))
        gates_dict[cleaned_gate] = number_of_gates

    tube_list = []

    for line in data[1:]:
        name = line[0].strip(".fcs")
        if not name in ["Mean", "SD"]:
            x = TubeData(name, line[1:-1])
            tube_list.append(x)

    return gate_order, gates_dict, tube_list

def check_starting_gate(gates):
    """Determine the starting gate and ask the user if unclear.

    If the user has made more than one inital gate on the ungated data, e.g.
    if the user has tried singlet gating then live gating vs. live gating first,
    then there should be multiple starting gates. Otherwise, the user should be
    asked to supply a starting gate.

    Returns the starting gates as a list of strings. Also returns a list of
    gates that should be ignored for cell count calculations."""

    only_one_start_gate = True
    starting_gate_list = []
    ignore_list = []

    lengths_checked = set([])
    redundant_lengths = set([])

    for length in gates.values():
        if length in lengths_checked and length == 1:
            only_one_start_gate = False
            #no need to continue checking
            break
        elif length in lengths_checked:
            redundant_lengths.add(length)
        lengths_checked.add(length)

    if only_one_start_gate:
        longest_shared = max(lengths_checked.difference(redundant_lengths))

        #finds one possible shortest gate, could be more efficient
        min_gate = ""
        for gate, number in gates.items():
            if number == longest_shared:
                min_gate = gate
        start_gate_str = ask_starting_gate(min_gate)
        starting_gate_list.append(start_gate_str)
        num_gate_of_min = gates[start_gate_str]
        for gate, number in gates.items():
            if number < num_gate_of_min:
                ignore_list.append(gate)
    else:
        [starting_gate_list.append(x) for x, y in gates.items() if y == 1]

    return starting_gate_list, ignore_list

def ask_starting_gate(min_gate):
    """Ask the user for a starting gate if there is only one base gate."""

    min_gate_list = min_gate.split("/")
    rep = ""
    for count, split in enumerate(min_gate_list, 1):
        rdiv = len(split) // 2
        if len(split) % 2 == 0:
            ldiv = rdiv - 1
        else:
            ldiv = rdiv
        part = "{}{}{}{}".format(" " * rdiv, count, " " * ldiv, "/")
        rep += part
    while True:
        print("Which gate should the cell count calculation start with?\n{}\n{}"
        .format(min_gate, rep))
        answer = input("> ")
        try:
            int_answer = int(answer)
            if 0 < int_answer <= len(min_gate_list):
                break
            else:
                print("This gate value wasn't one of the options.")
                yes_no()
        except ValueError:
            print("This isn't a number.")
            yes_no()

    return "/".join(min_gate.split("/")[:int_answer])

def find_parent_gate(start_gate_list, g_list, i_list):
    """Find parent gates for populations and return a list with indexes.

    The index will be used in calculate_cell_counts to index self.count_list"""
    calc_list = []
    for population in g_list:
        if population in start_gate_list:
            calc_list.append("start")
        elif population in i_list:
            calc_list.append("ignore")
        else:
            calc_list.append(g_list.index(population.rsplit("/", 1)[0]))
    return calc_list

def ask_group_identification(t_list):
    """Ask the user for the group id for the tubes and confirm it's correct."""

    for tube in t_list:
        tube.ask_group_id()

    while True:
        print("Are all of the groups correctly set for the tubes?")
        print("#\tTube Name\t\t\t\tGroup")
        for count, tube in enumerate(t_list, 1):
            print("{}\t{}\t\t{}".format(count, tube.n, tube.group_id))
        answer = input("> ").lower()
        if answer in ["yes", "y"]:
            break
        else:
            while True:
                print("Type the number for one of the incorrect tube(s).")
                num_answer = input("> ")
                try:
                    num_answer = int(num_answer)
                    if 0 < num_answer <= len(t_list):
                        break
                    else:
                        print("This isn't a number associated with a tube.")
                        yes_no()
                except ValueError:
                    print("This isn't a number.")
                    yes_no()
            to_fix = t_list[num_answer - 1]
            to_fix.ask_group_id()

    t_list.sort(key=lambda x: x.group_id)
    return(t_list)

def make_row_from_decimal(data, percents):
    """Make a list of strings from a list of Decimal objects."""
    row = []
    #to pay for using Decimal instead of floats, now have to convert to str
    for info in data:
        if percents:
            row.append(str(info * 100))
        else:
            row.append(str(info))
    return row

def make_compact_row_chunk(t_list, percent_bool):
    """Generate a compact row chunk for either the percents or counts."""
    content = []
    for tube in t_list:
        row = [tube.n]
        if grouping_bool:
            row.append(tube.group_id)
        if percent_bool:
            row.extend(make_row_from_decimal(tube.percent_list, percent_bool))
        else:
            row.extend(make_row_from_decimal(tube.count_list, percent_bool))
        row.append(str(tube.cell_conc))
        content.append(row)
    return content

def make_compact_csv_content(gate_list, tube_list):
    """Generate compact data content for the .csv output file.

    For csv.writer, each row must be a list, so content is a list of lists."""

    gate_list.insert(0, "Name")
    gate_list.append("Cell Concentration [10e4]")
    if grouping_bool:
        gate_list.insert(1, "Group")
    content_list = [["Percents"], gate_list]
    content_list.extend(make_compact_row_chunk(tube_list, True))
    content_list.extend([[""], ["Cell Numbers"], gate_list])
    content_list.extend(make_compact_row_chunk(tube_list, False))
    return content_list

def prism_chunk(header, obj_list, attr_func):
    """Generate the data for a gate for Prism.

    If there's no grouping, then iterate over the tube list.
    If there's grouping, then iterate over the row_matrix."""
    chunk = []
    if grouping_bool:
        chunk.extend([[], *header])
    else:
        chunk.extend([[], ["", header]])
    for obj in obj_list:
        if grouping_bool:
            temp = []
            for tube in obj:
                if tube:
                    temp.append(attr_func(tube))
                else:
                    temp.append("")
            chunk.append(temp)
        else:
            chunk.append([obj.n, attr_func(obj)])
    return chunk

def make_prism_csv_content(gate_list, tube_list):
    """Generate data content in a format easy to copy and paste into Prism.

    For csv.writer, each row must be a list, so content is a list of lists."""

    #This is the best I can do to balance readability and maintainability
    content = []
    if not grouping_bool:
        text = "Cell Concentration"
        func = (lambda x: x.cell_conc)
        content.extend(prism_chunk(text, tube_list, func))
        for count, gate in enumerate(gate_list):
            text = "% {}".format(gate)
            func = (lambda x: str(x.percent_list[count] * 100))
            content.extend(prism_chunk(text, tube_list, func))
        for count, gate in enumerate(gate_list):
            text = "# {}".format(gate)
            func = (lambda x: str(x.count_list[count]))
            content.extend(prism_chunk(text, tube_list, func))
    else:
        grouped_dict = {}
        for tube in tube_list:
            try:
                grouped_dict[tube.group_id].append(tube)
            except KeyError:
                grouped_dict[tube.group_id] = [tube]
        row_matrix = list(itertools.zip_longest(*grouped_dict.values()))
        group_order = [x.group_id for x in row_matrix[0]]
        #Tube ID
        text = ["Tube ID"], group_order
        func = (lambda x: x.n)
        content.extend(prism_chunk(text, row_matrix, func))
        #Cell Conc
        text = ["Cell Concentration"], group_order
        func = (lambda x: x.cell_conc)
        content.extend(prism_chunk(text, row_matrix, func))
        #Percents
        for count, gate in enumerate(gate_list):
            text = ["% {}".format(gate)], group_order
            func = (lambda x: str(x.percent_list[count] * 100))
            content.extend(prism_chunk(text, row_matrix, func))
        #Cell counts
        for count, gate in enumerate(gate_list):
            text = ["# {}".format(gate)], group_order
            func = (lambda x: str(x.count_list[count]))
            content.extend(prism_chunk(text, row_matrix, func))
    return content[1:]

def make_output_file(old_path, data):
    """Make a new output file and delete the original."""
    while True:
        print("What would you like to call the output file?")
        answer = input("> ")
        csv_answer = "{}.csv".format(answer)
        new_path = os.path.join(os.path.dirname(old_path), csv_answer)

        try:
            with open(new_path, "w") as f:
                file_content = csv.writer(f, lineterminator="\n")
                file_content.writerows(data)
            if not os.path.split(old_path)[1] == csv_answer:
                os.remove(old_path)
            break
        except IOError:
            print("Either the file is open or this isn't a valid filename.")
            yes_no()
    print("Done!")

def main():
    sys_arguments()
    p = ask_path()
    content = []
    with open(p, "r") as f:
        file_content = csv.reader(f)
        for x in file_content:
            content.append(x)
    gate_list, start_gates_dict, tube_list = process_csv(content)
    start_gate_list, ignore_list = check_starting_gate(start_gates_dict)
    calc_list = find_parent_gate(start_gate_list, gate_list, ignore_list)
    for tube in tube_list:
        tube.calculate_cell_counts(calc_list)
    if grouping_bool:
        tube_list = ask_group_identification(tube_list)
    if compact_bool:
        output = make_compact_csv_content(gate_list, tube_list)
    else:
        output = make_prism_csv_content(gate_list, tube_list)
    make_output_file(p, output)


if __name__ == "__main__":
    main()
