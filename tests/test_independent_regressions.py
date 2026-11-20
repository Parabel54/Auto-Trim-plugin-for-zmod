"""Independent acceptance checks written against beta 10.2.3 (archive note 31),
the two vibration gate checks removed with the gate in 10.2.7;
kept as regression tests since 10.2.5, where they pass. Originally:
independent acceptance checks against the unmodified uploaded beta 10.2.3.

These tests assert desired behavior and are expected to fail on the reviewed
release. Reuse its simulated printer fixtures, not its assertions about behavior.
DC_REVIEW_SOURCE selects an extracted source directory for reproduction.
"""
import os
from pathlib import Path
import sys
from unittest import mock

SOURCE = Path(os.environ.get('DC_REVIEW_SOURCE', Path(__file__).resolve().parents[1]))
sys.path[:0] = [str(SOURCE / 'tests'), str(SOURCE)]
import test_continuous_sensors as continuous
import vibration_analysis as analysis


def test_one_cumulative_overflow_does_not_stop_recording():
    # Native FixedFreqReader retains last_overflows until note_start(). The
    # sequence 1,1,1,1 therefore represents one overflow, not four new events.
    fixture = continuous.ContinuousTests()
    fixture.setUp()
    try:
        fixture.start()
        for batch in range(4):
            fixture.bulk.publish(fixture.rows(batch * 160), overflows=1)
            fixture.base.feed()
        assert fixture.cell.active, fixture.cell.sensors.error
        assert fixture.cell.sensors.overflows_total == 1
    finally:
        fixture.doCleanups()




def test_analysis_excludes_overflow_marked_windows_even_without_timestamp_gap(tmp_path):
    # Lost conversions need not leave an obvious timestamp gap after the
    # native clock regression; driver evidence must also exclude the window.
    path = tmp_path / 'run.jsonl'
    (tmp_path / 'run.accel.0000.dca').touch()
    rows = [dict(t=100. + i / 1600., x=0., y=0., z=9800., errors=0,
                 overflows=int(160 <= i < 320)) for i in range(640)]
    run = dict(path=str(path), complete=True,
               metadata=dict(sensor_capture=dict(acceleration=True)),
               samples=[dict(print_time=100.3, raw=1, filtered_raw=1,
                             label='UNLABELLED', offset_z=0.)],
               events=[dict(event='session_end', sensor_capture=dict(frames_received=640))])
    with mock.patch.object(analysis, 'read_acceleration', return_value=iter(rows)):
        result = analysis.analyze_vibration(run, tmp_path)
    assert result['matched_force_intervals'] == 0, result
