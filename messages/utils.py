from django.db import transaction

from .models import Group, GroupType


DEFAULT_GROUPS = (
    (GroupType.PRIVATE, "Private group (uses NID, no distance)."),
    (GroupType.EXCLUSIVE, "Exclusive group (uses NID, no distance)."),
    (GroupType.OPEN, "Open group (uses distance only)."),
    (GroupType.DATA_LOGGING, "Data Logger group (uses NID, no distance)."),
    (GroupType.ENHANCED, "Enhanced group (uses NID and distance)."),
    (GroupType.LOCATION, "Location group (uses NID and distance)."),
)


def ensure_default_groups():
    """Create baseline groups if none exist yet."""
    if Group.objects.exists():
        return False

    with transaction.atomic():
        for group_type, description in DEFAULT_GROUPS:
            Group.objects.create(group_type=group_type, description=description)
    return True


def normalize_nid(value):
    """Normalize NID to integer for comparisons."""
    if value is None:
        return None
    if isinstance(value, int):
        return value
    text = str(value).strip().replace('-', '')
    if not text:
        return None
    try:
        if text.lower().startswith('0x'):
            return int(text, 16)
        return int(text, 10)
    except ValueError:
        return None


def nid_variants(value):
    """Return possible string variants for NID matching."""
    if value is None:
        return []
    nid_int = normalize_nid(value)
    variants = set()
    raw_value = str(value)
    variants.add(raw_value)
    variants.add(raw_value.lower())
    variants.add(raw_value.upper())
    if nid_int is not None:
        variants.add(str(nid_int))
        variants.add(hex(nid_int))
        variants.add(hex(nid_int).upper())
        variants.add(f"0x{nid_int:X}")
        variants.add(f"0X{nid_int:X}")
    return list(variants)

