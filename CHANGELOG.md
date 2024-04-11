# Changelog

## 0.2.0 (2024-04-11)


### ⚠ BREAKING CHANGES

* Make `qubit` type lower case ([#165](https://github.com/CQCL/guppylang/issues/165))
* Add remaining tket2 ops ([#107](https://github.com/CQCL/guppylang/issues/107))
* rename package to guppylang ([#108](https://github.com/CQCL/guppylang/issues/108))
* conform to hugr schema ([#93](https://github.com/CQCL/guppylang/issues/93))

### Features

* Add compile-time Python expressions ([#74](https://github.com/CQCL/guppylang/issues/74)) ([7100132](https://github.com/CQCL/guppylang/commit/7100132fc15757c67e9c8f5f5c7f233c2fa31e8e))
* Add hugr-to-json encoding, and validate it ([06b3b16](https://github.com/CQCL/guppylang/commit/06b3b16c4ae89eaf9d049a8e8f83d3aba21a4fca))
* Add hugr-to-json encoding, and validate it ([#83](https://github.com/CQCL/guppylang/issues/83)) ([b441a3e](https://github.com/CQCL/guppylang/commit/b441a3e8b4f0271e813f72fa468b6102acbfc21f))
* Add iterators and lists ([#67](https://github.com/CQCL/guppylang/issues/67)) ([69fac9c](https://github.com/CQCL/guppylang/commit/69fac9c4111017206e51a6db93318e1662fc62ce))
* Add module load method to guppy ([#126](https://github.com/CQCL/guppylang/issues/126)) ([5204850](https://github.com/CQCL/guppylang/commit/52048508231ca942acc9e4559375d9c5ee60a5fb))
* Add polymorphism ([#61](https://github.com/CQCL/guppylang/issues/61)) ([d0cf104](https://github.com/CQCL/guppylang/commit/d0cf10434a3d33a8cc96050c1e611c646bd81cc9))
* Add remaining tket2 ops ([#107](https://github.com/CQCL/guppylang/issues/107)) ([e0761ff](https://github.com/CQCL/guppylang/commit/e0761ffd876d44d13aefeaac17fe6058932cbf80))
* add top-level imports ([#125](https://github.com/CQCL/guppylang/issues/125)) ([e3da1ec](https://github.com/CQCL/guppylang/commit/e3da1eca85e67890e4bd96154fdcde8b129b0243)), closes [#127](https://github.com/CQCL/guppylang/issues/127)
* Allow lists in py expressions ([#113](https://github.com/CQCL/guppylang/issues/113)) ([caaf562](https://github.com/CQCL/guppylang/commit/caaf5627ed19b171cda339b3e79954ce603effbf))
* Allow pytket circuits in py expressions ([#115](https://github.com/CQCL/guppylang/issues/115)) ([67d1a7e](https://github.com/CQCL/guppylang/commit/67d1a7e79c5ff439595f1a0e13fd7f8e3d6fbc6f))
* Local implicit modules for [@guppy](https://github.com/guppy) ([#105](https://github.com/CQCL/guppylang/issues/105)) ([f52a5de](https://github.com/CQCL/guppylang/commit/f52a5de95972d028167f5800d16573c178c9e2be))
* New type representation with parameters ([#174](https://github.com/CQCL/guppylang/issues/174)) ([73e29f2](https://github.com/CQCL/guppylang/commit/73e29f25ec90b8dfcc6517b961d6d1d13f694cb6))
* Utility methods to check if a module contains a fn/type ([f10de74](https://github.com/CQCL/guppylang/commit/f10de74689b3547c2a58a40558081c42bc0d0c3a))
* Utility methods to check if a module contains a fn/type ([a70470d](https://github.com/CQCL/guppylang/commit/a70470dae8b5bae1c44cba713e4f2925ee7bfedd))
* Utility methods to check if a module contains a fn/type ([#92](https://github.com/CQCL/guppylang/issues/92)) ([f10de74](https://github.com/CQCL/guppylang/commit/f10de74689b3547c2a58a40558081c42bc0d0c3a))


### Bug Fixes

* correct order of basic block successors ([#110](https://github.com/CQCL/guppylang/issues/110)) ([a42db7d](https://github.com/CQCL/guppylang/commit/a42db7dcda1e0b31e0f02b60f5800e695475cc99))
* Correctly store names of function definitions/declarations ([#47](https://github.com/CQCL/guppylang/issues/47)) ([a7537bb](https://github.com/CQCL/guppylang/commit/a7537bbd309a19766e517caa07b3bc3c8a74a813))
* default input extensions should be None ([#99](https://github.com/CQCL/guppylang/issues/99)) ([7fac597](https://github.com/CQCL/guppylang/commit/7fac597cec6b51c5cdbf09037952076d9803b4c1))
* Make dummy decl names unique ([#49](https://github.com/CQCL/guppylang/issues/49)) ([21e7094](https://github.com/CQCL/guppylang/commit/21e7094620742bc3cdaf4eafa1fd0d4a192e7518))
* make tket2 group rather than extra ([#128](https://github.com/CQCL/guppylang/issues/128)) ([3a69336](https://github.com/CQCL/guppylang/commit/3a69336cf4b7300a546e83abf3db8c99bfe65c0f))
* Make ZZMax a dyadic operation ([#168](https://github.com/CQCL/guppylang/issues/168)) ([152485f](https://github.com/CQCL/guppylang/commit/152485f08ef61c3450da1e8b03eee883558a6871)), closes [#154](https://github.com/CQCL/guppylang/issues/154)
* Return `in_port`/`out_port` for order edges ([c371f84](https://github.com/CQCL/guppylang/commit/c371f840ec64bdbfe9b45bbe52d57b8098bcb049))
* Return `in_port`/`out_port` for order edges ([#84](https://github.com/CQCL/guppylang/issues/84)) ([137941f](https://github.com/CQCL/guppylang/commit/137941f9d1ddab25f1c0c662d79029a241dcbfa4))
* Stop exiting interpreter on error ([#140](https://github.com/CQCL/guppylang/issues/140)) ([728e449](https://github.com/CQCL/guppylang/commit/728e44921f20b227ed92f89daae513798701ef62))
* Use correct TK2 gate names ([#190](https://github.com/CQCL/guppylang/issues/190)) ([df92642](https://github.com/CQCL/guppylang/commit/df92642c35b977c0d318747ac1d4011061d6e171))
* Use panicking division ops ([#56](https://github.com/CQCL/guppylang/issues/56)) ([c20233b](https://github.com/CQCL/guppylang/commit/c20233b96cd0fa12208c563134ef6c07234ebffc))


### Documentation

* Add licence file ([9edcd4a](https://github.com/CQCL/guppylang/commit/9edcd4ac9a42d1bbc758959761414e11dd954523))
* Add licence file ([#81](https://github.com/CQCL/guppylang/issues/81)) ([29008c0](https://github.com/CQCL/guppylang/commit/29008c0bfd9c521c5598fd9cdf1b8e090e69f650))
* add reference to runner to readme ([#129](https://github.com/CQCL/guppylang/issues/129)) ([45c2bf0](https://github.com/CQCL/guppylang/commit/45c2bf010a719785527e1c5cc2ac650975e84d4d))
* add repository to readme ([#117](https://github.com/CQCL/guppylang/issues/117)) ([c63bb0e](https://github.com/CQCL/guppylang/commit/c63bb0e0f2efb206219470aa483f5b730e45d902))
* Add short description and simplify readme for pypi ([#136](https://github.com/CQCL/guppylang/issues/136)) ([667bba3](https://github.com/CQCL/guppylang/commit/667bba380e7bd38d2e1c66e8e6b67dfbba4efa05))


### Miscellaneous Chores

* rename package to guppylang ([#108](https://github.com/CQCL/guppylang/issues/108)) ([888d81d](https://github.com/CQCL/guppylang/commit/888d81d071be3b6fde07daf6a01d7d4203de7a97))


### Code Refactoring

* conform to hugr schema ([#93](https://github.com/CQCL/guppylang/issues/93)) ([ee5f469](https://github.com/CQCL/guppylang/commit/ee5f469afda44abc52dee0cacacf8e6d9ac1753d))
* Make `qubit` type lower case ([#165](https://github.com/CQCL/guppylang/issues/165)) ([0a42097](https://github.com/CQCL/guppylang/commit/0a42097f617a231a7c6a3096b5d12bda6b19e0aa))


### Continuous Integration

* Use `release-please bootstrap`'s default config ([#187](https://github.com/CQCL/guppylang/issues/187)) ([72e666a](https://github.com/CQCL/guppylang/commit/72e666af5a52c44a4094080a665342422a242d2b))

## [0.1.0](https://github.com/CQCL/guppy/releases/tag/v0.1.0)

First release of Guppy! 🐟

This is an alpha release that implements basic language features and compilation to hugr v0.1.
