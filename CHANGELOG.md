# Changelog

## [0.5.0](https://github.com/CQCL/guppylang/compare/v0.4.0...v0.5.0) (2024-06-10)


### Features

* Add extern symbols ([#236](https://github.com/CQCL/guppylang/issues/236)) ([977ccd8](https://github.com/CQCL/guppylang/commit/977ccd831a3df1bdf49582309bce065a865d3e31))

## [0.4.0](https://github.com/CQCL/guppylang/compare/v0.3.0...v0.4.0) (2024-05-30)


### Features

* Export py function ([6dca95d](https://github.com/CQCL/guppylang/commit/6dca95deda3cc5bd103df104e33991c9adce2be2))

## [0.3.0](https://github.com/CQCL/guppylang/compare/v0.2.0...v0.3.0) (2024-05-22)


### Features

* Add a unified definition system ([#179](https://github.com/CQCL/guppylang/issues/179)) ([ae71932](https://github.com/CQCL/guppylang/commit/ae71932a608ed5034c060972eb70265ae2dec88c))
* Add struct types ([#207](https://github.com/CQCL/guppylang/issues/207)) ([f7adb85](https://github.com/CQCL/guppylang/commit/f7adb85bfbc7498047471cdf6b232c6b5056e19e))
* Allow calling a tensor of functions ([#196](https://github.com/CQCL/guppylang/issues/196)) ([af4fb07](https://github.com/CQCL/guppylang/commit/af4fb07e4613c8ab5948a681ba336f1f49a49495))
* Upgrade Hugr and start using the shared Pydantic model ([#201](https://github.com/CQCL/guppylang/issues/201)) ([bd7e67a](https://github.com/CQCL/guppylang/commit/bd7e67a59df3c6a8eede15c8a62f4f555d539c9a))


### Bug Fixes

* Consider type when deciding whether to pack up returns ([#212](https://github.com/CQCL/guppylang/issues/212)) ([4f24a07](https://github.com/CQCL/guppylang/commit/4f24a071d3c0b475920141fc5847474f0621b703))
* Mypy tket2 error ([#220](https://github.com/CQCL/guppylang/issues/220)) ([7ad3908](https://github.com/CQCL/guppylang/commit/7ad3908e2bb2672028df3eaa2cd78883020e144f))
* Only use path when determining equality of implicit modules ([#216](https://github.com/CQCL/guppylang/issues/216)) ([6f47d4b](https://github.com/CQCL/guppylang/commit/6f47d4bce55115c6b82d86007f75f40d46796b24))
* Serialisation of float values ([#219](https://github.com/CQCL/guppylang/issues/219)) ([937260a](https://github.com/CQCL/guppylang/commit/937260af694fbbd5bd217f23d20f13ee4759757c)), closes [#218](https://github.com/CQCL/guppylang/issues/218)


### Documentation

* Add compiler API docs ([#194](https://github.com/CQCL/guppylang/issues/194)) ([c3dd9bd](https://github.com/CQCL/guppylang/commit/c3dd9bdf19cbfeb23b792376f2fedf8f4f4dbeaf))
* Add pypi and python version badges to the README ([#192](https://github.com/CQCL/guppylang/issues/192)) ([7fecc45](https://github.com/CQCL/guppylang/commit/7fecc45f3fce8489872dbe65c6012f7cd0b8dc61))

## 0.2.0 (2024-04-11)


### ⚠ BREAKING CHANGES

* Make `qubit` type lower case ([#165](https://github.com/CQCL/guppylang/issues/165))

### Features

* Local implicit modules for `@guppy` ([#105](https://github.com/CQCL/guppylang/issues/105)) ([f52a5de](https://github.com/CQCL/guppylang/commit/f52a5de95972d028167f5800d16573c178c9e2be))
* New type representation with parameters ([#174](https://github.com/CQCL/guppylang/issues/174)) ([73e29f2](https://github.com/CQCL/guppylang/commit/73e29f25ec90b8dfcc6517b961d6d1d13f694cb6))


### Bug Fixes

* Make ZZMax a dyadic operation ([#168](https://github.com/CQCL/guppylang/issues/168)) ([152485f](https://github.com/CQCL/guppylang/commit/152485f08ef61c3450da1e8b03eee883558a6871)), closes [#154](https://github.com/CQCL/guppylang/issues/154)
* Stop exiting interpreter on error ([#140](https://github.com/CQCL/guppylang/issues/140)) ([728e449](https://github.com/CQCL/guppylang/commit/728e44921f20b227ed92f89daae513798701ef62))
* Use correct TK2 gate names ([#190](https://github.com/CQCL/guppylang/issues/190)) ([df92642](https://github.com/CQCL/guppylang/commit/df92642c35b977c0d318747ac1d4011061d6e171))


### Documentation

* add reference to runner to readme ([#129](https://github.com/CQCL/guppylang/issues/129)) ([45c2bf0](https://github.com/CQCL/guppylang/commit/45c2bf010a719785527e1c5cc2ac650975e84d4d))
* Add short description and simplify readme for pypi ([#136](https://github.com/CQCL/guppylang/issues/136)) ([667bba3](https://github.com/CQCL/guppylang/commit/667bba380e7bd38d2e1c66e8e6b67dfbba4efa05))


### Code Refactoring

* Make `qubit` type lower case ([#165](https://github.com/CQCL/guppylang/issues/165)) ([0a42097](https://github.com/CQCL/guppylang/commit/0a42097f617a231a7c6a3096b5d12bda6b19e0aa))


### Continuous Integration

* Use `release-please bootstrap`'s default config ([#187](https://github.com/CQCL/guppylang/issues/187)) ([72e666a](https://github.com/CQCL/guppylang/commit/72e666af5a52c44a4094080a665342422a242d2b))

## [0.1.0](https://github.com/CQCL/guppy/releases/tag/v0.1.0)

First release of Guppy! 🐟

This is an alpha release that implements basic language features and compilation to hugr v0.1.
