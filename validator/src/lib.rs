use hugr::extension::{ExtensionRegistry, PRELUDE};
use hugr::std_extensions::arithmetic::{float_ops, float_types, int_ops, int_types};
use hugr::std_extensions::collections;
use hugr::std_extensions::logic;
use lazy_static::lazy_static;
use pyo3::prelude::*;
use tket2::extension::{TKET1_EXTENSION, TKET2_EXTENSION};

lazy_static! {
    pub static ref REGISTRY: ExtensionRegistry = ExtensionRegistry::try_new([
        PRELUDE.to_owned(),
        logic::EXTENSION.to_owned(),
        int_types::extension(),
        int_ops::EXTENSION.to_owned(),
        float_types::EXTENSION.to_owned(),
        float_ops::EXTENSION.to_owned(),
        collections::EXTENSION.to_owned(),
        TKET1_EXTENSION.to_owned(),
        TKET2_EXTENSION.to_owned(),
    ])
    .unwrap();
}

/// Validate a json-encoded Hugr
#[pyfunction]
fn validate_json(hugr: String) -> PyResult<()> {
    let hg: hugr::Hugr = serde_json::from_str(&hugr).unwrap();
    hg.validate(&REGISTRY).unwrap();
    Ok(())
}

#[pymodule]
fn guppyval(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(validate_json, m)?)?;
    Ok(())
}
