#!/bin/python3
import argparse
import csv

"""
Converts a portal-switches-and-settings.csv file into a rst sections.
Using the portal-switches-and-settings.csv directly as a table resulted in a too wide table because of incorrect line
wraps.
"""

parser = argparse.ArgumentParser(
    description='Converts a portal-switches-and-settings.csv file into a rst sections.'
)
parser.add_argument('filename', help='portal-switches-and-settings.csv file location.')
args = parser.parse_args()

with open(args.filename, newline='') as f:
    reader = csv.reader(f)
    for row in reader:
        setting = row[0]
        default = row[1]
        comment = row[2]

        print(setting)
        print('"' * len(setting))
        print(f'\n\nDefault: *{default}*\n\n')
        print(f'{comment}\n\n')
