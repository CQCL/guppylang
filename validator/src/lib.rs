use pyo3::prelude::*;
use hugr;

#[pyfunction]
fn validate(hugr: Vec<u8>) -> PyResult<bool> {
    let hg: hugr::Hugr = rmp_serde::from_slice(&hugr).unwrap();
    let res = hg.validate();

    Ok(res.is_ok())
}

#[pymodule]
fn validator(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(validate, m)?)?;
    Ok(())
}