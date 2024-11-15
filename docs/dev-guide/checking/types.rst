Representing Types
==================

The :mod:`guppylang.tys` modules defined how the Guppy compiler represents types internally.


Kinds of Types
--------------

Guppy types are represented via an algebraic data type represented by the :data:`.Type` union.
It contains the following core types:

* :class:`.NoneType` represents the unit type ``None``.
* :class:`.NumericType` represents the types ``nat``, ``int``, and ``float``.
* :class:`.TupleType` is the type of tuples ``tuple[T1, T2, ...]``
* :class:`.OpaqueType` corresponds to types that are directly specified via a Hugr lowering.
  Examples include ``list[T]``, ``array[T, n]``, and ``qubit``.
  They are define via a :class:`.OpaqueTypeDef`.
* :class:`.StructType` represents user-defined struct types (see below for details).
* :class:`.FunctionType` represents (possibly generic) function types.
* :class:`.BoundTypeVar` is a type variable that is bound to a generic parameter.
  For example, the ``T`` in the generic function type ``forall T. T -> T``.
  They are identified by their de Bruijn index.
* :class:`.ExistentialTypeVar` represents variables that are used during type inference.
  They stand for concrete types that have not been inferred yet and are identified by a globally unique id.

All types inherit from :class:`.TypeBase` abstract base class which defines common behaviour of all types,
for example, querying whether a type is linear or lowering a type to Hugr.


Struct Types
------------

Consider a struct type like ``MyStruct[int]`` where ``MyStruct`` is defined like

.. code-block:: python

   @guppy.struct
   class MyStruct(Generic[T]):
      x: int
      y: T

The type ``MyStruct[int]`` is represented as an instance of :class:`.StructType`:

.. code-block:: python

   StructType(defn: CheckedStructDef, args: Sequence[Argument])

Struct types are made up of two parts:

* The :class:`.CheckedStructDef` identifies the struct but without concrete values for the generic parameters.
  In the example above, this is the ``MyStruct`` part.
* The :data:`.Argument` sequence identifies the concrete instantiation for the generic parameters of the struct.
  In the example above, this would be the ``[int]`` part.
  See below for more details on what exactly an "argument" is.

The benefit of splitting struct types up in this way is that it makes substitution and equality testing easier:
Turning a ``MyStruct[S]``, into a ``MyStruct[T]`` is very cheap.
Substituting the arguments deep into the struct fields would be a lot more costly.
This matches up with Guppy structs being `nominal types <https://en.wikipedia.org/wiki/Nominal_type_system>`_, i.e.
two struct types are equivalent if they have the same definition and their generic arguments are equivalent.

Note that we use the same representation for all other generic types in Guppy, i.e.
:class:`.TupleType`, :class:`.FunctionType` , :class:`.OpaqueType`, and :class:`.StructType`.
They all inherit from :class:`.ParametrizedTypeBase` and provide their generic arguments via the :attr:`.ParametrizedTypeBase.args` field.


Generic Arguments
-----------------

Guppy supports two kinds of generic arguments, captured via the :data:`.Argument` union type.
A good example of this is the type ``array[int, 10]``:

* ``int`` is a :class:`.TypeArg`, i.e. a generic argument of kind *type*.
* ``10`` is a :class:`.ConstArg`, i.e. a generic argument representing a compile-time constant value.

Note that constant arguments don't need to be literals, they could also be a generic constant variables.
(for example, the ``n`` in the function ``def foo[n](xs: array[int, n]) -> None``).
See :data:`.Const` for what constitutes a valid constant value.


Generic Parameters and Variables
--------------------------------

Going back to the example struct

.. code-block:: python

   @guppy.struct
   class MyStruct(Generic[T]):
      x: int
      y: T

we have now seen how the compiler represents the type arguments in a concrete type ``MyStruct[int]``.
However, we also need a way to represent the generic parameter ``T`` *within the definition* of ``MyStruct``.
We call these *generic parameters* and represent them via the :data:`.Parameter` union type.
The structure is similar to generic arguments:

* :class:`.TypeParam` represent parameters of kind type that can be instantiated with a :class:`.TypeArg`.
* :class:`.ConstParam` represents constant value parameters that can be instantiated with a :class:`.ConstArg` of matching type.

These parameters are stored within the struct definition in the :attr:`.CheckedStructDef.params` field.
In the struct field types, generic type variables are represented via a :class:`.BoundTypeVar` that refers to the *index* of
the corresponding type parameter in the :attr:`.CheckedStructDef.params` sequence.
The same applies to generic const values which are represented via a :class:`.BoundConstVar` pointing to the corresponding const parameter.

Note that we also use :data:`.Parameter` to represent the generic arguments of functions types.
For example, the function ``def foo[T, n](xs: array[T, n]) -> None`` has two parameters ``T`` and ``n``.
They are stored in the :attr:`.FunctionType.params` field.


Type Transformers
-----------------

Many operations on types require recursing into the type tree and looking at all intermediate nodes or leafs.
To make this recursive traversal easier, we have implemented the :class:`Transformable` interfaces
for all objects that contain types or const values.

By subclassing :class:`.Transformer` and implementing the :meth:`.Transformer.transform` method, we can do a custom traversal.
The ``transform`` method is going to be called for every type and const value in the type tree.
We can either return ``None`` to continue the recursive traversal, or return a new type to replace the old one in the type tree.
See :class:`.Substituter` and :class:`.Instantiator` for two examples of this pattern.

