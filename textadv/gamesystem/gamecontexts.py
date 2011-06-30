# gamecontexts.py
#
# Supposedly handles making the game modal in some way (as in, make
# input and output change how it works, or start playing a subgame in
# the game).
#
# The objects in this module are able to encapsulate the game state, though.
#
# provides: execute_context and ActorContext

from textadv.gamesystem.utilities import eval_str, as_actor
from textadv.core.rulesystem import AbortAction, ActionHandled, ActivityHelperObject, RuleHelperObject
from textadv.core.rulesystem import ActivityTable, RuleTable
from textadv.gamesystem.eventsystem import verify_action, run_action
from textadv.gamesystem.utilities import *
from textadv.gamesystem import parser
#from textadv.gamesystem.basicpatterns import X,Y,Z

def execute_context(context) :
    """Takes a context and runs it.  If it returns anything, it is
    treated to be a (context, nextargs), and that is run, and so
    on."""
    ret, args = context.run()
    while ret is not None :
        ret, args = ret.run(**args)

class GameContext(object) :
    """Provides a way to look at the world.  Handles all user input in
    a contextual way."""
    def run(self) :
        """Drives the context.  The return value is the new context to
        run, None if the game is over."""
        raise NotImplementedError("GameContext is abstract.")
    def write(self, *stuff) :
        """Handles output.  That way filters can be applied by the
        current context."""
        raise NotImplementedError("GameContext is abstract.")

## the io object for ActorContext must implement "get_input" which
## functions as "raw_input", and "write" which functions as "print x,"

class ActorActivities(object) :
    """This is a table of activities that all actors use."""
    def __init__(self) :
        self._activities = dict()
        self.activity = ActivityHelperObject(self)
    def define_activity(self, name, **kwargs) :
        self._activities[name] = ActivityTable(**kwargs)
    def to(self, name, **kwargs) :
        def _to(f) :
            if not self._activities.has_key(name) :
                self._activities[name] = ActivityTable()
            self._activities[name].add_handler(f, **kwargs)
            return f
        return _to
    def activity_table(self, name) :
        """Gets the activity table of the given name."""
        return self._activities[name]
    def call(self, name, *args, **kwargs) :
        return self._activities[name].notify(args, {"ctxt" : kwargs["ctxt"]}, disable=kwargs.get("disable", []))

class ActorRules(object) :
    """This is a table of rules that all actors use."""
    def __init__(self) :
        self._rules = dict()
        self.rule = RuleHelperObject(self)
    def define_event(self, name, **kwargs) :
        self._rules[name] = RuleTable(**kwargs)
    def to(self, name, pattern, **kwargs) :
        def _to(f) :
            if not self._rules.has_key(name) :
                self._rules[name] = RuleTable()
            self._rules[name].add_handler(pattern, f, **kwargs)
            return f
        return _to
    def rule_table(self, name) :
        """Gets the event table of the given name"""
        return self._rules[name]
    def call(self, name, *args, **kwargs) :
        return self._rules[name].notify(args, {"ctxt" : kwargs["ctxt"]}, {"world" : kwargs["ctxt"].world})

actoractivities = ActorActivities()
actorrules = ActorRules()

class ActorContext(GameContext) :
    """Represents the context in which the player is assuming the role
    of the actor.  The parser is the main parser in the parser module."""
    def __init__(self, parentcontext, io, world, actor) :
        self.parentcontext = parentcontext
        self.io = io
        self.world = world
        self.actor = actor
        self.activity = ActivityHelperObject(self)
        self.rule = RuleHelperObject(self)
    def write(self, *stuff, **kwargs) :
        """Writes a line by evaluating the string using the utilities
        module.  If there is an actor, then the text is wrapped so
        that the text is rendered as if the actor were doing it."""
        if kwargs.has_key("actor") :
            stuff = [as_actor(s, kwargs["actor"]) for s in stuff]
        newstuff = [eval_str(s, self) for s in stuff]
        self.io.write(*newstuff)
    def run(self, input=None, action=None) :
        try :
            if input is None and action is None:
                input = self.io.get_input()
                if input == "dump" :
                    self.world.dump()
                    return (self, {})
            try :
                if action is None :
                    action, disambiguated = parser.handle_all(input, self, verify_action)
                else :
                    disambiguated = True
                if disambiguated :
                    run_action(action, self, write_action=True)
                else :
                    run_action(action, self)
            except parser.NoSuchWord as ex :
                esc = escape_str(ex.word)
                self.write("I don't know what you mean by %r." % esc)
            except parser.NoUnderstand :
                self.write("Huh?")
            except parser.NoInput :
                pass
            except parser.Ambiguous as ex :
                return (DisambiguationContext(self, ex), dict())
            except AbortAction as ab :
                if len(ab.args) > 0 : # the AbortAction may contain a message
                    self.write(*ab.args, **ab.kwargs)
#             except GameIsEnding as gis :
#                 event_notify(gis.msg, context=self)
#                 self.write_line("\n\n*** The game is over ***")
#                 return None
            return (self, dict())
        except Exception :
            import traceback
            traceback.print_exc()
            return (self, dict())
    def call_activity(self, name, *args, **kwargs) :
        kwargs["ctxt"] = self
        return actoractivities.call(name, *args, **kwargs)
    def call_rule(self, name, *args, **kwargs) :
        kwargs["ctxt"] = self
        return actorrules.call(name, *args, **kwargs)
    def activity_table(self, name) :
        """Gets the action table of the given name."""
        return actoractivities.activity_table(name)
    def rule_table(self, name) :
        """Gets the event table of the given name."""
        return actorrules.rule_table(name)

class DisambiguationContext(GameContext) :
    def __init__(self, parent, amb) :
        self.parent = parent
        self.amb = amb
    def run(self) :
        repl = dict()
        if len(self.amb.options) > 1 :
            self.parent.write("I'm a bit confused by what you meant in a couple of places.")
        for var, opts in self.amb.options.iteritems() :
            res = serial_comma([self.parent.world.get_property("DefiniteName", o)
                                for o in opts], conj="or")
            self.parent.write("Did you mean "+res+"?")
            input = self.parent.io.get_input(">>>")
            res = parser.run_parser("something",
                                    parser.transform_text_to_words(input), self.parent)
            if len(res) == 0 :
                return (self.parent, {"input" : input})
            elif len(res) == 1 :
                repl[var] = res[0][0].value
            else :
                self.parent.write("That didn't help me out at all.")
                return (self.parent, dict())
        return (self.parent, {"action" : self.amb.pattern.expand_pattern(repl)})

def make_documentation(escape, heading_level=1) :
    hls = str(heading_level)
    shls = str(heading_level+1)
    print "<h"+hls+">Actor activities</h"+hls+">"
    print "<p>This is the documentation for the actor activities attached to <tt>actoractivities</tt> in <tt>gamecontexts.py</tt>.</p>"
    for name, table in actoractivities._activities.iteritems() :
        print "<h"+shls+">to "+escape(name)+"</h"+shls+">"
        table.make_documentation(escape, heading_level=heading_level+2)
    print "<h"+hls+">Actor rules</h"+hls+">"
    print "<p>This is the documentation for the actor rules attached to <tt>actorrules</tt> in <tt>gamecontexts.py</tt>.</p>"
    for name, table in actorrules._rules.iteritems() :
        print "<h"+shls+">to "+escape(name)+"</h"+shls+">"
        table.make_documentation(escape, heading_level=heading_level+2)

