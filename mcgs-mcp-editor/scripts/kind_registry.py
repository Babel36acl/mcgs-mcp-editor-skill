"""Verified WndUser kind registry: kind -> class, family, patchable edits.

Evidence: Ghidra 12.1.4 ctor decompilations of McgsSetPro.exe
(a8e1ce78535ea3db0ca5fdb54306df7f9b56f298ca1025f2e20e337347fd6f54);
each class ctor pushes its kind constant then installs its vftable.
Field islands per kind come from equal-length multi-record alignment
of real MCPs (see scratch group_align reports).

Policy (fail-closed):
- string: all registered kinds, but variable-length text changes are only
  allowed where nested length behavior is proven (label/input/button);
  other kinds accept same-length text only (delta 0 cannot shift offsets).
- rectangle (int32 x4 @ payload+24): widget kinds with verified rect only.
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

# int32 (left, top, right, bottom) @ payload+24, verified by alignment.
RECT_WIDGETS = {0x5008, 0x5025, 0x5027, 0x5028, 0x503D}

# u16 geometry words @ payload+12..24, int32 rect does NOT apply here.
SHAPE_KINDS = {0x5002, 0x5004, 0x5005, 0x502A, 0x5031}

# Variable-length text proven safe (nested counts understood).
VARLEN_TEXT_KINDS = {0x5008, 0x5025, 0x5027}

INPUT_KINDS = {0x5025}
BUTTON_KINDS = {0x5027}


def _units(text):
    return len(text.encode('utf-16le')) // 2


def check_patchable(kind, edits):
    """Raise ValueError unless every edit is proven-safe for kind."""
    if kind not in KIND_CLASSES:
        raise ValueError('Unknown control kind %s; refusing' % hex(kind))
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
        elif etype in ('input_binding', 'input_range'):
            if kind not in INPUT_KINDS:
                raise ValueError('%s is only proven for numeric input 0x5025' % etype)
        elif etype == 'event':
            if kind not in BUTTON_KINDS:
                raise ValueError('event edit is only proven for standard button 0x5027')
        else:
            raise ValueError('Unsupported edit type: %s' % etype)
    return KIND_CLASSES[kind]
