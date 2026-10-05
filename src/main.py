import sys


def read_lines(path):
    """Read a file as raw bytes and split it into lines."""
    try:
        with open(path, "rb") as file:
            data = file.read()
    except (OSError, IOError) as error:
        print(f"error: cannot read {path}: {error}", file=sys.stderr)
        return None

    # Split only on the newline byte.
    lines = data.split(b"\n")

    # A final newline does not create an extra empty line.
    if lines and lines[-1] == b"":
        lines.pop()

    return lines


def myers_diff(a, b):
    n = len(a)
    m = len(b)

    if n == 0:
        return [("insert", value) for value in b]

    if m == 0:
        return [("delete", value) for value in a]

    if a == b:
        return [("keep", value) for value in a]

    max_d = n + m

    # V[k] = furthest x reached on diagonal k
    v = {0: 0}

    # Save V after every completed d level.
    trace = []

    for d in range(max_d + 1):

        for k in range(-d, d + 1, 2):

            # Decide whether the path comes from:
            # k + 1 -> insertion
            # k - 1 -> deletion
            if k == -d:
                x = v.get(k + 1, 0)

            elif k == d:
                x = v.get(k - 1, 0) + 1

            else:
                # Prefer deletion when both choices reach
                # the same or similar position.
                if v.get(k - 1, -1) + 1 >= v.get(k + 1, -1):
                    x = v.get(k - 1, -1) + 1
                else:
                    x = v.get(k + 1, -1)

            y = x - k

            # Follow the diagonal as far as possible.
            while x < n and y < m and a[x] == b[y]:
                x += 1
                y += 1

            v[k] = x

            # We reached the end.
            if x >= n and y >= m:
                trace.append(v.copy())
                return reconstruct(a, b, trace)

        trace.append(v.copy())

    return []



def reconstruct(a, b, trace):
    x = len(a)
    y = len(b)

    operations = []

    # Work backwards through d = D ... 1
    for d in range(len(trace) - 1, 0, -1):

        v_previous = trace[d - 1]

        k = x - y

        # Decide which previous diagonal we came from.
        if k == -d:
            previous_k = k + 1

        elif k == d:
            previous_k = k - 1

        else:
            left = v_previous.get(k - 1, -1)
            right = v_previous.get(k + 1, -1)

            # Deletion has priority when tied.
            if left + 1 >= right:
                previous_k = k - 1
            else:
                previous_k = k + 1

        previous_x = v_previous.get(previous_k, 0)
        previous_y = previous_x - previous_k

        # Everything between previous position and current
        # position on the diagonal is a match.
        while x > previous_x and y > previous_y:
            operations.append(("keep", a[x - 1]))
            x -= 1
            y -= 1

        # One edit happened before the diagonal.
        if x == previous_x:
            # Insertion from B.
            if y > 0:
                operations.append(("insert", b[y - 1]))
                y -= 1
        else:
            # Deletion from A.
            if x > 0:
                operations.append(("delete", a[x - 1]))
                x -= 1

    # Any remaining diagonal at the beginning.
    while x > 0 and y > 0:
        operations.append(("keep", a[x - 1]))
        x -= 1
        y -= 1

    while x > 0:
        operations.append(("delete", a[x - 1]))
        x -= 1

    while y > 0:
        operations.append(("insert", b[y - 1]))
        y -= 1

    operations.reverse()

    return operations

def get_changed_ranges(old_text, new_text):
    old_chars = list(old_text)
    new_chars = list(new_text)

    operations = myers_diff(old_chars, new_chars)

    old_ranges = []
    new_ranges = []

    old_index = 0
    new_index = 0

    old_start = None
    old_end = None

    new_start = None
    new_end = None

    def add_old_range(start, end):
        if start == end:
            return

        if old_ranges and start <= old_ranges[-1][1]:
            old_ranges[-1] = (
                old_ranges[-1][0],
                max(old_ranges[-1][1], end)
            )
        else:
            old_ranges.append((start, end))

    def add_new_range(start, end):
        if start == end:
            return

        if new_ranges and start <= new_ranges[-1][1]:
            new_ranges[-1] = (
                new_ranges[-1][0],
                max(new_ranges[-1][1], end)
            )
        else:
            new_ranges.append((start, end))

    for operation, value in operations:

        if operation == "keep":

            if old_start is not None:
                add_old_range(old_start, old_end)
                old_start = None
                old_end = None

            if new_start is not None:
                add_new_range(new_start, new_end)
                new_start = None
                new_end = None

            old_index += 1
            new_index += 1

        elif operation == "delete":

            if old_start is None:
                old_start = old_index

            old_index += 1
            old_end = old_index

        elif operation == "insert":

            if new_start is None:
                new_start = new_index

            new_index += 1
            new_end = new_index

    if old_start is not None:
        add_old_range(old_start, old_end)

    if new_start is not None:
        add_new_range(new_start, new_end)

    old_result = ",".join(
        str(start) + "-" + str(end)
        for start, end in old_ranges
    )

    new_result = ",".join(
        str(start) + "-" + str(end)
        for start, end in new_ranges
    )

    if old_result == "":
        old_result = "."

    if new_result == "":
        new_result = "."

    return old_result, new_result


def write_lines_diff(operations):
    """Write Part A output as exact bytes."""

    output = bytearray()

    i = 0

    while i < len(operations):
        operation, value = operations[i]

        if operation == "keep":
            output.extend(b" ")
            output.extend(value)
            output.extend(b"\n")
            i += 1

        else:
            # A change block contains consecutive deletes/inserts.
            deletes = []
            inserts = []

            while i < len(operations) and operations[i][0] != "keep":
                operation, value = operations[i]

                if operation == "delete":
                    deletes.append(value)
                else:
                    inserts.append(value)

                i += 1

            # Assignment requirement:
            # all deletes must come before all inserts.
            for value in deletes:
                output.extend(b"-")
                output.extend(value)
                output.extend(b"\n")

            for value in inserts:
                output.extend(b"+")
                output.extend(value)
                output.extend(b"\n")

    sys.stdout.buffer.write(output)
    
def write_highlight_diff(operations):
    output = bytearray()

    i = 0

    while i < len(operations):

        operation, value = operations[i]

        if operation == "keep":

            output.extend(b" ")
            output.extend(value)
            output.extend(b"\n")

            i += 1
            continue

        # Collect one change block.
        deletes = []
        inserts = []

        while i < len(operations) and operations[i][0] != "keep":

            operation, value = operations[i]

            if operation == "delete":
                deletes.append(value)
            else:
                inserts.append(value)

            i += 1

        # Part A output:
        # all deletions first
        for value in deletes:
            output.extend(b"-")
            output.extend(value)
            output.extend(b"\n")

        # Then insertions.
        for index in range(len(inserts)):

            new_value = inserts[index]

            output.extend(b"+")
            output.extend(new_value)
            output.extend(b"\n")

            # Pair the insertion with the corresponding deletion.
            if index < len(deletes):

                old_value = deletes[index]

                # Part B highlighting is only required for
                # valid UTF-8 changed lines.
                old_text = old_value.decode("utf-8")
                new_text = new_value.decode("utf-8")

                old_ranges, new_ranges = get_changed_ranges(
                    old_text,
                    new_text
                )

                output.extend(b"? ")
                output.extend(old_ranges.encode("utf-8"))
                output.extend(b" | ")
                output.extend(new_ranges.encode("utf-8"))
                output.extend(b"\n")

    sys.stdout.buffer.write(output)


def main() -> int:
    if len(sys.argv) != 4 or sys.argv[1] not in ("lines", "highlight"):
        print("usage: main.py lines|highlight A_PATH B_PATH", file=sys.stderr)
        return 2

    command, a_path, b_path = sys.argv[1:]

    a = read_lines(a_path)
    b = read_lines(b_path)

    if a is None or b is None:
        return 2

    operations = myers_diff(a, b)

    if command == "lines":
        write_lines_diff(operations)
    else:
        write_highlight_diff(operations)
        
    return 0


raise SystemExit(main())