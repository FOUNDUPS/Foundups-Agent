"""Binary Git-tree fixtures shared by module-intent contract tests."""

from __future__ import annotations


HEAD_A = "a" * 40
HEAD_B = "b" * 40


def directory_tree(*paths: str) -> bytes:
    return b"".join(
        f"040000 tree {index:040x}\t{path}\0".encode("utf-8")
        for index, path in enumerate(paths, start=1)
    )


def raw_tree(*names: str) -> bytes:
    return b"".join(
        b"100644 " + name.encode("utf-8") + b"\0" + bytes([index]) * 20
        for index, name in enumerate(names, start=1)
    )


def candidate_batch(
    input_data: bytes, *, documented: set[int] | None = None,
) -> bytes:
    documented = documented or set()
    output = bytearray()
    for position, oid in enumerate(input_data.decode("ascii").splitlines()):
        body = raw_tree(
            "README.md" if position in documented else "artifact.txt"
        )
        output.extend(f"{oid} tree {len(body)}\n".encode("ascii"))
        output.extend(body)
        output.extend(b"\n")
    return bytes(output)


def framed_tree(
    input_data: bytes, body: bytes, *, oid: str | None = None,
) -> bytes:
    requested = input_data.decode("ascii").strip()
    header_oid = requested if oid is None else oid
    return f"{header_oid} tree {len(body)}\n".encode("ascii") + body + b"\n"


__all__ = [
    "HEAD_A", "HEAD_B", "candidate_batch", "directory_tree", "framed_tree",
    "raw_tree",
]
