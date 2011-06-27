# world.py
# The definition of the main world database.  Properties are what can be used to query the properties database

from textadv.core.patterns import BasicPattern
from textadv.core.rulesystem import ActionTable, PropertyTable, ActionHelperObject


class World(object) :
    def __init__(self) :
        self.properties = PropertyTable()
        self.property_types = dict() # name -> Property
        self.inv_property_types = dict() # Property -> name
        self.modified_properties = dict()
        self.game_defined = False
        self.relations = dict()
        self.relation_handlers = []
        self.name_to_relation = dict()
        self._actions = dict()
        self.actions = ActionHelperObject(self)
    def set_game_defined(self) :
        """Set when it's time to close off arbitrary property
        definitions."""
        self.game_defined = True
    def __setitem__(self, item, value) :
        if self.game_defined :
            self.modified_properties[item] = value
        else :
            self.properties[item] = value
    def __getitem__(self, item) :
        if self.modified_properties.has_key(item) :
            return self.modified_properties[item]
        return self.properties.get_property(item, {"world" : self})
    def handler(self, item) :
        return self.properties.handler(item)

    def make_property(self, numargs, name) :
        class _NewProperty(BasicPattern) :
            def __init__(self, *args) :
                if len(args) != numargs :
                    raise Exception("Property requires exactly "+str(numargs)+" arguments.")
                self.args = args
        _NewProperty.__name__ = name
        self.property_types[name] = _NewProperty
        self.inv_property_types[_NewProperty] = name
        return _NewProperty
    def set_property(self, name, *args, **kwargs) :
        """This is __setitem__ but by the registered name of the property."""
        self[self.property_types[name](*args)] = kwargs["value"]
    def get_property(self, name, *args) :
        """This is __getitem__ but by name."""
        return self[self.property_types[name](*args)]

    def add_relation(self, relation) :
        relation.add_relation(self.relations[type(relation)])
    def remove_relation(self, relation) :
        relation.remove_relation(self.relations[type(relation)])
    def define_relation(self, r) :
        if self.game_defined :
            raise Exception("Can't define new relation when game is defined.")
        self.relation_handlers.append(r)
        self.relations[r] = r.setup_table()
        self.name_to_relation[r.__name__] = r
        return r
    def query_relation(self, relation, var=None) :
        res = relation.query_relation(self.relations[type(relation)])
        if var is None :
            return res
        else :
            return [r[var.varName] for r in res]
    def r_path_to(self, r, a, b) :
        return r.path_to(self.relations[r], a, b)
    def get_relation(self, name) :
        return self.relation_handlers[name]

    def define_action(self, name, **kwargs) :
        self._actions[name] = ActionTable(**kwargs)
    def to(self, name) :
        if self.game_defined :
            raise Exception("Can't add new actions when game is defined.")
        def _to(f) :
            if not self._actions.has_key(name) :
                self._actions[name] = ActionTable()
            self._actions[name].add_handler(f)
            return f
        return _to
    def call(self, name, *args) :
        return self._actions[name].notify(args, {"world" : self})

    def serialize(self) :
        import pickle
        mp = []
        for k,v in self.modified_properties.iteritems() :
            mp.append((self.inv_property_types[type(k)], k.args, v))
        return pickle.dumps((mp, self.relations))
    def deserialize(self, data) :
        import pickle
        import copy
        mp, rel = pickle.loads(data)
        newworld = copy.copy(self)
        newworld.modified_properties = dict()
        for name, args, v in mp :
            newworld.modified_properties[self.property_types[name](*args)] = v
        newworld.relations = rel
        return newworld

    def dump(self) :
        print "**Property table:**"
        self.properties.dump()
        print "\n**Modified property table:**"
        for k,v in self.modified_properties.iteritems() :
            print "%r = %r" % (k,v)
        print "\n**Relation tables:**"
        for r in self.relation_handlers :
            print " * For %s *" % r.__name__
            r.dump(self.relations[r])

