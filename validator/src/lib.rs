use pyo3::prelude::*;
use hugr::{self, algorithm::nest_cfgs::{transform_cfg_to_nested, SimpleCfgView}};

#[pyfunction]
fn validate(hugr: Vec<u8>) -> PyResult<bool> {
    let hg: hugr::Hugr = rmp_serde::from_slice(&hugr).unwrap();
    let res = hg.validate();

    Ok(res.is_ok())
}

#[pyfunction]
fn nest_cfg(hugr: Vec<u8>) -> PyResult<()> {
    let mut h: hugr::Hugr = rmp_serde::from_slice(&hugr).unwrap();
    transform_cfg_to_nested(&mut SimpleCfgView::new(&mut h)).unwrap();
    h.validate().unwrap();

    Ok(())
}

#[pymodule]
fn validator(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(validate, m)?)?;
    m.add_function(wrap_pyfunction!(nest_cfg, m)?)?;
    Ok(())
}
