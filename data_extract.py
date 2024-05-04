""" Get data from exported Table A drawings """

# pylint: disable=E0401, W0621

import re
from typing import List, Union
from collections import namedtuple
import os
from pandas import DataFrame

from img2table.tables.objects.extraction import ExtractedTable
from img2table.document import Image

from easy_ocr import EasyOcrCustom


WORKDIR = '.'
IMAGES = 'processed'
FAILED = 'failed_meta'
META = 'meta'
PATH = os.path.join(WORKDIR, IMAGES)
IMAGE = os.path.join(PATH, 'EA1010-001.png')

VALID_MILEAGE = re.compile("[0-9]{1,3}[ ]{1,}[0-9]{1,4}")
MILEAGE_HEADER = re.compile('[M]?.[Ch]{?}')
FILTERED_MILEAGE = re.compile(r'[\d\s]+')
ELR = re.compile("[A-Z]{3}[0-9]?")
TSV = os.path.join(WORKDIR, 'output.tsv')

Mileage = namedtuple('Mileage', 'miles, chains, yards')

for path in [
        os.path.join(WORKDIR, META),
        os.path.join(WORKDIR, IMAGES),
        os.path.join(WORKDIR, FAILED),
    ]:
    if not os.path.isdir(path):
        os.mkdir(path)

reader = EasyOcrCustom(lang=['en'])

meta = {}

def get_images() -> list:
    """ Gets a list of all images """
    return sorted([image for image in os.listdir(PATH) if '.png' in image])

def default_mileage_parse(raw: str) -> Union[Mileage, None]:
    """ Attempt to get a default mileage """

    matches = VALID_MILEAGE.findall(raw)
    if not matches:
        return None
    split = matches[0].split()
    yards = int(split[1]) * 22
    return Mileage(split[0], split[1], yards)

def format_raw_mileage(raw: str) -> Union[list, None]:
    """ Format raw mileage for further parsing """
    raw = re.sub('\n', ' ', raw)
    regexp = re.compile(r"[0-9]{2}[  *]+")
    if not regexp:
        return None
    return [srch.strip() for srch in regexp.findall(raw)]

def extract_star_mileage(raw: list) -> Union[List, None]:
    """ Look for likely star mileages """
    try:
        for pos in range(len(raw), 0, -1):
            if '*' in raw[pos - 1]:
                chains = re.findall('[0-9]{2}', raw[pos - 1])
                miles = re.findall('[0-9]{2}', raw[pos - 2])
                return [miles[0], chains[0]]
    except IndexError:
        return None
    return None

def parse_mileages(raw: str) -> List[Union[Mileage, None]]:
    """ Parse the mileages, return as a list """

    if not raw:
        return [None]

    # Step one, attempt to get a valid mileage
    match = default_mileage_parse(raw)
    if match:
        return [match]

    # Step two, refine step one
    filtered = format_raw_mileage(raw)
    if filtered:
        match = extract_star_mileage(filtered)
        if match:
            return [
                Mileage(
                    match[0],
                    match[1],
                    int(match[1]) * 22
                )
            ]

    # step three, attempt matching pairs
    ret_val = []
    filtered = FILTERED_MILEAGE.findall(raw)
    if not filtered:
        return [None]
    filtered = [filtered.replace('\n', '') for filtered in filtered]

    miles = filtered[::2]
    chains = filtered[1::2]
    if not len(miles) == len(chains):
        return [None]

    for index, element in enumerate(miles):
        ret_val.append(
            Mileage(
                element,
                chains[index],
                int(chains[index]) * 22
            )
        )
    return ret_val

def parse_description(raw: str) -> Union[str, None]:
    """ Parse the description """
    if not raw:
        return None
    raw = raw.strip()
    if '|' in raw:
        split = raw.split('|')
        raw = split[-1].strip()
    return raw.replace('\n', ' ')

def generic_crawler(frame: DataFrame, search_str: str = 'Route') -> Union[str, None]:
    """ Returns corresponding column data when header matches """
    cols = list(frame)
    for i in cols:
        value = frame[i][0]
        if not value:
            return None
        if search_str in value:
            return frame[i][1]
    return None

def crawl_for_description(frame: DataFrame) -> str:
    """ Find and return the raw description data """
    return generic_crawler(frame, 'Route')

def crawl_for_elr(frame: DataFrame) -> Union[str, None]:
    """ Find and return the raw ELR data """
    return generic_crawler(frame, 'ELR')

def crawl_for_mileage(data: DataFrame) -> Union[str, None]:
    """ Find and return the raw mileage data """
    columns = list(data)
    for i in columns:
        value = data[i][2]
        value = value.replace('\n', '')
        value = value.replace(' ', '')
        ret_val = ''
        if 'MCh' in value:
            for row in range(3, len(data)):
                blob = data[i][row]
                if not blob:
                    return None
                if blob not in ret_val:
                    ret_val += blob
            return ret_val
    return None

def extract_values(frame: DataFrame) -> dict:
    """ Extract the required raw values from the dataframe """
    return {
        'raw_desc': crawl_for_description(frame),
        'raw_mileages': crawl_for_mileage(frame),
        'raw_elr':crawl_for_elr(frame)
    }

def parse_image(file: str) -> ExtractedTable:
    """ Extract the data from the image """
    doc = Image(file)
    extracted_tables = doc.extract_tables(
        ocr=reader,
        implicit_rows=True,
        borderless_tables=True,
        min_confidence=50
    )

    return extracted_tables[0]

def move_folder(full_path: str, file_path: str, folder: str = META) -> None:
    """ Move to the specified folder """
    os.rename(full_path, os.path.join(WORKDIR, folder, file_path))

def parse_elr(raw: str) -> Union[List[str], None]:
    """ Parse the ELR references """
    if not raw:
        return [None]
    matches = ELR.findall(raw)
    if not matches:
        return [None]
    return matches

def update_csv(filename: str, elr: str, mileage: float, description: str):
    """ Write the data to the csv file """
    with open(TSV, 'a', encoding='utf-8') as file:
        lor, seq = filename.split('-')
        file.write(f'{filename}\t{lor}\t{seq.strip(".png")}\t{elr}\t{mileage}\t{description}\n')

def write_to_csv(
        filename: str,
        elr: List[Union[str, None]],
        mileage: List[Union[Mileage, None]],
        description: str
    ):
    """ Writes the data to the csv file """
    lor, seq = filename.split('-')
    seq = seq.strip(".png")

    elr = elr[0] or 'Undefined'

    miles: str = 'Undefined'
    chains: str = 'Undefined'
    yards: str = 'Undefined'

    if isinstance(mileage[0], Mileage):
        miles = mileage[0].miles
        chains = mileage[0].chains
        yards = mileage[0].yards

    description = description or 'Undefined'

    to_write: str = (
        f'{filename}\t',
        f'{lor}\t',
        f'{seq}\t',
        f'{elr}\t',
        f'{miles}\t',
        f'{chains}\t',
        f'{yards}\t',
        f'{description}\n'
    )

    with open(TSV, 'a', encoding='utf-8') as file:
        file.write(''.join(to_write))

def run_extract(file: str) -> dict:
    """ Run the process for the provided file """

    print(f'Processing: {file}')
    extract = parse_image(file)

    values = extract_values(extract.df)
    print(f'\t{values}')

    description = parse_description(values.get('raw_desc'))
    print(f'\t\t{description}')

    elr = parse_elr(values.get('raw_elr'))
    print(f'\t\t{elr}')

    mileages = parse_mileages(values.get('raw_mileages'))
    print(f'\t\t{mileages}')

    write_to_csv(
        os.path.basename(file),
        elr,
        mileages,
        description
    )

    if not all([description, elr[0], mileages[0]]):
        print('\t\tFAILED!')
        move_folder(file, os.path.basename(file), FAILED)
        return

    move_folder(file, os.path.basename(file))

def multiple_run() -> None:
    """ Run on all files in the processed directory """
    for image in get_images():
        run_extract(os.path.join(PATH, image))

if __name__ == '__main__':
    multiple_run()
