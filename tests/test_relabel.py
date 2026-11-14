# analyze.py --relabel: a label judged after the print replaces the one
# recorded during it, for first-layer readings at that offset.
import unittest
import analyze

def row(z, label='GOOD', layer=1):
    return dict(layer=layer, offset_z=z, label=label, label_source='held_through_first_layer',
                label_inferred=True, rejection='', eligible=True)

class RelabelTests(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(analyze.parse_relabel(['-0.125=too_low', '0.01=GOOD']), [(-0.125, 'TOO_LOW'), (0.01, 'GOOD')])
        for bad in ('-0.125', 'x=GOOD', '-0.1=BAD', 'nan=GOOD'):
            with self.assertRaises(ValueError):
                analyze.parse_relabel([bad])

    def test_first_layer_readings_at_that_offset_are_relabelled(self):
        runs = [dict(samples=[row(-0.125), row(-0.125), row(-0.12), row(-0.125, layer=2), row(-0.1252)])]
        counts = analyze.apply_relabel(runs, [(-0.125, 'TOO_LOW')])
        labels = [(r['offset_z'], r['layer'], r['label']) for r in runs[0]['samples']]
        self.assertEqual(labels, [(-0.125, 1, 'TOO_LOW'), (-0.125, 1, 'TOO_LOW'), (-0.12, 1, 'GOOD'), (-0.125, 2, 'GOOD'), (-0.1252, 1, 'TOO_LOW')])
        self.assertEqual(counts, {'-0.1250=TOO_LOW': 3})
        r = runs[0]['samples'][0]
        self.assertEqual(r['label_source'], 'relabelled_after_print'); self.assertFalse(r['label_inferred'])

    def test_travel_and_transition_labels_are_left_alone(self):
        runs = [dict(samples=[row(-0.125, 'TRAVEL'), row(-0.125, 'TRANSITION'), row(-0.125, 'UNLABELLED')])]
        analyze.apply_relabel(runs, [(-0.125, 'TOO_LOW')])
        self.assertEqual([r['label'] for r in runs[0]['samples']], ['TRAVEL', 'TRANSITION', 'TOO_LOW'])

    def test_unlabelled_reason_is_cleared(self):
        runs = [dict(samples=[dict(row(-0.125, 'UNLABELLED'), rejection='unlabelled_or_transition', eligible=False)])]
        analyze.apply_relabel(runs, [(-0.125, 'TOO_LOW')])
        r = runs[0]['samples'][0]
        self.assertTrue(r['eligible']); self.assertEqual(r['rejection'], '')

if __name__ == '__main__':
    unittest.main()
