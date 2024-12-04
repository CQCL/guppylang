Overview
========

This chapter gives an overview of the overall compilation pipeline and how everything fits together.


What the ``@guppy`` decorator does
----------------------------------

Guppy programs are defined by decorating regular Python functions or classes with the ``@guppy`` decorator.
At this point, no compilation or checking is taking place yet, i.e. decorating is an infallible operation.
The only thing the decorator does is registering that an object needs to be handled later when the user triggers compilation.

Internally, we represent these decorated objects as "raw definitions" (see TODO for more on definitions).
For example, a decorated function is stored as a :class:`.RawFunctionDef` that holds a reference to the Python function that was decorated.
Function declarations, structs, type variables -- essentially everything the user can define -- are handled in a similar way.

All of these raw definitions are stored in a :class:`.GuppyModule`.
Modules are our main compilation units and by default, each Python file corresponds to a :class:`.GuppyModule`.
The ``@guppy`` decorator tries to find the Python file from which it was invoked and registers the raw definition with the corresponding module.
See TODO for more on Guppy's module system.


Compilation Pipeline
--------------------

There are various ways the user can trigger compilation of a module, but all paths lead to the :meth:`.GuppyModule.compile` method.
In this method, all registered raw definitions are processed in various stages.

Parsing
^^^^^^^

We use Python's :mod:`inspect` module to look up the source for decorated objects.
Then, we use Python's :func:`ast.parse` to turn this source into an abstract syntax tree (AST).
See :func:`.parse_py_func` for an example of this in action.
Throughout the whole compilation pipeline, we mostly use the builtin AST representation provided by Python.
Any additional AST nodes we need are defined in the :mod:`.nodes` module.

During parsing, we turn our raw definition into a "parsed definition".
For example, a :class:`.RawFunctionDef` is turned into a :class:`.ParsedFunctionDef` that can then be processed further.

Checking
^^^^^^^^

Next, we do variety of things like name analysis, type inference, type checking, and linearity checking.
These are described in detail in TODO.
The result of this phase is a checked definition, for example a :class:`.CheckedFunctionDef`

Lowering to HUGR
^^^^^^^^^^^^^^^^

Finally, we lower all definition to our `HUGR intermediate representation <https://github.com/CQCL/hugr>`_.
Internally, we refer to this stage as "compiling" since this is the final stage done by the Guppy compiler.
For example, we turn our :class:`.CheckedFunctionDef` into a :class:`.CompiledFunctionDef`.
From here on, the IR is handed off to tools like `tket2 <https://github.com/CQCL/tket2>`_ for optimisation
and `hugr-llvm <https://github.com/CQCL/hugr-llvm>`_ for further lowering anc machine-code generation.

