import unittest
from flat_bom_generator.tests.full_bom_part_13 import full_bom_part_13

class TestFullBOMPart13(unittest.TestCase):
    def test_total_unique_parts(self):
        # Each unique Component in the BOM is a unique part
        unique_parts = set(row['Component'] for row in full_bom_part_13)
        total_unique_parts = len(unique_parts)
        # The expected value should match the deduplicated unique part count
        # For the provided sample, there are 9 unique parts (from the 10 sample rows)
        # If more rows are added, update this expected value accordingly
        self.assertEqual(total_unique_parts, 9)

if __name__ == '__main__':
    unittest.main()
