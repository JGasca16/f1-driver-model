"""Small checks for the new inspection charts; existing outputs stay untouched."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd
from PIL import Image

import make_sanity_charts as charts


class SanityChartTests(unittest.TestCase):
    def test_four_pngs_are_created_at_150_dpi_and_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'charts'
            with contextlib.redirect_stdout(io.StringIO()):
                charts.make_charts(output_dir=output)
            self.assertEqual({p.name for p in output.iterdir()}, set(charts.FILENAMES))
            for name in charts.FILENAMES:
                with Image.open(output/name) as image:
                    self.assertEqual(image.format, 'PNG')
                    self.assertGreater(image.width, 1000)
                    self.assertAlmostEqual(image.info['dpi'][0], 150, places=1)
                    image.verify()
            with self.assertRaises(FileExistsError):
                charts.make_charts(output_dir=output)

    def test_order_stays_within_groups_instead_of_global_score_sort(self):
        rows = pd.DataFrame({
            'driver':['B1','A1','B2','A2'],
            'comparison_group':['B','A','B','A'],
            'combined_rating':[-2,2,-3,1],
        })
        order = charts.grouped_driver_order(rows)
        self.assertEqual(order.driver.tolist(), ['A2','A1','B2','B1'])
        self.assertEqual(order.comparison_group.tolist(), ['A','A','B','B'])

    def test_pair_perspective_and_missing_rounds(self):
        dry = pd.DataFrame([dict(driver='B',teammate='A',round_number=2,
                                 final_gap=10.,final_se_pp=1.,method_used='strict')])
        series = charts.pair_series(dry,'A','B')
        self.assertAlmostEqual(series.loc[2,'gap'], -1000/110)
        self.assertAlmostEqual(series.loc[2,'se'], 1/1.1**2)
        self.assertTrue(np.isnan(series.loc[1,'gap']))
        self.assertTrue(np.isnan(series.loc[3,'gap']))

    def test_coverage_distinguishes_missing_signals_from_not_entered(self):
        ratings = pd.DataFrame({'driver':['A','B','C']})
        quali = pd.DataFrame({'driver':['A','B'], 'round_number':[1,1],
                              'combined_gap':[np.nan,np.nan]})
        dry = pd.DataFrame({'driver':['A'],'teammate':['B'],
                            'round_number':[1],'final_gap':[.1]})
        wet = pd.DataFrame(columns=['driver','teammate','round_number','wet_gap_2pct'])
        drivers, matrix = charts.coverage_data(ratings,quali,dry,wet)
        self.assertEqual(drivers,['A','B','C'])
        self.assertEqual(matrix[:,0].tolist(),[2,2,-1])


if __name__ == '__main__':
    unittest.main()
