""" Update failed meta information """

from typing import List, Union
from collections import namedtuple
import csv
import os

OUTPUT_DIR = '.'
TSV = 'output.tsv'
CORRECTED_FILE = os.path.join(OUTPUT_DIR, 'corrected.tsv')
FULL_PATH = os.path.join(OUTPUT_DIR, TSV)
NOT_SET_KW = 'Undefined'
Record = namedtuple('Record', 'file, lor, seq, elr, m, ch, yds, desc')
processed = []

def import_records() -> list:
    """ Parse the records from the TSV file """

    with open(TSV, '+r', encoding='utf-8') as tsv:
        reader = csv.reader(tsv, delimiter='\t')
        return list(reader)

def parse_records(rows: list) -> List[Record]:
    """ Return list of Records """
    return [Record(*row) for row in rows]

def prompt(name: str, default: Union[str, None] = None, rec: bool = False) -> Union[str, None]:
    """ Standard prompt for data correction """

    if not rec:
        print(f'\t{name} not specified')

    if default and NOT_SET_KW not in default:
        resp = input(f'\t\tUse "{default}" (Y/N)? ')
        if resp.strip() == 'Y':
            return default

    next_prompt = input(f'\t\tEnter the value for {name}: ')
    value = prompt(name, next_prompt, True)
    return value


def correct_undef(record: Record, cur_elr: str, cur_desc: str):
    """ Prompt for value correction where needed """

    print()
    print(record)

    elr = record.elr
    if NOT_SET_KW in elr:
        elr = prompt('ELR', cur_elr)
        cur_elr = elr

    desc = record.desc
    if NOT_SET_KW in desc:
        desc = prompt('Description', cur_desc)
        cur_desc = desc

    miles = record.m
    if NOT_SET_KW in miles:
        miles = prompt('Miles', miles)

    chains = record.ch
    yards = record.yds
    if NOT_SET_KW in chains:
        chains = prompt('Chains', chains)
        yards = int(chains) * 22

    return Record(
        record.file,
        record.lor,
        record.seq,
        elr,
        miles,
        chains,
        yards,
        desc
    )

def write_to_tsv() -> None:
    """ Output to the correct file/format """

    for record in processed:
        to_write: str = (
            f'{record.file}\t',
            f'{record.lor}\t',
            f'{record.seq}\t',
            f'{record.elr}\t',
            f'{record.m}\t',
            f'{record.ch}\t',
            f'{record.yds}\t',
            f'{record.desc}\n'
        )
        with open(CORRECTED_FILE, 'a', encoding='utf-8') as file:
            file.write(''.join(to_write))

def main():
    """ Entrypoint """
    records = parse_records(import_records())

    cur_elr: str = 'Undefined'
    cur_desc: str = 'Undefined'

    for record in records:

        if NOT_SET_KW not in record:
            processed.append(record)
            cur_elr = record.elr
            cur_desc = record.desc
            continue

        correction = correct_undef(record, cur_elr, cur_desc)
        if isinstance(correction, Record):
            cur_elr = correction.elr
            cur_desc = correction.desc
            processed.append(correction)

    write_to_tsv()


if __name__ == "__main__":
    main()
