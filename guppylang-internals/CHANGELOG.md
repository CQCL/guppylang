# Changelog

First release of `guppylang_internals` package containing refactored out internal components
from `guppylang`.

## [0.21.2](https://github.com/CQCL/guppylang/compare/guppylang-internals-v0.21.1...guppylang-internals-v0.21.2) (2025-08-11)


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
