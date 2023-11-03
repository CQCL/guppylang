# Test Guppy execution on PECOS

`guppy2phir.py` is a script in which you can define a guppy function, compile it
to HUGR, and execute it using PECOS.

Currently supported are quantum operations (including rotation gates with
constant parameters) and integer arithmetic. **Control flow is not yet supported**.

Requirements: 
* a python environment with Guppy and
[PECOS](https://github.com/PECOS-packages/PECOS) installed.
* A binary available somewhere of the
  [`hugr2phir`](https://github.com/CQCL/tket2/tree/feat/phir/hugr2phir) utility.
  The path to this will need to be set in the script as the `HUGR2PHIR` constant.

Optional:
If you want to validate the PHIR output using
[phir-cli](https://github.com/CQCL/phir) you will need the path to the
`phir-cli` executable (installed when you `pip install phir`) set in the
`PHIR_CLI` constant in the script.
