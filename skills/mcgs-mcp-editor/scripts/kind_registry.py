"""Verified WndUser kind registry: kind -> class, family, patchable edits.

Evidence: Ghidra 12.1.4 ctor decompilations of McgsSetPro.exe
(a8e1ce78535ea3db0ca5fdb54306df7f9b56f298ca1025f2e20e337347fd6f54);
each class ctor pushes its kind constant then installs its vftable.
2026-10-17 official Samples: 18 files, 143 windows, 136 fully parsed,
7 rejected; 4099 records and 21 kinds in the successful windows only.
The third-party 0x5026 = CDrawFlow has host ctor and plugin type evidence.
Its exact MCP serialization is not yet mapped, so explicit edits remain
blocked. Variable-length data can have equal-length instances; length
variation is not proof that a type can never become editable.
See ../references/format.md for evidence levels and layout limits.

Policy (fail-closed):
- string: registered kinds except the currently blocked 0x5026;
  variable-length text changes are only
  allowed where nested length behavior is proven (label/input/button);
  other kinds accept same-length text only (delta 0 cannot shift offsets).
- rectangle: verified int32 x4 layouts only; the profile supplies the
  independently checked offset (label +12, most widgets +24, DLL either).
- horizontal_move: only 0x5004/0x5006; shape_geometry additionally pins a
  specimen fingerprint and refuses changed style, name, size or vertical position.
- input_binding / input_range: 0x5025 only (binding ID + [max,min] proven).
- event (source + compiled array): 0x5027 only (nested length behavior proven).
Unknown kinds are always rejected; offsets still come from the profile,
never inferred here.
"""
import struct

KIND_CLASSES = {
    0x5002: 'CDrawLine',
    0x5004: 'CDrawRect',
    0x5005: 'CDrawRoundRect',
    0x5006: 'CDrawEllipse',
    0x5008: 'CDrawLabel',
    0x5009: 'CDrawBitmap',
    0x5023: 'CDrawBall3D',
    0x5025: 'CDrawEdit',
    0x5026: 'CDrawFlow',
    0x5027: 'CDrawButton',
    0x5028: 'CDrawMulBtn',
    0x5029: 'CDrawSlider',
    0x502A: 'CDrawMulDis',
    0x502D: 'CDrawPic',
    0x502E: 'CDrawHisPic',
    0x5031: 'CDrawSliderFill',
    0x5032: 'CDrawRotateTbl',
    0x5033: 'CDrawSaveData',
    0x5039: 'CDrawCell',
    0x503A: 'CDrawUnit',
    0x503C: 'CDrawComboBox',
    0x503D: 'CDrawDll',
}

# int32 (left, top, right, bottom); offsets are profile-specific, not selected
# by kind. Label samples use +12; DLL samples include both +12 and +24.
# 0x503C's 498B +24 sample has host move/width feedback. This set does not
# extend that evidence to other layouts or to the experimental shape kinds.
RECT_WIDGETS = {0x5008, 0x5025, 0x5027, 0x5028, 0x503C, 0x503D}

# Geometry candidates at +12/+16/+20/+24; low-word variation alone does
# not prove field width or signedness. No general rectangle edits for these kinds;
# two exact specimens have a separate horizontal_move operation.
# New-kind field positions come from native-sample cross-file groups.
SHAPE_KINDS = {0x5002, 0x5004, 0x5005, 0x5006, 0x5009, 0x5023, 0x5029,
               0x502A, 0x502D, 0x502E, 0x5031, 0x5032, 0x5033, 0x503A}

# Variable-length text proven safe (nested counts understood).
VARLEN_TEXT_KINDS = {0x5008, 0x5025, 0x5027}

INPUT_KINDS = {0x5025}
BUTTON_KINDS = {0x5027}


def _units(text):
    return len(text.encode('utf-16le')) // 2


# No explicit field edits have been validated for these kinds. Keep this
# exported name for compatibility; it is a current gate, not a permanent
# claim that future field evidence is impossible.
NEVER_EDITABLE = {0x5026}


def check_patchable(kind, edits):
    """Raise ValueError unless every edit is proven-safe for kind."""
    if kind not in KIND_CLASSES:
        raise ValueError('Unknown control kind %s; refusing' % hex(kind))
    if kind in NEVER_EDITABLE and edits:
        raise ValueError('%s (%s) has no verified writable MCP layout; '
                         'no edit is proven safe'
                         % (hex(kind), KIND_CLASSES[kind]))
    for edit in edits or []:
        etype = edit.get('type')
        if etype == 'string':
            if kind not in VARLEN_TEXT_KINDS and \
                    _units(edit.get('value', '')) != _units(edit.get('expected', '')):
                raise ValueError('Only same-length text is allowed for %s (%s)'
                                 % (hex(kind), KIND_CLASSES[kind]))
        elif etype == 'rectangle':
            if kind not in RECT_WIDGETS:
                raise ValueError('int32 rectangle not verified for %s (%s)'
                                 % (hex(kind), KIND_CLASSES[kind]))
        elif etype == 'horizontal_move':
            from shape_geometry import HORIZONTAL_SAMPLES
            if kind not in HORIZONTAL_SAMPLES:
                raise ValueError('Horizontal move not verified for %s' % hex(kind))
        elif etype in ('input_binding', 'input_range'):
            if kind not in INPUT_KINDS:
                raise ValueError('%s is only proven for numeric input 0x5025' % etype)
        elif etype == 'event':
            if kind not in BUTTON_KINDS:
                raise ValueError('event edit is only proven for standard button 0x5027')
        else:
            raise ValueError('Unsupported edit type: %s' % etype)
    return KIND_CLASSES[kind]
