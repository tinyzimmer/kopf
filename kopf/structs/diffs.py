"""
All the functions to calculate the diffs of the dicts.
"""
import collections.abc
import enum
from typing import Any, Iterator, Sequence, NamedTuple, Iterable, Union, overload

from kopf.structs import dicts


class DiffOperation(str, enum.Enum):
    ADD = 'add'
    CHANGE = 'change'
    REMOVE = 'remove'

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return repr(self.value)


class DiffItem(NamedTuple):
    operation: DiffOperation
    field: dicts.FieldPath
    old: Any
    new: Any

    def __repr__(self) -> str:
        return repr(tuple(self))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, collections.abc.Sequence):
            return tuple(self) == tuple(other)
        return NotImplemented

    def __ne__(self, other: object) -> bool:
        if isinstance(other, collections.abc.Sequence):
            return tuple(self) != tuple(other)
        return NotImplemented

    @property
    def op(self) -> DiffOperation:
        return self.operation


class Diff(Sequence[DiffItem]):

    def __init__(self, __items: Iterable[DiffItem]):
        super().__init__()
        self._items = tuple(DiffItem(*item) for item in __items)

    def __repr__(self) -> str:
        return repr(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[DiffItem]:
        return iter(self._items)

    @overload
    def __getitem__(self, i: int) -> DiffItem: ...

    @overload
    def __getitem__(self, i: slice) -> Sequence[DiffItem]: ...

    def __getitem__(self, item: Union[int, slice]) -> Union[DiffItem, Sequence[DiffItem]]:
        return self._items[item]

    def __eq__(self, other: object) -> bool:
        if isinstance(other, collections.abc.Sequence):
            return tuple(self) == tuple(other)
        return NotImplemented

    def __ne__(self, other: object) -> bool:
        if isinstance(other, collections.abc.Sequence):
            return tuple(self) != tuple(other)
        return NotImplemented


def reduce_iter(
        __d: Diff,
        path: dicts.FieldPath,
) -> Iterator[DiffItem]:
    for op, field, old, new in __d:

        # As-is diff (i.e. a root field).
        if not path:
            yield DiffItem(op, tuple(field), old, new)

        # The diff-field is longer than the path: get "spec.struct" when "spec.struct.field" is set.
        # Retranslate the diff with the field prefix shrinked.
        elif tuple(field[:len(path)]) == tuple(path):
            yield DiffItem(op, tuple(field[len(path):]), old, new)

        # The diff-field is shorter than the path: get "spec.struct" when "spec={...}" is added.
        # Generate a new diff, with new ops, for the resolved sub-field.
        elif tuple(field) == tuple(path[:len(field)]):
            tail = path[len(field):]
            old_tail = dicts.resolve(old, tail, default=None, assume_empty=True)
            new_tail = dicts.resolve(new, tail, default=None, assume_empty=True)
            yield from diff_iter(old_tail, new_tail)


def reduce(
        __d: Diff,
        path: dicts.FieldPath,
) -> Diff:
    path = dicts.parse_field(path)
    return __d if not path else Diff(reduce_iter(__d, path))


def diff_iter(
        __a: Any,
        __b: Any,
        path: dicts.FieldPath = (),
) -> Iterator[DiffItem]:
    """
    Calculate the diff between two dicts.

    Yields the tuple of form ``(op, path, old, new)``,
    where ``op`` is either ``"add"``/``"change"``/``"remove"``,
    ``path`` is a tuple with the field names (empty tuple means root),
    and the ``old`` & ``new`` values (`None` for addition/removal).

    List values are treated as a whole, and not recursed into.
    Therefore, an addition/removal of a list item is considered
    as a change of the whole value.

    If the deep diff for lists/sets is needed, see the libraries:

    * https://dictdiffer.readthedocs.io/en/latest/
    * https://github.com/seperman/deepdiff
    * https://python-json-patch.readthedocs.io/en/latest/tutorial.html
    """
    if __a == __b:  # incl. cases when both are None
        pass
    elif __a is None:
        yield DiffItem(DiffOperation.ADD, path, __a, __b)
    elif __b is None:
        yield DiffItem(DiffOperation.REMOVE, path, __a, __b)
    elif type(__a) != type(__b):  # pylint: disable=unidiomatic-typecheck
        yield DiffItem(DiffOperation.CHANGE, path, __a, __b)
    elif isinstance(__a, collections.abc.Mapping):
        a_keys = frozenset(__a.keys())
        b_keys = frozenset(__b.keys())
        for key in b_keys - a_keys:
            yield from diff_iter(None, __b[key], path=path + (key,))
        for key in a_keys - b_keys:
            yield from diff_iter(__a[key], None, path=path + (key,))
        for key in a_keys & b_keys:
            yield from diff_iter(__a[key], __b[key], path=path + (key,))
    else:
        yield DiffItem(DiffOperation.CHANGE, path, __a, __b)


def diff(
        __a: Any,
        __b: Any,
        path: dicts.FieldPath = (),
) -> Diff:
    """
    Same as `diff`, but returns the whole tuple instead of iterator.
    """
    return Diff(diff_iter(__a, __b, path=path))


EMPTY = diff(None, None)
