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
        else:
            return NotImplemented

    def __ne__(self, other: object) -> bool:
        if isinstance(other, collections.abc.Sequence):
            return tuple(self) != tuple(other)
        else:
            return NotImplemented

    @property
    def op(self) -> DiffOperation:
        return self.operation


class Diff(Sequence[DiffItem]):
    """
    A diff between two objects (currently mostly dicts).

    The diff highlights which keys were added, changed, or removed
    in the dictionary, with old & new values being selectable,
    and generally ignores all other fields that were not changed.

    Due to specifics of Kubernetes, ``None`` is interpreted as absence
    of the value/field, not as a value of its own kind. In case of diffs,
    it means that the value did not exist before, or will not exist after
    the changes (for the old & new value positions respectively):

    >>> Diff.build(None, {'spec': {'struct': {'field': 'value'}}})
    ... (('add', (), None, {'spec': {'struct': {'field': 'value'}}}),)

    >>> Diff.build({}, {'spec': {'struct': {'field': 'value'}}})
    ... (('add', ('spec',), None, {'struct': {'field': 'value'}}),)

    Selecting from the diff by an integer index returns the diff item
    at that position, as if the diff was a tuple:

    >>> d = Diff.build({}, {'spec': {'struct': {'field': 'value'}}})
    >>> len(d)
    ... 1
    >>> d[0]
    ... ('add', ('spec',), None, {'struct': {'field': 'value'}})

    Other types of indexes are treated as a field specifier
    (e.g. a dot-separated string, a list/tuple of strings, etc),
    and return a diff reduced to that field only:

    >>> d[('spec')]
    ... (('add', (), None, {'struct': {'field': 'value'}}),)

    >>> d[('spec', 'struct')]
    ... (('add', (), None, {'field': 'value'}),)

    >>> d[('spec', 'struct', 'field')]
    ... (('add', (), None, 'value'),)

    All forms of single or multiple selections pointing to the same field
    return the same reduced diff:

    >>> d['spec.struct.field']
    ... (('add', (), None, 'value'),)

    >>> d['spec']['struct.field']
    ... (('add', (), None, 'value'),)

    >>> d['spec']['struct']['field']
    ... (('add', (), None, 'value'),)

    Note that the reduced diff's items are always relative to the selected
    field, or ``()`` if the whole selected field is added/changed/removed.

    Every diff object, however, remembers its own field path (for information):

    >>> d.path
    ... ()

    >>> d['spec.struct.field'].path
    ... ('spec', 'struct', 'field')

    >>> d['spec']['struct']['field'].path
    ... ('spec', 'struct', 'field')
    """

    # # TODO: maybe Diff.calculate(a, b) factory instead of overloading?
    # @overload
    # def __init__(self, __a: Any, __b: Any): ...
    #
    # @overload
    # def __init__(self, *, items=None, path: dicts.FieldPath = ()): ...

    def __init__(self, __items: Iterable[DiffItem], *, path=()):
        super().__init__()
        self._items = tuple(DiffItem(*item) for item in __items)
        self._path = path

    def __repr__(self) -> str:
        return repr(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[DiffItem]:
        return iter(self._items)

    @overload
    def __getitem__(self, item: int) -> DiffItem: ...

    @overload
    def __getitem__(self, item: dicts.FieldSpec) -> "Diff": ...

    def __getitem__(self, item):
        if isinstance(item, int):
            return self._items[item]
        else:
            cls = type(self)
            field = dicts.parse_field(item)
            return cls(reduce_iter(self, field), path=self._path + field)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, collections.abc.Sequence):
            return tuple(self) == tuple(other)
        else:
            return NotImplemented

    def __ne__(self, other: object) -> bool:
        if isinstance(other, collections.abc.Sequence):
            return tuple(self) != tuple(other)
        else:
            return NotImplemented

    @property
    def path(self) -> dicts.FieldPath:
        return self._path

    @classmethod
    def build(cls, __a: Any, __b: Any) -> "Diff":
        return cls(diff_iter(__a, __b))


# TODO: merge into the Diff class
def reduce_iter(
        d: Diff,
        path: dicts.FieldSpec,
) -> Iterator[DiffItem]:
    """
    Reduce a bigger diff to a diff of a specific sub-field or sub-structure.

    If the diff contains few records matching the specified path
    (e.g. for the individual fields within the path), all of them are returned.

    If the diff contains a single record for a freshly added/removed dictionary,
    and the path points to an individual field within that dictionary,
    the dict's record will be resolved to a record of the individual field.

    If the field or its parents are not there (absent), they are assumed
    to be empty dicts or ``None``, and will possibly appear later.
    However, a diff for a non-existent field (absent both in old & new)
    is an empty diff, not a single-record diff from ``None`` to ``None``.

    The field is always assumed to exist, and to be contained in the dicts.
    Any de-facto deviations from this assumptions, e.g. when the parent field
    is actually a scalar value or a list instead of a dict, lead to errors.
    """
    path = dicts.parse_field(path)
    for op, field, old, new in d:

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


# TODO: merge into the Diff class
def reduce(
        d: Diff,
        path: dicts.FieldSpec,
) -> Diff:
    return d[path]


def diff_iter(
        a: Any,
        b: Any,
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
    if a == b:  # incl. cases when both are None
        pass
    elif a is None:
        yield DiffItem(DiffOperation.ADD, path, a, b)
    elif b is None:
        yield DiffItem(DiffOperation.REMOVE, path, a, b)
    elif type(a) != type(b):
        yield DiffItem(DiffOperation.CHANGE, path, a, b)
    elif isinstance(a, collections.abc.Mapping):
        a_keys = frozenset(a.keys())
        b_keys = frozenset(b.keys())
        for key in b_keys - a_keys:
            yield from diff_iter(None, b[key], path=path+(key,))
        for key in a_keys - b_keys:
            yield from diff_iter(a[key], None, path=path+(key,))
        for key in a_keys & b_keys:
            yield from diff_iter(a[key], b[key], path=path+(key,))
    else:
        yield DiffItem(DiffOperation.CHANGE, path, a, b)


def diff(
        a: Any,
        b: Any,
) -> Diff:
    """
    Same as `diff`, but returns the whole tuple instead of iterator.
    """
    return Diff.build(a, b)


EMPTY = diff(None, None)
