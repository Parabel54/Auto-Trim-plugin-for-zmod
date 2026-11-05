# Auto Trim load cell add-on for zMod (AD5X)
#
# The AD5X bed weighing board answers each reading request (H7) with
#   "command H7 ok. <raw count> <grams> g"
# The grams field comes in 20 g steps. The raw count is the sensor's own
# reading, about 43 counts per gram, so roughly a thousand times finer.
# zMod's load cell module (zmod_tenz) polls the board 5 times a second, keeps
# only the grams, drops their sign, and discards the raw count.
#
# This module does not open the serial port and sends nothing to the board.
# It wraps zmod_tenz's reply parser, so it sees every reply zMod already
# receives, and keeps the raw count. Macros can then read a precise, signed
# force:
#
#   printer.auto_trim_cell.force       grams since AUTO_TRIM_CELL_TARE, averaged
#                                      over the last `window` seconds
#   printer.auto_trim_cell.valid       True when readings are recent and tared
#   printer.auto_trim_cell.raw         latest raw count
#   printer.auto_trim_cell.board_grams latest grams field, with its sign
#   printer.auto_trim_cell.noise       standard deviation (g) over the window
#   printer.auto_trim_cell.rate        readings per second
#
# Commands:
#   AUTO_TRIM_CELL_TARE [SAMPLES=5]     zero the force on fresh readings
#   AUTO_TRIM_CELL_READ [SAMPLES=5]     report force, raw count and noise
#   AUTO_TRIM_CELL_CALIBRATE GRAMS=<g> [SAMPLES=10]
#       with a known weight on the bed, placed after AUTO_TRIM_CELL_TARE:
#       measures counts per gram (and its sign) and saves it
#
# Config (all optional):
#   [auto_trim_cell]
#   counts_per_gram: 43      # Kiln OS estimate; AUTO_TRIM_CELL_CALIBRATE
#                            # replaces it with this printer's own value
#   window: 1.0              # seconds averaged for `force`
#   stale_after: 1.5         # seconds without a reading before `valid` drops
#
# Depends on zMod's zmod_tenz module (its reply parser,
# extract_last_value_before_g). If a zMod update changes that, this module
# reports itself as not connected and Auto Trim falls back to the 20 g
# readings.
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import collections
import logging
import math
import re
import threading

# "<raw> <grams> g" at the end of the reply, as the board sends it
REPLY_RE = re.compile(r"(-?\d+)\s+(-?\d+(?:\.\d+)?)\s*g\b", re.IGNORECASE)
SAVE_VAR = "auto_trim_cell_cpg"
OVERLOAD_G = 5120.


def parse_reply(text):
    """(raw, grams) from an H7 reply, or None."""
    m = None
    for m in REPLY_RE.finditer(text or ""):
        pass
    if m is None:
        return None
    try:
        return int(m.group(1)), float(m.group(2))
    except ValueError:
        return None


class AutoTrimCell:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.reactor = self.printer.get_reactor()
        self.gcode = self.printer.lookup_object('gcode')
        self.cpg_config = config.getfloat('counts_per_gram', 43.)
        if self.cpg_config == 0.:
            raise config.error("auto_trim_cell: counts_per_gram can't be 0")
        self.cpg = self.cpg_config
        self.window = config.getfloat('window', 1.0, above=0.)
        self.stale_after = config.getfloat('stale_after', 1.5, above=0.)
        self.lock = threading.Lock()
        self.samples = collections.deque(maxlen=50)    # (time, raw, grams), about 10 s
        self.count = 0
        self.tare_raw = None
        self.hooked = False
        self.source = None
        self.printer.register_event_handler("klippy:connect", self._connect)
        self.mark_time = None
        self.measure = {'median': None, 'n': 0, 'sd': None}
        for cmd in ("AUTO_TRIM_CELL_TARE", "AUTO_TRIM_CELL_READ",
                    "AUTO_TRIM_CELL_CALIBRATE", "AUTO_TRIM_CELL_MARK",
                    "AUTO_TRIM_CELL_MEASURE"):
            self.gcode.register_command(cmd, getattr(self, "cmd_" + cmd),
                                        desc=getattr(self, "cmd_%s_help" % cmd))

    # Hooking into zmod_tenz
    def _find_reader(self):
        obj = self.printer.lookup_object('temperature_load weightValue', None)
        if obj is not None and hasattr(obj, 'extract_last_value_before_g'):
            return 'temperature_load weightValue', obj
        for name, obj in self.printer.lookup_objects():
            if name.startswith('temperature_load') and hasattr(
                    obj, 'extract_last_value_before_g'):
                return name, obj
        return None, None

    def _connect(self):
        sv = self.printer.lookup_object('save_variables', None)
        if sv is not None:
            saved = sv.allVariables.get(SAVE_VAR)
            if isinstance(saved, (int, float)) and saved != 0:
                self.cpg = float(saved)
        name, reader = self._find_reader()
        if reader is None:
            logging.warning("auto_trim_cell: zMod load cell reader "
                            "(zmod_tenz) not found; not connected")
            return
        original = reader.extract_last_value_before_g

        def wrapped(response, _original=original):
            # Runs in zmod_tenz's serial thread for every H7 reply
            try:
                self._capture(response)
            except Exception:
                logging.exception("auto_trim_cell: capture failed")
            return _original(response)
        reader.extract_last_value_before_g = wrapped
        self.hooked = True
        self.source = name
        logging.info("auto_trim_cell: reading raw counts from %s", name)

    def _capture(self, response):
        parsed = parse_reply(response)
        if parsed is None:
            return
        raw, grams = parsed
        # The board occasionally reports nonsense above about 5 kg; zMod
        # filters those, and they must not reach the force average either.
        if abs(grams) > OVERLOAD_G:
            return
        now = self.reactor.monotonic()
        with self.lock:
            self.samples.append((now, raw, grams))
            self.count += 1

    # Readings
    def _snapshot(self):
        with self.lock:
            return list(self.samples), self.count, self.tare_raw

    def _window_stats(self, samples, end, seconds):
        recent = [s for s in samples if s[0] >= end - seconds]
        if not recent:
            return None
        raws = [s[1] for s in recent]
        mean = sum(raws) / float(len(raws))
        var = sum((r - mean) ** 2 for r in raws) / float(len(raws))
        return mean, math.sqrt(var), recent

    def get_status(self, eventtime):
        samples, count, tare = self._snapshot()
        # Connected once readings arrive, not just once the reader is wrapped
        st = {'connected': self.hooked and count > 0, 'hooked': self.hooked, 'valid': False, 'tared':
              tare is not None, 'force': None, 'raw': None,
              'board_grams': None, 'noise': None, 'rate': 0.,
              'age': None, 'counts_per_gram': self.cpg, 'readings': count,
              'measure': dict(self.measure)}
        if not samples:
            return st
        last = samples[-1]
        age = eventtime - last[0]
        stats = self._window_stats(samples, last[0], self.window)
        st.update({'raw': last[1], 'board_grams': last[2],
                   'age': round(age, 3)})
        if stats is not None:
            mean, sd, recent = stats
            st['noise'] = round(sd / abs(self.cpg), 3)
            span = recent[-1][0] - recent[0][0]
            if len(recent) > 1 and span > 0:
                st['rate'] = round((len(recent) - 1) / span, 2)
            if tare is not None:
                st['force'] = round((mean - tare) / self.cpg, 2)
        st['valid'] = bool(self.hooked and tare is not None
                           and age <= self.stale_after)
        return st

    def _fresh_raw(self, gcmd, samples_wanted, timeout):
        """Mean and SD of raw counts from readings arriving after now."""
        if not self.hooked:
            raise gcmd.error("auto_trim_cell: not connected to zMod's load "
                             "cell reader (zmod_tenz)")
        self.printer.lookup_object('toolhead').wait_moves()
        start_count = self._snapshot()[1]
        start = self.reactor.monotonic()
        while True:
            samples, count, _ = self._snapshot()
            if count - start_count >= samples_wanted:
                break
            now = self.reactor.monotonic()
            if now - start > timeout:
                raise gcmd.error("auto_trim_cell: only %d of %d readings "
                                 "in %.0f s" % (count - start_count,
                                                samples_wanted, timeout))
            self.reactor.pause(now + 0.05)
        new = samples[-(count - start_count):]
        raws = [s[1] for s in new]
        mean = sum(raws) / float(len(raws))
        sd = math.sqrt(sum((r - mean) ** 2 for r in raws) / float(len(raws)))
        return mean, sd, len(raws)

    # Commands
    cmd_AUTO_TRIM_CELL_TARE_help = ("Zero the precise load cell force on "
                                    "fresh readings [SAMPLES=5] [OPTIONAL=1]")

    def cmd_AUTO_TRIM_CELL_TARE(self, gcmd):
        n = gcmd.get_int('SAMPLES', 5, minval=1, maxval=100)
        optional = gcmd.get_int('OPTIONAL', 0)
        try:
            mean, sd, got = self._fresh_raw(gcmd, n, 2. + n * 0.5)
        except gcmd.error as e:
            if not optional:
                raise
            # Used at print start: a stalled reader must not stop the print.
            # Without a fresh zero the force stays invalid and Auto Trim
            # uses the 20 g readings.
            with self.lock:
                self.tare_raw = None
            gcmd.respond_info("AUTO TRIM CELL: could not zero (%s); using "
                              "the 20 g readings for this print" % (e,))
            return
        with self.lock:
            self.tare_raw = mean
        gcmd.respond_info("AUTO TRIM CELL: zeroed on %d readings (raw %.1f, "
                          "noise %.2f g)" % (got, mean, sd / abs(self.cpg)))

    cmd_AUTO_TRIM_CELL_READ_help = ("Report the precise load cell force "
                                    "[SAMPLES=5]")

    def cmd_AUTO_TRIM_CELL_READ(self, gcmd):
        n = gcmd.get_int('SAMPLES', 5, minval=1, maxval=100)
        mean, sd, got = self._fresh_raw(gcmd, n, 2. + n * 0.5)
        tare = self._snapshot()[2]
        force = ("%.2f g" % ((mean - tare) / self.cpg)) if tare is not None \
            else "not zeroed (AUTO_TRIM_CELL_TARE)"
        gcmd.respond_info("AUTO TRIM CELL: force %s, raw %.1f, noise %.2f g "
                          "over %d readings, %.1f counts per gram"
                          % (force, mean, sd / abs(self.cpg), got, self.cpg))

    cmd_AUTO_TRIM_CELL_MARK_help = ("Mark the start of a measurement "
                                     "(AUTO_TRIM_CELL_MEASURE)")

    def cmd_AUTO_TRIM_CELL_MARK(self, gcmd):
        # Run after M400: the moves that follow start now
        self.mark_time = self.reactor.monotonic()

    cmd_AUTO_TRIM_CELL_MEASURE_help = ("Median force since AUTO_TRIM_CELL_MARK"
                                       " [SKIP=0.5]")

    def cmd_AUTO_TRIM_CELL_MEASURE(self, gcmd):
        # Run after M400: the readings between the mark (plus SKIP seconds
        # for the move to start) and now
        skip = gcmd.get_float('SKIP', 0.5, minval=0.)
        samples, count, tare = self._snapshot()
        if self.mark_time is None or tare is None:
            raise gcmd.error("auto_trim_cell: AUTO_TRIM_CELL_TARE and "
                             "AUTO_TRIM_CELL_MARK first")
        forces = [(raw - tare) / self.cpg for (t, raw, g) in samples
                  if t >= self.mark_time + skip]
        if forces:
            med = _median(forces)
            mean = sum(forces) / float(len(forces))
            sd = math.sqrt(sum((f - mean) ** 2 for f in forces)
                           / float(len(forces)))
            self.measure = {'median': round(med, 2), 'n': len(forces),
                            'sd': round(sd, 2)}
        else:
            self.measure = {'median': None, 'n': 0, 'sd': None}
        self.mark_time = None

    cmd_AUTO_TRIM_CELL_CALIBRATE_help = ("Measure counts per gram with a "
                                         "known weight on the bed: GRAMS=")

    def cmd_AUTO_TRIM_CELL_CALIBRATE(self, gcmd):
        grams = gcmd.get_float('GRAMS', above=0.)
        n = gcmd.get_int('SAMPLES', 10, minval=3, maxval=100)
        tare = self._snapshot()[2]
        if tare is None:
            raise gcmd.error("auto_trim_cell: zero first with an empty bed "
                             "(AUTO_TRIM_CELL_TARE), then place the weight")
        mean, sd, got = self._fresh_raw(gcmd, n, 2. + n * 0.5)
        delta = mean - tare
        if abs(delta) < 5 * max(sd, 1.):
            raise gcmd.error("auto_trim_cell: the reading barely changed "
                             "(%.1f counts). Is the weight on the bed?"
                             % (delta,))
        self.cpg = delta / grams
        if self.printer.lookup_object('save_variables', None) is not None:
            self.gcode.run_script_from_command(
                "SAVE_VARIABLE VARIABLE=%s VALUE=%.4f" % (SAVE_VAR, self.cpg))
        gcmd.respond_info("AUTO TRIM CELL: %.3f counts per gram (%s), from "
                          "%.1f counts for %.1f g; saved"
                          % (self.cpg, "pressing raises the count"
                             if self.cpg > 0 else "pressing lowers the count",
                             delta, grams))


def _median(values):
    v = sorted(values)
    n = len(v)
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2.


def load_config(config):
    return AutoTrimCell(config)
