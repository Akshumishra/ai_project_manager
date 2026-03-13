def generate_position(prev_pos, next_pos):
    GAP = 1000.0

    def to_float(val):
        if val is None:
            return None
        try:
            return float(val)
        except ValueError:
            return 0.0

    p = to_float(prev_pos)
    n = to_float(next_pos)

    if p is None and n is None:
        result = GAP
    elif p is None:
        result = n / 2.0
    elif n is None:
        result = p + GAP
    else:
        result = (p + n) / 2.0

    return str(int(result)) if result.is_integer() else str(result)
