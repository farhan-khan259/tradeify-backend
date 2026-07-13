import random
import unittest

from app.main import generate_new_block


class TestAccountOutcomeBlocks(unittest.TestCase):
    def test_generate_new_block_has_five_wins_and_five_losses(self):
        block = generate_new_block()

        self.assertEqual(len(block), 10)
        self.assertEqual(block.count("W"), 5)
        self.assertEqual(block.count("L"), 5)

    def test_generate_new_block_stays_balanced_across_the_batch(self):
        for seed in range(50):
            random.seed(seed)
            block = generate_new_block()
            win_count_after_8 = block[:8].count("W")
            self.assertGreaterEqual(win_count_after_8, 3)
            self.assertLessEqual(win_count_after_8, 5)


if __name__ == "__main__":
    unittest.main()
