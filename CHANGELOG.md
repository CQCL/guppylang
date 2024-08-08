# Changelog

## [0.8.1](https://github.com/CQCL/guppylang/compare/v0.8.0...v0.8.1) (2024-08-08)


### Bug Fixes

* Fix invalid result operation name ([#367](https://github.com/CQCL/guppylang/issues/367)) ([568624d](https://github.com/CQCL/guppylang/commit/568624d1ccd70dc78c16f4ca2170dc167791ea64))
* Linearity checking bug ([#355](https://github.com/CQCL/guppylang/issues/355)) ([e14660f](https://github.com/CQCL/guppylang/commit/e14660f2b31d104c7fb0b5cb8806c3656098afbb))

## [0.8.0](https://github.com/CQCL/guppylang/compare/v0.7.0...v0.8.0) (2024-07-30)


### Features

* Parse docstrings for functions ([#334](https://github.com/CQCL/guppylang/issues/334)) ([a7cc97a](https://github.com/CQCL/guppylang/commit/a7cc97a6c1af674972c3a37e28ef7e33ddf6fa3d))


### Bug Fixes

* Use places in BB signatures for Hugr generation ([#342](https://github.com/CQCL/guppylang/issues/342)) ([48b0e35](https://github.com/CQCL/guppylang/commit/48b0e352d835298b66ea90ff12528391c1c0e2a3))

## [0.7.0](https://github.com/CQCL/guppylang/compare/v0.6.2...v0.7.0) (2024-07-25)


### ⚠ BREAKING CHANGES

* `qubit`s are now reset on allocation

### Features

* `qubit`s are now reset on allocation, and `dirty_qubit` added ([#325](https://github.com/CQCL/guppylang/issues/325)) ([4a9e205](https://github.com/CQCL/guppylang/commit/4a9e20529a4d0859f010fad62ba06f62ca1c98ce))
* Allow access to struct fields and mutation of linear ones ([#295](https://github.com/CQCL/guppylang/issues/295)) ([6698b75](https://github.com/CQCL/guppylang/commit/6698b75b01421cd1fa545219786266fb0c1da05b)), closes [#293](https://github.com/CQCL/guppylang/issues/293)
* Allow redefinition of names in guppy modules ([#326](https://github.com/CQCL/guppylang/issues/326)) ([314409c](https://github.com/CQCL/guppylang/commit/314409cd63b544d0fdbf16db66201b08dead81fe)), closes [#307](https://github.com/CQCL/guppylang/issues/307)


### Bug Fixes

* Use correct hook for error printing inside jupyter notebooks ([#324](https://github.com/CQCL/guppylang/issues/324)) ([bfdb003](https://github.com/CQCL/guppylang/commit/bfdb003d454d3d8fb6385c2c758dab56ab622496)), closes [#323](https://github.com/CQCL/guppylang/issues/323)

## [0.6.2](https://github.com/CQCL/guppylang/compare/v0.6.1...v0.6.2) (2024-07-10)


### Features

* update to hugr-python 0.4  ([af770c3](https://github.com/CQCL/guppylang/commit/af770c31536a59c32fd8229579455a309e90058e))

## [0.6.1](https://github.com/CQCL/guppylang/compare/v0.6.0...v0.6.1) (2024-07-09)


### Features

* update to `hugr-py 0.3` ([3da3936](https://github.com/CQCL/guppylang/commit/3da393674de7d03dd0d5d5b8239dd8968d16c4c4))

## [0.6.0](https://github.com/CQCL/guppylang/compare/v0.5.2...v0.6.0) (2024-07-02)


### Features

* Add array type ([#258](https://github.com/CQCL/guppylang/issues/258)) ([041c621](https://github.com/CQCL/guppylang/commit/041c621a0481f14ee517b0356e0ebb9cae6ddc2e))
* Add nat type ([#254](https://github.com/CQCL/guppylang/issues/254)) ([a461a9d](https://github.com/CQCL/guppylang/commit/a461a9d5556d7ed68da5a722100c8b3fb449b25e))
* Add result function ([#271](https://github.com/CQCL/guppylang/issues/271)) ([792fb87](https://github.com/CQCL/guppylang/commit/792fb871cac5b19905e87dd485e11d7488f2fb87)), closes [#270](https://github.com/CQCL/guppylang/issues/270)
* Allow constant nats as type args ([#255](https://github.com/CQCL/guppylang/issues/255)) ([d706735](https://github.com/CQCL/guppylang/commit/d7067356c71cbcc5352e69ea4eed6bdc1d0c1ec8))
* Generate constructor methods for structs ([#262](https://github.com/CQCL/guppylang/issues/262)) ([f68d0af](https://github.com/CQCL/guppylang/commit/f68d0afe74c75e40b49babe26091a24d822218f7)), closes [#261](https://github.com/CQCL/guppylang/issues/261)
* Return already-compiled hugrs from `GuppyModule.compile` ([#247](https://github.com/CQCL/guppylang/issues/247)) ([9d01eae](https://github.com/CQCL/guppylang/commit/9d01eae8e4db21a95ad3e97d4e78fea7b4b32c08))
* Turn int and float into core types ([#225](https://github.com/CQCL/guppylang/issues/225)) ([99217dc](https://github.com/CQCL/guppylang/commit/99217dcddb16fa7c713b7e5c5d356715a0fc9496))


### Bug Fixes

* Add missing test file ([#266](https://github.com/CQCL/guppylang/issues/266)) ([75231fe](https://github.com/CQCL/guppylang/commit/75231fe509c52945d44eadb2aa238d1eecf01b0c))
* Loading custom polymorphic function defs as values ([#260](https://github.com/CQCL/guppylang/issues/260)) ([d15b2f5](https://github.com/CQCL/guppylang/commit/d15b2f5a2c012924436ecd3ab482099654a1752e)), closes [#259](https://github.com/CQCL/guppylang/issues/259)

## [0.5.2](https://github.com/CQCL/guppylang/compare/v0.5.1...v0.5.2) (2024-06-13)


### Bug Fixes

* Don't reorder inputs of entry BB ([#243](https://github.com/CQCL/guppylang/issues/243)) ([ad56b99](https://github.com/CQCL/guppylang/commit/ad56b991c03e1bc52690e41450521e7fe9100268))

## [0.5.1](https://github.com/CQCL/guppylang/compare/v0.5.0...v0.5.1) (2024-06-12)


### Bug Fixes

* Serialisation of bool values ([#239](https://github.com/CQCL/guppylang/issues/239)) ([16a77db](https://github.com/CQCL/guppylang/commit/16a77dbd4c5905eff6c4ddabe66b5ef1b8a7e15b))

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
