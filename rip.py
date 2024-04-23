""" Extracts Section Appendix Table A drawings from pdf """

# pylint: disable=R1713, E0401

from collections import namedtuple
import os
import re
from typing import Union
import datetime
import easyocr
from tqdm import tqdm
import fitz

reader = easyocr.Reader(['en'], gpu=True)
TableA = namedtuple('TABLE_A', 'file_path, lor, seq, updated')

LOR = ['CY', 'EA', 'GW', 'LN', 'MD', 'NW', 'NZ', 'SC', 'SO', 'SW', 'XR']
VALID_SEQ = re.compile("^[O0-9]{3}$")
VALID_DATE = re.compile("[0-9]{2}/[0-9]{2}/[0-9]{4}")
WORKDIR = '.'
START_PAGE = 660
END_PAGE = 699
FAILED = '/failed/'
PROCESSED = '/processed/'

def get_updated_date(values: list) -> Union[str, None]:
    """ Strips the updated date from the table A drawing """
    for data in values:
        result = VALID_DATE.match(data)
        if result:
            return result.group()
    return None

def create_regex() -> str:
    """ Create the regex search string """
    lor_str = ""
    for lor in LOR:
        lor_str += f"{lor}|"
    return f"^({lor_str[:-1]}){{1}}[O0-9]{{3}}$"

VALID_LOR = re.compile(create_regex())

def get_lor(values: list) -> Union[str, None]:
    """ Attempts to find the LOR code """
    for data in values:
        result = VALID_LOR.match(data)
        if result:
            return result.group()
    return None

def get_seq(values:list) -> Union[str, None]:
    """ Returns the sequence number """
    for data in values:
        result = VALID_SEQ.match(data)
        if result:
            return result.group()
    return None

def format_filename(table_a: TableA) -> str:
    """ Returns the filename in the correct format """

    return f'{table_a.lor}-{table_a.seq}.png'

def strip_images(all_pages: bool = False) -> None:
    """ Strip all images and place in the image directory """

    for each_path in os.listdir(WORKDIR):
        if ".pdf" in each_path:
            doc = fitz.Document((os.path.join(WORKDIR, each_path)))
            if all_pages:
                rng = range(len(doc))
            else:
                rng = range(START_PAGE, END_PAGE)
            for i in tqdm(rng, desc="pages"):
                for img in tqdm(doc.get_page_images(i), desc="page_images"):

                    xref = img[0]

                    save_path = os.path.join(WORKDIR + '/images/')
                    tmp_filename = f'{each_path[:-4]}_p{i}-{xref}.png'
                    full_path = os.path.join(save_path, tmp_filename)

                    pix = fitz.Pixmap(doc, xref)
                    pix.save(full_path)

def move_folder(full_path: str, file_path: str, folder: str = FAILED) -> None:
    """ Move to the specified folder """
    os.rename(full_path, os.path.join(WORKDIR + folder, file_path))

def update_created_datetime(file_name: str, table_a: TableA) -> None:
    """ Update the created datetime """
    full_path = os.path.join(WORKDIR + PROCESSED, file_name)
    dt = datetime.datetime.strptime(table_a.updated, '%d/%m/%Y')
    os.utime(full_path, (dt.timestamp(), dt.timestamp()))
    print(full_path)

def does_file_exist(file_name: str, folder: str = PROCESSED) -> bool:
    """ Returns True is the filename already exists """
    full_path = os.path.join(WORKDIR + folder, file_name)
    return os.path.isfile(full_path)

def rename_images() -> None:
    """ Renames all table A images """
    for each_path in os.listdir(os.path.join(WORKDIR, 'images/')):
        full_path = os.path.join(WORKDIR + '/images/', each_path)
        if ".png" in each_path:
            result = reader.readtext(full_path, detail=0)

            if not 'LOR' in result:
                move_folder(full_path, each_path, FAILED)
                continue

            table_a = TableA(
                each_path,
                get_lor(result).replace('O', '0'),
                get_seq(result).replace('O', '0'),
                get_updated_date(result)
            )

            if not all(table_a):
                move_folder(full_path, each_path, FAILED)
                print(result)
                continue

            print(table_a)
            new_file_name = format_filename(table_a)

            if does_file_exist(new_file_name):
                move_folder(full_path, each_path, FAILED)
                print(f'File already exist: {new_file_name}')
                continue

            move_folder(full_path, new_file_name, PROCESSED)
            update_created_datetime(new_file_name, table_a)

if __name__ == "__main__":
    strip_images(all_pages=True)
    rename_images()
