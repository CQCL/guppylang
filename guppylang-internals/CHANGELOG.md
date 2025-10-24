# Changelog

First release of `guppylang_internals` package containing refactored out internal components
from `guppylang`.

## [0.25.0](https://github.com/CQCL/guppylang/compare/guppylang-internals-v0.24.0...guppylang-internals-v0.25.0) (2025-10-24)


### ⚠ BREAKING CHANGES

* (guppy-internals) Arrays are now lowered to `borrow_array`s instead of `value_array`s so elements do no longer need to be wrapped in options during lowering.
* `checker.core.requires_monomorphization` renamed into `require_monomorphization` and now operating on all parameters simultaneously `tys.subst.BoundVarFinder` removed. Instead, use the new `bound_vars` property on types, arguments, and consts. `tys.parsing.parse_parameter` now requires a `param_var_mapping`.

### Features

* modifiers in CFG and its type checker (experimental) ([#1281](https://github.com/CQCL/guppylang/issues/1281)) ([fe85018](https://github.com/CQCL/guppylang/commit/fe8501854507c3c43cec2f26bba75198766a4a17))
* Turn type parameters into dependent telescopes ([#1154](https://github.com/CQCL/guppylang/issues/1154)) ([b56e056](https://github.com/CQCL/guppylang/commit/b56e056a6b4795c778ed8124a09a194fb1d97dda))
* update hugr, tket-exts and tket ([#1305](https://github.com/CQCL/guppylang/issues/1305)) ([6990d85](https://github.com/CQCL/guppylang/commit/6990d850170e6901f60ef1d1e718c99349105b56))
* Use `borrow_array` instead of `value_array` for array lowering ([#1166](https://github.com/CQCL/guppylang/issues/1166)) ([f9ef42b](https://github.com/CQCL/guppylang/commit/f9ef42b2baf61c3e1c2cfcf7bd1f3bcac33a1a25))


### Bug Fixes

* compilation of affine-bounded type variables ([#1308](https://github.com/CQCL/guppylang/issues/1308)) ([49ecb49](https://github.com/CQCL/guppylang/commit/49ecb497bf450d0853baec1de9c516a3804a80eb))
* Detect unsolved generic parameters even if they are unused ([#1279](https://github.com/CQCL/guppylang/issues/1279)) ([f830db0](https://github.com/CQCL/guppylang/commit/f830db00c416cfc1e9fe7ec70c612b6b558aa740)), closes [#1273](https://github.com/CQCL/guppylang/issues/1273)
* Fix bug in symbolic pytket circuit loading with arrays ([#1302](https://github.com/CQCL/guppylang/issues/1302)) ([e6b90e8](https://github.com/CQCL/guppylang/commit/e6b90e8e4d275d36514a75e87eb097383495a291)), closes [#1298](https://github.com/CQCL/guppylang/issues/1298)
* Improve track_hugr_side_effects, adding Order edges from/to Input/Output ([#1311](https://github.com/CQCL/guppylang/issues/1311)) ([3c6ce7a](https://github.com/CQCL/guppylang/commit/3c6ce7aaf7a1c93c6412501976fc97afd61a062d))
* multiline loop arguments  ([#1309](https://github.com/CQCL/guppylang/issues/1309)) ([836ef72](https://github.com/CQCL/guppylang/commit/836ef722d8f8bdb02c56e5f06934246a718e68d3))

## [0.24.0](https://github.com/CQCL/guppylang/compare/guppylang-internals-v0.23.0...guppylang-internals-v0.24.0) (2025-09-19)


### ⚠ BREAKING CHANGES

* `guppylang_internals.decorator.extend_type` now returns a `GuppyDefinition` by default. To get the previous behaviour of returning the annotated class unchanged, pass `return_class=True`.
* `TypeDef`s now require a `params` field
* guppylang_internals.ty.parsing.parse_function_io_types replaced with parse_function_arg_annotation and check_function_arg
* Significant changes to the WASM decorators, types and operations
* Deleted `guppylang_internals.nodes.{IterHasNext, IterEnd}`
* guppylang_internals.tracing.unpacking.update_packed_value now returns a bool signalling whether the operation was successful.
* `CompilationEngine` now initialises all it's fields
* Calling `CompilationEngine.reset` no longer nullifies `additional_extensions`
* `CompilationEngine.register_extension` no longer adds duplicates to the `additional_extensions` list

### Features

* Infer type of `self` arguments ([#1192](https://github.com/CQCL/guppylang/issues/1192)) ([51f5a2b](https://github.com/CQCL/guppylang/commit/51f5a2b3a9b06bc4ab054f32a4d07f7395df8ff4))


### Bug Fixes

* Add init to CompilationEngine; don't trash additional_extensions ([#1256](https://github.com/CQCL/guppylang/issues/1256)) ([e413748](https://github.com/CQCL/guppylang/commit/e413748532db3895cab4925a222177a4fa3fd61b))
* Allow generic specialization of methods ([#1206](https://github.com/CQCL/guppylang/issues/1206)) ([93936cc](https://github.com/CQCL/guppylang/commit/93936cc275c56dd856d11fabc7aac20176304147)), closes [#1182](https://github.com/CQCL/guppylang/issues/1182)
* Correctly update borrowed values after calls and catch cases where it's impossible ([#1253](https://github.com/CQCL/guppylang/issues/1253)) ([3ec5462](https://github.com/CQCL/guppylang/commit/3ec54627729b49689da006a743e9e2c359cd3728))
* Fix `nat` constructor in comptime functions ([#1258](https://github.com/CQCL/guppylang/issues/1258)) ([e257b6f](https://github.com/CQCL/guppylang/commit/e257b6fc2fe3793d6d8f63feca83bf5ed6643673))
* Fix incorrect leak error for borrowing functions in comptime ([#1252](https://github.com/CQCL/guppylang/issues/1252)) ([855244e](https://github.com/CQCL/guppylang/commit/855244e2d5e3aeb04c2028f9f2310dba0e74210a)), closes [#1249](https://github.com/CQCL/guppylang/issues/1249)
* wasm module updates based on tested lowering ([#1230](https://github.com/CQCL/guppylang/issues/1230)) ([657cea2](https://github.com/CQCL/guppylang/commit/657cea27af00a9c02e8d1a3190db535bbd1e7981))


### Miscellaneous Chores

* Delete unused old iterator AST nodes ([#1215](https://github.com/CQCL/guppylang/issues/1215)) ([2310897](https://github.com/CQCL/guppylang/commit/231089750e33cf70754e5218feed64053c558c17))

## [0.23.0](https://github.com/CQCL/guppylang/compare/guppylang-internals-v0.22.0...guppylang-internals-v0.23.0) (2025-08-19)


### ⚠ BREAKING CHANGES

* `check_rows_match` no longer takes `globals` Deleted `GlobalShadowError` and `BranchTypeError.GlobalHint`

### Bug Fixes

* Fix globals vs locals scoping behaviour to match Python ([#1169](https://github.com/CQCL/guppylang/issues/1169)) ([a6a91ca](https://github.com/CQCL/guppylang/commit/a6a91ca32ad7c67bf1d733eb26c016a2662256ef))
* Fix scoping issues with comprehensions in comptime expressions ([#1218](https://github.com/CQCL/guppylang/issues/1218)) ([0b990e2](https://github.com/CQCL/guppylang/commit/0b990e2b006c31352675004aec63a857f03a0793))


### Documentation

* use results sequence protocol for simplicity ([#1208](https://github.com/CQCL/guppylang/issues/1208)) ([f9c1aee](https://github.com/CQCL/guppylang/commit/f9c1aee38776c678660ede5495989ac4d75baaeb))

## [0.22.0](https://github.com/CQCL/guppylang/compare/guppylang-internals-v0.21.2...guppylang-internals-v0.22.0) (2025-08-11)


### ⚠ BREAKING CHANGES

* RangeChecker has been deleted.

### Features

* Add float parameter inputs to symbolic pytket circuits ([#1105](https://github.com/CQCL/guppylang/issues/1105)) ([34c546c](https://github.com/CQCL/guppylang/commit/34c546c3b5787beb839687fdbf4db8bc94f36c4a)), closes [#1076](https://github.com/CQCL/guppylang/issues/1076)
* Allow custom start and step in `range` ([#1157](https://github.com/CQCL/guppylang/issues/1157)) ([a1b9333](https://github.com/CQCL/guppylang/commit/a1b9333712c74270d5efaaa72f83d6b09047c068))
* Improve codegen for array unpacking ([#1106](https://github.com/CQCL/guppylang/issues/1106)) ([f375097](https://github.com/CQCL/guppylang/commit/f3750973a719b03d27668a3ae39f58c8424deffc))
* Insert drop ops for affine values ([#1090](https://github.com/CQCL/guppylang/issues/1090)) ([083133e](https://github.com/CQCL/guppylang/commit/083133e809873fce265bb78547fc3e519cb66ea1))


### Bug Fixes

* Fix builtins mock escaping the tracing scope ([#1161](https://github.com/CQCL/guppylang/issues/1161)) ([a27a5c1](https://github.com/CQCL/guppylang/commit/a27a5c19560d76e46678f846476ea86e873ac8ac))

## [0.21.1](https://github.com/CQCL/guppylang/compare/guppylang-internals-v0.21.0...guppylang-internals-v0.21.1) (2025-08-05)


### Bug Fixes

* **guppylang-internals:** Fix circular import for custom decorators ([#1146](https://github.com/CQCL/guppylang/issues/1146)) ([d8474d8](https://github.com/CQCL/guppylang/commit/d8474d8af3d394275268cd3d0754ff06ecb9bcc2)), closes [#1145](https://github.com/CQCL/guppylang/issues/1145)
* Support `None` value ([#1149](https://github.com/CQCL/guppylang/issues/1149)) ([7f606c7](https://github.com/CQCL/guppylang/commit/7f606c778d98312a0d1c4a9c7a27448c24d80585)), closes [#1148](https://github.com/CQCL/guppylang/issues/1148)


### Documentation

* Fix docs build ([#1142](https://github.com/CQCL/guppylang/issues/1142)) ([4dfd575](https://github.com/CQCL/guppylang/commit/4dfd575bcdfdf1e2db4e61f2f406fff27e0c08f7))

## [0.21.0](https://github.com/CQCL/guppylang/compare/guppylang-internals-v0.20.0...guppylang-internals-v0.21.0) (2025-08-04)


### ⚠ BREAKING CHANGES

* All compiler-internal and non-userfacing functionality is moved into a new `guppylang_internals` package

### Code Refactoring

* Split up into `guppylang_internals` package ([#1126](https://github.com/CQCL/guppylang/issues/1126)) ([81d50c0](https://github.com/CQCL/guppylang/commit/81d50c0a24f55eca48d62e4b0275ef2126c5e626))
