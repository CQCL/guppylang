use hugr::extension::{ExtensionRegistry, PRELUDE};
use hugr::std_extensions::arithmetic::{float_ops, float_types, int_ops, int_types};
use hugr::std_extensions::logic;
use lazy_static::lazy_static;
use pyo3::prelude::*;

lazy_static! {
    pub static ref REGISTRY: ExtensionRegistry = ExtensionRegistry::try_new([
        PRELUDE.to_owned(),
        logic::EXTENSION.to_owned(),
        int_types::extension(),
        int_ops::EXTENSION.to_owned(),
        float_types::extension(),
        float_ops::extension()
    ])
    .unwrap();
}

#[pyfunction]
fn validate(hugr: Vec<u8>) -> PyResult<()> {
    let hg: hugr::Hugr = rmp_serde::from_slice(&hugr).unwrap();
    hg.validate(&REGISTRY).unwrap();
    Ok(())
}

#[pymodule]
fn validator(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(validate, m)?)?;
    Ok(())
}
