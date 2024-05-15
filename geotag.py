""" Process Milepost Layer/Corrected Output and
GeoTag images """

#pylint: disable=E0401

from functools import lru_cache
from typing import Union, List
import os
import sys
import geopandas as gpd
import pandas as pds

WRK_DIR = "."
MP_GEO = os.path.join(WRK_DIR, "mileposts.gpkg")
CORRECTED = os.path.join(WRK_DIR, "corrected_full.tsv")
TAGGED = os.path.join(WRK_DIR, "geo_tagged.tsv")
TSV_HEADER = [
    'file',
    'lor',
    'seq',
    'elr',
    'm',
    'ch',
    'yds',
    'desc'
]

class GeoTag:
    """ GeoTag images """
    GEO = gpd.read_file(MP_GEO)
    TSV = pds.read_csv(CORRECTED, delimiter="\t", names=TSV_HEADER)

    @classmethod
    def _get_valid_elr_geo(cls) -> list:
        """ Returns a list of valid ELR codes """
        return list(GeoTag.GEO.filter(items=['ELR']).drop_duplicates()["ELR"])

    @classmethod
    def _get_elr_tsv(cls) -> list:
        """ Returns a list of ELR codes from TSV output """
        return list(GeoTag.TSV.filter(items=["elr"]).drop_duplicates()["elr"])

    def __init__(self):
        """ Initialisation """
        self.valid_elr = self._get_valid_elr_geo()
        self.output_elr = self._get_elr_tsv()

    def check_elr_errors(self) -> Union[None, List[str]]:
        """ Check for ELR errors """
        err = []
        for elr in self.output_elr:
            if elr not in self.valid_elr:
                err.append(elr)
        if not err:
            return None
        return err

    @lru_cache
    def return_matching_elr(self, elr: str) -> gpd.GeoDataFrame:
        """ Return matching geo records for elr """
        return self.GEO[self.GEO['ELR'] == elr]

    @staticmethod
    def closest_match(value: float, frame: gpd.GeoDataFrame):
        """ Return the Milepost Record which is the closest match """
        return frame.iloc[(frame['VALUE']-value).abs().argsort()[:1]]

    @staticmethod
    def format_as_tsv(values: list) -> str:
        """ Format for tsv entry """
        sep = '\t'
        values = [str(value) for value in values]
        return sep.join(values)

    @staticmethod
    def write_to_tsv(line: str) -> None:
        """ Append to the output file """
        with open(TAGGED, '+a', encoding='utf-8') as file:
            file.write(f'{line}\n')

    @staticmethod
    def return_coordinates(closest: gpd.GeoDataFrame) -> tuple:
        """ Extract coordinates and parent record """
        lon = closest.geometry.x.to_string()
        parent, lon = lon.split()
        lat = closest.geometry.y.to_string().split()[1]

        return (lon, lat, parent)

    def match_to_mp(self) -> pds.DataFrame:
        """ Match a TSV entry to a milepost """
        self.TSV.reset_index()
        for _, row in self.TSV.iterrows():
            elr = row.get('elr')
            miles = row.get('m')
            yards = row.get('yds')
            mileage = float(f'{miles}.{yards}')
            matches = self.return_matching_elr(elr)
            closest = self.closest_match(mileage, matches)
            row['lon'], row['lat'], row['parent'] = self.return_coordinates(closest)
            self.write_to_tsv(self.format_as_tsv(list(row)))

        return pds.read_csv(TAGGED, delimiter='\t', names=TSV_HEADER + ['lon', 'lat', 'parent'])

    def start_parse(self) -> None:
        """ Parse the data """
        elr_errors = self.check_elr_errors()
        if elr_errors:
            print(
                f"The following {len(elr_errors)} ELR(S) in '{CORRECTED}'\n",
                f"are not found in '{MP_GEO}'\n",
                f'{" ".join(elr_errors)}'
            )
            sys.exit(1)

        tagged = self.match_to_mp()
        print(tagged)

if __name__ == "__main__":
    tag = GeoTag()
    tag.start_parse()
