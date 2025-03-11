## Model execution engine

# Loading a System

We supply mx with a system to run, an initial context, and a scenario to execute

`mx -s elevator -c three_bank1 -x lobby_to_three`

The required arguments are:

```
-s / --system
-c / --context
-x / --scenario
```
Optional arguments are:
```
-D / --debug
-V / --version
```
### -s or --system

Here you specify the name of a directory containing the following components:
```
system_name/
    system.ral   - Metamodel produced by xuml-populate (can be named anything you like, with any extension)
    db_types/    - Directory of yaml files mapping user types to TclRAL system types (must have this name)
        domain_name1_types.yaml  - Each yaml file name must begin with domain name or alias
        domain_name2_types.yaml
        domain_name3_types.yaml
```
Example:
```
elevator/                 - Any name ok
    elevator.ral          - Any name ok, ev.txt, mm3.ral, etc.
    db_types/             - Must be this name
        evman_types.yaml  - could have named it evman.yaml, elevator_management.yaml, 
                          - evman_user_to_tcl_types.yaml, etc
                          - but prefix must be either evman (alias) or elevator_management
                          - case insensitive, so EVMAN also okay
```


The `system.ral` file is actually just a text file serialization of a TclRAL database.
Specifically, it is a populated SM Metamodel that you can generate with the xuml-populate tool.  The metamodel is populated with one or more modeled domains. In our example, this is the elevator management domain. We could also add in the transport and sio domains defined in the elevator case study if we like, but for now we just have the elevator management (EVMAN) domain.

### -c or --context

This is yet another directory that contains a single initial context per domain. It is structured like this:
```
context_name/    - Any name that describes your aggregate initial context
     domain1.sip - One initial population per domain in the system
     domain2.sip
     domain3.sip
```

An initial context is a population of initial instances and states. That way we can begin a scenario with a known set of instances in known states for those instances with modeled lifecycles (state machines).

Each domain's context is defined with a single *.sip (scenario instance population) file.

In our example we have only one domain population:
```
three_bank/
     evman_three_bank1.sip
```
We named it 'three_bank' since we are using three separate elevator banks, 'lower floors',
'express', and 'freight'.

If we were running the trans and sio domains, we could have supplied one *.sip file for each
in this directory as well.

Note that each *.sip file name must begin with a domain name or alias.

See the sip-parser repository wiki for details on the grammar.

MX invokes the sip-parser when it loads the file and will throw any errors it finds in the process.

### -x or --scenario

Finally, we provide a sequence of interactions in the form of a scenario file to run against the populated system.

This is specified in a *.scn file. *(grammar/parser yet to be designed)*

You use the sequence of interactions to drive validation or exploration.

For example, you might specify that a cabin going up is requested from the lobby floor 
in the lower floors bank. It arrives, floor 3 is requested, the doors close, the cabin transits and then arrives at that floor with the doors opening.

This scenario will result in the appropriate events signaled in the loaded system and collect any responses and status updates of interest along the way.

You can define multiple initial contexts for a system and run the same or different scenarios against each.
