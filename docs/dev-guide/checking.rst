Checking a Function
===================

This chapter walks through the various phases of type and linearity checking for function definitions.

Our starting point is a :class:`.CheckedFunctionDef` storing the parsed abstract syntax tree of our function in form of a :class:`ast.FunctionDef`.
The top-level entry point for the checking logic is :meth:`.ParsedFunctionDef.check` and subsequent code in the :mod:`.func_checker` module.


1. CFG Construction
-------------------

Before doing any checking, we actually begin by transforming the function into a control-flow graph.
This is slightly unusual compared to other compilers that do this at a later stage (usually after semantic analysis).
In Guppy, we do it earlier to cope with dynamic variable assignments in Python that require reasoning about control-flow.

Motivation
^^^^^^^^^^

We want to be permissive about changing the type of a variable, for example the following should be fine:

.. code-block:: python

   x = 1
   use_int(x)
   if cond:
      x = 1.0
      use_float(x)
   else:
      use_int(x)

On the other hand, we need to reject programs if the type is not unique:

.. code-block:: python

   if cond:
      x = 1
   else:
      x = 1.0
   use(x)  # Error: x could be int or float

To achieve this, we run type checking on a CFG instead of the pure AST.

CFG Builder
^^^^^^^^^^^

Control-flow graphs are defined in the :mod:`guppylang.cfg` module.
They are made up of basic blocks :class:`.BB` whose statements are restricted to :data:`.BBStatement` AST nodes.
In particular, this excludes control-flow statements like conditionals or loops.

We construct CFGs using the :class:`.CFGBuilder` AST visitor.
This visitor also turns control-flow expressions like short-circuiting boolean logic or ``if`` expressions into explicit control-flow.
Furthermore, it does some light desugaring for list comprehensions, ``py(...)`` expressions, and walrus expressions (i.e. ``x := expr``).


2. Name Analysis
----------------

After the CFG is constructed, we start with the checking.
The entry point for this is the :func:`check_cfg` function.
However, before looking at types, we first do a name analysis pass that checks if variables are definitely assigned before they are used.
For example, the following code should be rejected:

.. code-block:: python

   if cond() or (y := foo()):
      return y  # Error: y not defined if `cond()` is true
   return y  # y is defined here

This check is done using standard dataflow analysis on the CFG.
We begin by collecting which variables are defined and used in each basic block.
This is done by the :class:`.VariableVisitor`, annotating each BB with a :class:`.VariableStats`.
Our dataflow analysis framework is implemented in the :mod:`.cfg.analysis` module and is triggered via the :meth:`.CFG.analyze` method.


3. Type Checking
----------------

After we have checked that the names used in a BB are definitely assigned, we can start to type-check the BB.
By visiting the blocks in BFS order, we make sure that we have already determined the types of the variables used in a BB once we get to it.
We also make sure that the input types flowing into a BB match up across all its predecessors.
This way we detect programs where the types of variables differs between different control-flow branches.
The details of type checking and inference is explained in TODO.

After type checking, every AST expression will be annotated with a type.
They can be queried via the :func:`.get_type` function.

.. note::

   In the future, it would be nice to statically enforce this with mypy, e.g. by defining something like a ``TypedAST``

Furthermore, type checking replaces some AST nodes with more fine-grained versions.
For example, :class:`ast.Name` nodes are turned into either a :class:`.GlobalName` for global variables or a :class:`.PlaceNode` for
local variable (see TODO for more on places).
Similar for other custom nodes defined in :mod:`.nodes` module.


4. Linearity Checking
---------------------

TODO

