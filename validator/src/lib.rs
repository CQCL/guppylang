use pyo3::prelude::*;
use hugr;

#[pyfunction]
fn validate(hugr: Vec<u8>) -> PyResult<()> {
    let hg: hugr::Hugr = rmp_serde::from_slice(&hugr).unwrap();
    hg.validate().unwrap();

    Ok(())
}

#[pymodule]
fn validator(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(validate, m)?)?;
    Ok(())
}