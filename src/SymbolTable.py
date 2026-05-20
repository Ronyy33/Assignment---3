"""
SymbolTable - Manages mapping of identifiers in Jack source to their type,
kind (static, field, argument, local), and index offset within their respective segment.
"""

SCOPE_STATIC = 'static'
SCOPE_FIELD  = 'field'
SCOPE_ARG    = 'argument'
SCOPE_VAR    = 'var'

SEGMENT_MAPPING = {
    SCOPE_STATIC: 'static',
    SCOPE_FIELD:  'this',
    SCOPE_ARG:    'argument',
    SCOPE_VAR:    'local',
}


class LexicalScopeTable:
    """
    Tracks identifiers across class-level scope and subroutine-level scope.
    """

    def __init__(self):
        self._class_symbols = {}      # maps identifier to (type, kind, index)
        self._subroutine_symbols = {} # maps identifier to (type, kind, index)
        self._index_counters = {
            SCOPE_STATIC: 0,
            SCOPE_FIELD: 0,
            SCOPE_ARG: 0,
            SCOPE_VAR: 0
        }

    def reset_subroutine_scope(self):
        """
        Clears the subroutine scope table and resets arguments and variable indexes to 0.
        """
        self._subroutine_symbols.clear()
        self._index_counters[SCOPE_ARG] = 0
        self._index_counters[SCOPE_VAR] = 0

    def register_symbol(self, name, var_type, kind):
        """
        Defines a new identifier with a name, type, and kind in the appropriate scope.
        """
        index = self._index_counters[kind]
        entry = (var_type, kind, index)
        self._index_counters[kind] += 1

        if kind in (SCOPE_STATIC, SCOPE_FIELD):
            self._class_symbols[name] = entry
        else:
            self._subroutine_symbols[name] = entry

    def get_count_for_kind(self, kind):
        """
        Returns the number of variables defined in the current scope for the given kind.
        """
        return self._index_counters[kind]

    def _resolve_symbol(self, name):
        """
        Internal lookup helper that checks subroutine scope first, then class scope.
        """
        if name in self._subroutine_symbols:
            return self._subroutine_symbols[name]
        return self._class_symbols.get(name, None)

    def get_segment_of(self, name):
        """
        Returns the target memory segment corresponding to the variable's scope kind.
        """
        entry = self._resolve_symbol(name)
        if entry is not None:
            _, kind, _ = entry
            return SEGMENT_MAPPING[kind]
        return None

    def get_type_of(self, name):
        """
        Returns the declared type of the identifier.
        """
        entry = self._resolve_symbol(name)
        if entry is not None:
            return entry[0]
        return None

    def get_index_of(self, name):
        """
        Returns the index offset of the identifier in its segment.
        """
        entry = self._resolve_symbol(name)
        if entry is not None:
            return entry[2]
        return None

    def has_symbol(self, name):
        """
        Queries if the identifier exists in either the subroutine or class scope.
        """
        return self._resolve_symbol(name) is not None

    def clear_all(self):
        """
        Resets both scopes and all index counters completely.
        """
        self._class_symbols.clear()
        self._subroutine_symbols.clear()
        self._index_counters = {
            SCOPE_STATIC: 0,
            SCOPE_FIELD: 0,
            SCOPE_ARG: 0,
            SCOPE_VAR: 0
        }
