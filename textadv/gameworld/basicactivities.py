### Not to be imported
## Should be execfile'd

# basicactivities.py

# These are activities attached to the world and to the actor.

###
### World Activities
###

world.define_activity("def_obj", doc="""Defines an object of a
                                 particular kind in the game world.""")

@world.to("def_obj")
def default_def_obj(name, kind, world) :
    """Adds the relation IsA(name, kind)."""
    world.add_relation(IsA(name, kind))


##
## Activity: get the doors in a room
##

world.define_activity("get_room_doors", accumulator=list_append,
                      doc="""Gets a list of doors that are in a particular room.""")
@world.to("get_room_doors")
def default_get_room_doors(room, world) :
    """The doors in a room are those for which there is an exit from
    the room."""
    neighbors = world.query_relation(Exit(room, X, Y), var=Y)
    doors = [n for n in neighbors if world[IsA(n, "door")]]
    return doors

##
## Activity: get the other side of a door
##

world.define_activity("door_other_side_from", accumulator=lambda x : x[0],
                      doc="""Gets the room on the other side of a door from a given room.""")
@world.to("door_other_side_from")
def default_door_other_side_from(door, room, world) :
    """Given (door, room), gives the other room associated with the
    door."""
    rooms = world.query_relation(Exit(door, X, Y), var=Y)
    if len(rooms) == 1 :
        raise Exception("Door only has one side")
    elif rooms[0] == room :
        return rooms[1]
    else :
        return rooms[0]

##
## Activities: getting exits from a room
##

world.define_activity("get_room_exit_directions", accumulator=list_append,
                      doc="""Gets the directions from a room one can leave.""")

@world.to("get_room_exit_directions")
def default_get_room_exit_directions(room, world) :
    """Just looks through the Exit relation table."""
    return world.query_relation(Exit(room, X, Y), var=X)


###
### Actor Activities
###

##
## Activity: describing a location
##

@actoractivities.to("describe_current_location")
def describe_current_location_default(ctxt) :
    """Calls describe_location using the Location and the
    VisibleContainer of the current actor."""
    loc = ctxt.world[Location(ctxt.actor)]
    vis_cont = ctxt.world[VisibleContainer(loc)]
    ctxt.world[Global("current_location")] = vis_cont
    ctxt.activity.describe_location(ctxt.actor, loc, vis_cont)

__DESCRIBE_LOCATION_notables = []
__DESCRIBE_LOCATION_mentioned = []

@actoractivities.to("describe_location")
def describe_location_init(actor, loc, vis_cont, ctxt) :
    """Initializes the global variables __DESCRIBE_LOCATION_notables
    and __DESCRIBE_LOCATION_mentioned."""
    global __DESCRIBE_LOCATION_notables, __DESCRIBE_LOCATION_mentioned
    __DESCRIBE_LOCATION_notables = []
    __DESCRIBE_LOCATION_mentioned = []

@actoractivities.to("describe_location")
def describe_location_Heading(actor, loc, vis_cont, ctxt) :
    """Constructs the heading using describe_location_heading.  If the
    room is in darkness, then, writes "Darkness"."""
    if ctxt.world[ContainsLight(vis_cont)] :
        ctxt.world[Global("currently_lit")] = True
        ctxt.activity.describe_location_heading(actor, loc, vis_cont)
    else :
        ctxt.world[Global("currently_lit")] = False
        ctxt.write("Darkness")

@actoractivities.to("describe_location")
def describe_location_Description(actor, loc, vis_cont, ctxt) :
    """Prints the description property of the visible container if it
    is a room, unless the room is in darkness.  Darkness stops further
    description of the location."""
    if ctxt.world[ContainsLight(vis_cont)] :
        if ctxt.world[IsA(vis_cont, "room")] :
            d = ctxt.world[Description(vis_cont)]
            if d : ctxt.write("[newline]"+d)
    else :
        ctxt.write("[newline]You can't see a thing; it's incredibly dark.")
        raise ActionHandled()

@actoractivities.to("describe_location")
def describe_location_Objects(actor, loc, vis_cont, ctxt) :
    """Prints descriptions of the notable objects in the contents of
    the visible container."""
    continue_ascending = True
    mentioned = __DESCRIBE_LOCATION_mentioned
    notables = __DESCRIBE_LOCATION_notables
    curr_msgs = []
    while continue_ascending :
        obs = ctxt.world[Contents(loc)]
        raw_notables = list_append(ctxt.activity.get_notable_objects(actor, o) for o in obs)
        to_ignore = [o for o,n in raw_notables if n==0]
        filtered_notables = [(o,n) for o,n in raw_notables if o not in to_ignore]
        filtered_notables.sort(key=lambda x : x[1], reverse=True)
        notables = [o for o,n in filtered_notables]

        unnotable_messages = []
        current_location = None
        is_first_sentence = loc==vis_cont # the top level ends up printing first
        current_start = None
        current_descs = None
        for o in notables :
            if o not in mentioned :
                msg = ctxt.activity.terse_obj_description(actor, o, notables, mentioned)
                mentioned.append(o)
                if not msg : # the object printed its own description
                    pass
                else :
                    # we need special handling for doors (which have no Location)
                    if ctxt.world[IsA(o, "door")] :
                        # we assume that if we've found a door, then then it must be in the vis_cont location
                        o_loc = vis_cont
                    else :
                        o_loc = ctxt.world[Location(o)]
                    if o_loc != current_location :
                        if current_descs :
                            unnotable_messages.append((current_start, current_descs))
                        current_location = o_loc
                        if o_loc == vis_cont :
                            if is_first_sentence :
                                current_start = "You see "
                                is_first_sentence = False
                            else :
                                current_start = "You also see "
                        elif ctxt.world[IsA(o_loc, "container")] :
                            mentioned.append(o_loc)
                            if is_first_sentence :
                                current_start = "In "+ctxt.world[DefiniteName(o_loc)]+" you see "
                                is_first_sentence = False
                            else :
                                current_start = "In "+ctxt.world[DefiniteName(o_loc)]+" you also see "
                        elif ctxt.world[IsA(o_loc, "supporter")] :
                            mentioned.append(o_loc)
                            if is_first_sentence :
                                current_start = "On "+ctxt.world[DefiniteName(o_loc)]+" you see "
                                is_first_sentence = False
                            else :
                                current_start = "On "+ctxt.world[DefiniteName(o_loc)]+" you also see "
                        else :
                            raise Exception("Unknown kind of location for "+o_loc)
                        current_descs = []
                    current_descs.append(msg)
        if current_descs : # then we need to add the remainder of the messages
            unnotable_messages.append((current_start, current_descs))

        if unnotable_messages :
            curr_msgs.insert(0, "[newline]".join(start+serial_comma(msgs)+"." for start,msgs in unnotable_messages))
        
        if loc == vis_cont :
            continue_ascending = False
        else :
            loc = ctxt.world[Location(loc)]

    if curr_msgs :
        ctxt.write("[newline]"+"[newline]".join(curr_msgs))

@actoractivities.to("describe_location")
def describe_location_set_visited(actor, loc, vis_cont, ctxt) :
    """If the visible container is a room, then we set it to being
    visited."""
    if ctxt.world[IsA(vis_cont, "room")] :
        ctxt.world[Visited(vis_cont)] = True


@actoractivities.to("describe_location_heading")
def describe_location_heading_Name(actor, loc, vis_cont, ctxt) :
    """Prints the name of the visible container."""
    if ctxt.world[IsA(vis_cont, "thing")] :
        ctxt.write(str_with_objs("[The $z]", z=vis_cont), actor=actor)
    else :
        ctxt.write(str_with_objs("[get Name $z]", z=vis_cont), actor=actor)

@actoractivities.to("describe_location_heading")
def describe_location_property_heading_location(actor, loc, vis_cont, ctxt) :
    """Creates a description of where the location is with respect to
    the visible container."""
    while loc != vis_cont :
        if ctxt.world[IsA(loc, "container")] :
            ctxt.write("(in",ctxt.world[DefiniteName(loc)]+")")
            __DESCRIBE_LOCATION_mentioned.append(loc)
        elif ctxt.world[IsA(loc, "supporter")] :
            ctxt.write("(on",ctxt.world[DefiniteName(loc)]+")")
            __DESCRIBE_LOCATION_mentioned.append(loc)
        else :
            return
        loc = ctxt.world[Location(loc)]

##
## Activity: terse_obj_description
##

actoractivities.define_activity("terse_obj_description", accumulator=join_with_spaces,
                           doc="""Should give a terse description of
                           an object while modifying mentioned as
                           objects are mentioned.  Should raise
                           ActionHandled() if want to signal no
                           message to be given (for if wanting to
                           print out a paragraph).""")

@actoractivities.to("terse_obj_description")
def terse_obj_description_IndefiniteName(actor, o, notables, mentioned, ctxt) :
    """Describes the object based on its indefinite name.  Except, if
    the NotableDescription is set, that is printed instead, and makes
    terse_obj_description return the empty string."""
    mentioned.append(o)
    d = ctxt.world[NotableDescription(o)]
    if d :
        ctxt.write(d)
        raise ActionHandled()
    else :
        return ctxt.world[IndefiniteName(o)]

@actoractivities.to("terse_obj_description")
def terse_obj_description_container(actor, o, notables, mentioned, ctxt) :
    """Describes the contents of a container, giving information of
    whether it is open or closed as needed (uses IsOpaque for if the
    container is openable and closed)."""
    if ctxt.world[IsA(o, "container")] :
        if ctxt.world[IsOpaque(o)] and ctxt.world[Openable(o)] and not ctxt.world[IsOpen(o)] :
            return "(which is closed)"
        else :
            contents = ctxt.world[Contents(o)]
            msgs = []
            for c in contents :
                if c in notables and c not in mentioned :
                    msg = ctxt.activity.terse_obj_description(actor, c, notables, mentioned)
                    if msg : msgs.append(msg)
            if msgs :
                state = "which is closed and " if ctxt.world[Openable(o)] and not ctxt.world[IsOpen(o)] else ""
                return "("+state+"in which "+is_are_list(msgs)+")"
            elif not contents :
                return "(which is empty)"
            else :
                raise NotHandled()
    else : raise NotHandled()

@actoractivities.to("terse_obj_description")
def terse_obj_description_supporter(actor, o, notables, mentioned, ctxt) :
    if ctxt.world[IsA(o, "supporter")] :
        contents = ctxt.world[Contents(o)]
        msgs = []
        for o in contents :
            if o in notables and o not in mentioned :
                msg = ctxt.activity.terse_obj_description(actor, o, notables, mentioned)
                if msg : msgs.append(msg)
        if msgs :
            return "(on which "+is_are_list(msgs)+")"
    raise NotHandled()


##
## Activity: get_notable_objects
##

actoractivities.define_activity("get_notable_objects", accumulator=list_append,
                           doc="""Returns a list of objects which are
                           notable in a description as (obj,n) pairs,
                           where n is a numeric value from 0 onward
                           denoting notability.  n=1 is default, and
                           n=0 disables.  Repeats are fine.""")

@actoractivities.to("get_notable_objects")
def get_notable_objects_no_for_scenery(actor, x, ctxt) :
    """If a container that is scenery is not notable, and neither are
    its contents (since they are presumably not very prominent), so
    returns [(x,0)] and stops executing the rest of the activity."""
    if ctxt.world[Scenery(x)] and ctxt.world[IsA(x, "container")] :
        raise ActionHandled([(x, 0)])
    else : raise NotHandled()
@actoractivities.to("get_notable_objects")
def get_notable_objects_thing(actor, x, ctxt) :
    """By default, returns (x, 1) to represent x not being very
    notable, but notable enough to be mentioned."""
    if ctxt.world[IsA(x, "thing")] :
        return [(x, 1)]
    else : raise NotHandled()
@actoractivities.to("get_notable_objects")
def get_notable_objects_container(actor, x, ctxt) :
    """Gets objects from the container"""
    if ctxt.world[IsA(x, "container")] :
        obs = ctxt.world[Contents(x)]
        return list_append(ctxt.activity.get_notable_objects(actor, o) for o in obs if ctxt.world[VisibleTo(o, actor)])
    else : raise NotHandled()
@actoractivities.to("get_notable_objects")
def get_notable_objects_supporter(actor, x, ctxt) :
    if ctxt.world[IsA(x, "supporter")] :
        obs = ctxt.world[Contents(x)]
        return list_append(ctxt.activity.get_notable_objects(actor, o) for o in obs)
    else : raise NotHandled()
@actoractivities.to("get_notable_objects")
def get_notable_objects_not_reported(actor, x, ctxt) :
    if not ctxt.world[Reported(x)] :
        return [(x, 0)]
    else : raise NotHandled()

##
## Activity: describe_object
##

actoractivities.define_activity("describe_object",
                           doc="""Describes an object for the purpose of examining.""")

__DESCRIBE_OBJECT_described = False

@actoractivities.to("describe_object")
def describe_object_init(actor, o, ctxt) :
    """Initialize the global variable __DESCRIBE_OBJECT_described,
    which represents whether any description was uttered."""
    global __DESCRIBE_OBJECT_described
    __DESCRIBE_OBJECT_described = False
@actoractivities.to("describe_object")
def describe_object_description(actor, o, ctxt) :
    """Writes the Description if there is one defined."""
    d = ctxt.world[Description(o)]
    if d :
        global __DESCRIBE_OBJECT_described
        __DESCRIBE_OBJECT_described = True
        ctxt.write(d, actor=actor)
@actoractivities.to("describe_object")
def describe_object_container(actor, o, ctxt) :
    """Writes a line about the contents of a container if the container is not opaque."""
    global __DESCRIBE_OBJECT_described
    if ctxt.world[IsA(o, "container")] :
        if not ctxt.world[IsOpaque(o)] :
            contents = [ctxt.world[IndefiniteName(c)] for c in ctxt.world[Contents(o)] if ctxt.world[Reported(c)]]
            if contents :
                if __DESCRIBE_OBJECT_described : # print a newline if needed.
                    ctxt.write("[newline]")
                __DESCRIBE_OBJECT_described = True
                ctxt.write("In "+ctxt.world[DefiniteName(o)]+" "+is_are_list(contents)+".", actor=actor)
        elif ctxt.world[Openable(o)] and not ctxt.world[IsOpen(o)] :
            if __DESCRIBE_OBJECT_described :
                ctxt.write("[newline]")
            __DESCRIBE_OBJECT_described = True
            ctxt.write(str_with_objs("[The $o] is closed.", o=o), actor=actor)
@actoractivities.to("describe_object")
def describe_object_supporter(actor, o, ctxt) :
    """Writes a line about the contents of a supporter."""
    if ctxt.world[IsA(o, "supporter")] :
        contents = [ctxt.world[IndefiniteName(c)] for c in ctxt.world[Contents(o)] if ctxt.world[Reported(c)]]
        if contents :
            global __DESCRIBE_OBJECT_described # print a newline if needed.
            if __DESCRIBE_OBJECT_described :
                ctxt.write("[newline]")
            __DESCRIBE_OBJECT_described = True
            ctxt.write("On "+ctxt.world[DefiniteName(o)]+" "+is_are_list(contents)+".", actor=actor)
@actoractivities.to("describe_object")
def describe_object_default(actor, o, ctxt) :
    """Runs if none of the previous were successful.  Prints a default message."""
    global __DESCRIBE_OBJECT_described
    if not __DESCRIBE_OBJECT_described :
        ctxt.write(str_with_objs("{Bob|cap} {sees} nothing special about [the $o].", o=o), actor=actor)

##
## Activity: describe_possession
##

actoractivities.define_activity("describe_possession",
                           doc="""Describes an object as if it were a possession.""")

@actoractivities.to("describe_possession")
def describe_possession_indefinite_name(actor, o, numtabs, ctxt) :
    """Prints the indefinite name of the object preceded by numtabs
    indentations."""
    ctxt.write("[break]"+"[indent]"*numtabs+ctxt.world[IndefiniteName(o)])
@actoractivities.to("describe_possession")
def describe_possession_if_worn(actor, o, numtabs, ctxt) :
    """Just writes (worn) if the thing is worn."""
    if ctxt.world.query_relation(Wears(actor, o)) :
        ctxt.write("(worn)")
@actoractivities.to("describe_possession")
def describe_possession_openable(actor, o, numtabs, ctxt) :
    """Prints (open) or (closed) if the thing is openable."""
    if ctxt.world[Openable(o)] :
        if ctxt.world[IsOpen(o)] :
            ctxt.write("(open)")
        else :
            ctxt.write("(closed)")
@actoractivities.to("describe_possession")
def describe_possession_container(actor, o, numtabs, ctxt) :
    """Prints the contents of a container if it's not opaque."""
    if ctxt.world[IsA(o, "container")] and not ctxt.world[IsOpaque(o)] :
        cont = ctxt.world[Contents(o)]
        for c in cont :
            ctxt.activity.describe_possession(actor, c, numtabs+1)
@actoractivities.to("describe_possession")
def describe_possession_supporter(actor, o, numtabs, ctxt) :
    """Prints the contents of a supporter."""
    if ctxt.world[IsA(o, "supporter")] :
        cont = ctxt.world[Contents(o)]
        for c in cont :
            ctxt.activity.describe_possession(actor, c, numtabs+1)