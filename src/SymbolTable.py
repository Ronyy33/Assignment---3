STATIC = 'static'
FIELD  = 'field'
ARG    = 'argument'
VAR    = 'var'

KIND_TO_SEGMENT = {
    STATIC: 'static',
    FIELD:  'this',
    ARG:    'argument',
    VAR:    'local',
}


class SymbolTable:

    def __init__(self):
        self.class_table = {}       # name to (type, kind, index)
        self.subroutine_table = {}  # name to (type, kind, index)
        self.counts = {STATIC: 0, FIELD: 0, ARG: 0, VAR: 0}

    def start_subroutine(self):
        self.subroutine_table = {}
        self.counts[ARG] = 0
        self.counts[VAR] = 0

    def define(self, name, var_type, kind):
        index = self.counts[kind]
        entry = (var_type, kind, index)
        self.counts[kind] += 1

        if kind in (STATIC, FIELD):
            self.class_table[name] = entry
        else:
            self.subroutine_table[name] = entry

    def var_count(self, kind):
        return self.counts[kind]

    def _lookup(self, name):
        if name in self.subroutine_table:
            return self.subroutine_table[name]
        if name in self.class_table:
            return self.class_table[name]
        return None

    def kind_of(self, name):
        entry = self._lookup(name)
        if entry is None:
            return None
        _, kind, _ = entry
        return KIND_TO_SEGMENT[kind]

    def type_of(self, name):
        entry = self._lookup(name)
        if entry is None:
            return None
        return entry[0]

    def index_of(self, name):
        entry = self._lookup(name)
        if entry is None:
            return None
        return entry[2]

    def contains(self, name):
        return self._lookup(name) is not None

    def reset(self):
        self.class_table = {}
        self.subroutine_table = {}
        self.counts = {STATIC: 0, FIELD: 0, ARG: 0, VAR: 0}
