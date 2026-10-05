import sys
from array import array


def load_file(path):
    try:
        with open(path, "rb") as f:
            content = f.read()
    except OSError as err:
        print(f"error: cannot read {path}: {err}", file=sys.stderr)
        return None

    parts = content.split(b"\n")

    if parts and parts[-1] == b"":
        parts.pop()

    return parts


def traceback_value(row, diagonal, distance):
    if diagonal < -distance or diagonal > distance:
        return -1

    return row[diagonal + distance]


def restore_script(left, right, layers, last_distance):
    x = len(left)
    y = len(right)
    reversed_script = []

    for distance in range(last_distance, 0, -1):
        diagonal = x - y
        previous_layer = layers[distance - 1]

        down_value = traceback_value(
            previous_layer,
            diagonal + 1,
            distance - 1
        )

        right_value = traceback_value(
            previous_layer,
            diagonal - 1,
            distance - 1
        )

        if diagonal == -distance:
            previous_diagonal = diagonal + 1
        elif diagonal == distance:
            previous_diagonal = diagonal - 1
        elif right_value + 1 >= down_value:
            previous_diagonal = diagonal - 1
        else:
            previous_diagonal = diagonal + 1

        previous_x = traceback_value(
            previous_layer,
            previous_diagonal,
            distance - 1
        )

        previous_y = previous_x - previous_diagonal

        while x > previous_x and y > previous_y:
            x -= 1
            y -= 1
            reversed_script.append(("keep", left[x]))

        if x == previous_x:
            y -= 1
            reversed_script.append(("insert", right[y]))
        else:
            x -= 1
            reversed_script.append(("delete", left[x]))

    while x > 0 and y > 0:
        x -= 1
        y -= 1
        reversed_script.append(("keep", left[x]))

    while x > 0:
        x -= 1
        reversed_script.append(("delete", left[x]))

    while y > 0:
        y -= 1
        reversed_script.append(("insert", right[y]))

    reversed_script.reverse()
    return reversed_script


def compute_myers(left, right):
    n = len(left)
    m = len(right)

    if n == 0:
        return [("insert", value) for value in right]

    if m == 0:
        return [("delete", value) for value in left]

    if left == right:
        return [("keep", value) for value in left]

    limit = n + m
    middle = limit + 1

    frontier = [-1] * (2 * limit + 3)

    # Initial Myers frontier.
    frontier[middle + 1] = 0

    layers = []

    for distance in range(limit + 1):
        first_diagonal = -distance
        last_diagonal = distance

        for diagonal in range(
            first_diagonal,
            last_diagonal + 1,
            2
        ):
            slot = middle + diagonal

            if diagonal == -distance:
                x = frontier[slot + 1]

            elif diagonal == distance:
                x = frontier[slot - 1] + 1

            elif frontier[slot - 1] >= frontier[slot + 1]:
                # Prefer deletion when both paths are equally long.
                x = frontier[slot - 1] + 1

            else:
                x = frontier[slot + 1]

            y = x - diagonal

            while (
                x < n
                and y < m
                and left[x] == right[y]
            ):
                x += 1
                y += 1

            frontier[slot] = x

            if x >= n and y >= m:
                layers.append(
                    array(
                        "i",
                        frontier[
                            middle + first_diagonal:
                            middle + last_diagonal + 1
                        ]
                    )
                )

                return restore_script(
                    left,
                    right,
                    layers,
                    distance
                )

        # Save only the diagonals active at this distance.
        layers.append(
            array(
                "i",
                frontier[
                    middle + first_diagonal:
                    middle + last_diagonal + 1
                ]
            )
        )

    return []


def normalize_changes(script):
    arranged = []
    index = 0

    while index < len(script):
        if script[index][0] == "keep":
            arranged.append(script[index])
            index += 1
            continue

        removed = []
        added = []

        while (
            index < len(script)
            and script[index][0] != "keep"
        ):
            kind, value = script[index]

            if kind == "delete":
                removed.append((kind, value))
            else:
                added.append((kind, value))

            index += 1

        arranged.extend(removed)
        arranged.extend(added)

    return arranged


def diff(left, right):
    return normalize_changes(
        compute_myers(left, right)
    )


def merge_ranges(ranges):
    if not ranges:
        return "."

    result = []

    for start, finish in ranges:
        if result and start <= result[-1][1]:
            old_start, old_finish = result[-1]
            result[-1] = (
                old_start,
                max(old_finish, finish)
            )
        else:
            result.append((start, finish))

    return ",".join(
        f"{start}-{finish}"
        for start, finish in result
    )


def character_ranges(old_line, new_line):
    old_chars = list(old_line.decode("utf-8"))
    new_chars = list(new_line.decode("utf-8"))

    script = diff(old_chars, new_chars)

    old_ranges = []
    new_ranges = []

    old_pos = 0
    new_pos = 0

    active_old = None
    active_new = None

    for kind, _ in script:
        if kind == "keep":
            if active_old is not None:
                old_ranges.append(
                    (active_old, old_pos)
                )
                active_old = None

            if active_new is not None:
                new_ranges.append(
                    (active_new, new_pos)
                )
                active_new = None

            old_pos += 1
            new_pos += 1

        elif kind == "delete":
            if active_old is None:
                active_old = old_pos

            old_pos += 1

        else:
            if active_new is None:
                active_new = new_pos

            new_pos += 1

    if active_old is not None:
        old_ranges.append(
            (active_old, old_pos)
        )

    if active_new is not None:
        new_ranges.append(
            (active_new, new_pos)
        )

    return (
        merge_ranges(old_ranges),
        merge_ranges(new_ranges)
    )


def output_lines(script):
    stream = sys.stdout.buffer

    for kind, line in script:
        if kind == "keep":
            marker = b" "
        elif kind == "delete":
            marker = b"-"
        else:
            marker = b"+"

        stream.write(marker)
        stream.write(line)
        stream.write(b"\n")


def output_highlight(script):
    stream = sys.stdout.buffer
    index = 0

    while index < len(script):

        if script[index][0] == "keep":
            stream.write(b" ")
            stream.write(script[index][1])
            stream.write(b"\n")
            index += 1
            continue

        removed = []
        added = []

        while (
            index < len(script)
            and script[index][0] != "keep"
        ):
            kind, line = script[index]

            if kind == "delete":
                removed.append(line)
            else:
                added.append(line)

            index += 1

        for line in removed:
            stream.write(b"-")
            stream.write(line)
            stream.write(b"\n")

        for number, line in enumerate(added):
            stream.write(b"+")
            stream.write(line)
            stream.write(b"\n")

            if number < len(removed):
                old_range, new_range = character_ranges(
                    removed[number],
                    line
                )

                stream.write(
                    b"? "
                    + old_range.encode("utf-8")
                    + b" | "
                    + new_range.encode("utf-8")
                    + b"\n"
                )


def main():
    if len(sys.argv) != 4:
        print(
            "Usage: python src/main.py lines A B",
            file=sys.stderr
        )
        print(
            "   or: python src/main.py highlight A B",
            file=sys.stderr
        )
        return 2

    command = sys.argv[1]
    first_path = sys.argv[2]
    second_path = sys.argv[3]

    first = load_file(first_path)
    second = load_file(second_path)

    if first is None or second is None:
        return 2

    if command == "lines":
        output_lines(diff(first, second))
        return 0

    if command == "highlight":
        output_highlight(diff(first, second))
        return 0

    print(
        "error: mode must be 'lines' or 'highlight'",
        file=sys.stderr
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())