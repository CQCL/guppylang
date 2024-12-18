//! This module provides a Python interface to compile and execute a Hugr program to LLVM IR.
use hugr::llvm::utils::fat::FatExt;
use hugr::Hugr;
use hugr::{self, ops, std_extensions, HugrView};
use inkwell::{context::Context, module::Module, values::GenericValue};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

macro_rules! pyerr {
    ($fmt:literal $(,$arg:tt)*) => { PyValueError::new_err(format!($fmt, $($arg),*)) }
}

fn parse_hugr(hugr_json: &str) -> PyResult<hugr::Hugr> {
    let hugr = Hugr::load_json(hugr_json.as_bytes(), &std_extensions::std_reg())
        .map_err(|e| pyerr!("Couldn't deserialize hugr: {}", e))?;
    Ok(hugr)
}

// Find the FuncDefn node for the function we're trying to execute.
fn find_funcdef_node(hugr: impl HugrView, fn_name: &str) -> PyResult<hugr::Node> {
    let root = hugr.root();
    let mut fn_nodes = Vec::new();
    for n in hugr.children(root) {
        let op = hugr.get_optype(n);
        if let ops::OpType::FuncDefn(ops::FuncDefn { name, .. }) = op {
            if name == fn_name {
                fn_nodes.push(n);
            }
        }
    }
    match fn_nodes[..] {
        [] => Err(pyerr!("Couldn't find top level FuncDefn named {}", fn_name)),
        [x] => Ok(x),
        _ => Err(pyerr!(
            "Found multiple top level FuncDefn nodes named {}",
            fn_name
        )),
    }
}

fn guppy_pass(hugr: Hugr) -> Hugr {
    let hugr = hugr::algorithms::monomorphize(hugr);
    hugr::algorithms::remove_polyfuncs(hugr)
}

fn compile_module<'a>(
    hugr: &'a hugr::Hugr,
    ctx: &'a Context,
    namer: hugr::llvm::emit::Namer,
) -> PyResult<Module<'a>> {
    let llvm_module = ctx.create_module("guppy_llvm");
    // TODO: Handle tket2 codegen extension
    let extensions = hugr::llvm::custom::CodegenExtsBuilder::default()
        .add_int_extensions()
        .add_logic_extensions()
        .add_default_prelude_extensions()
        .add_default_array_extensions()
        .add_float_extensions()
        .add_conversion_extensions();

    let emitter =
        hugr::llvm::emit::EmitHugr::new(ctx, llvm_module, namer.into(), extensions.finish().into());
    let hugr_module = hugr.fat_root().unwrap();
    let emitter = emitter
        .emit_module(hugr_module)
        .map_err(|e| pyerr!("Error compiling to llvm: {}", e))?;

    Ok(emitter.finish())
}

#[pyfunction]
fn compile_module_to_string(hugr_json: &str) -> PyResult<String> {
    let mut hugr = parse_hugr(hugr_json)?;
    let ctx = Context::create();

    hugr = guppy_pass(hugr);
    let module = compile_module(&hugr, &ctx, Default::default())?;

    Ok(module.print_to_string().to_str().unwrap().to_string())
}

fn run_function<T>(
    hugr_json: &str,
    fn_name: &str,
    parse_result: impl FnOnce(&Context, GenericValue) -> PyResult<T>,
) -> PyResult<T> {
    let mut hugr = parse_hugr(hugr_json)?;
    hugr = guppy_pass(hugr);
    let ctx = Context::create();

    let namer = hugr::llvm::emit::Namer::default();
    let funcdefn_node = find_funcdef_node(&hugr, fn_name)?;
    let mangled_name = namer.name_func(fn_name, funcdefn_node);

    let module = compile_module(&hugr, &ctx, namer)?;

    let fv = module
        .get_function(&mangled_name)
        .ok_or(pyerr!("Couldn't find function {} in module", mangled_name))?;

    let ee = module
        .create_execution_engine()
        .map_err(|_| pyerr!("Failed to create execution engine"))?;
    let llvm_result = unsafe { ee.run_function(fv, &[]) };
    parse_result(&ctx, llvm_result)
}

#[pyfunction]
fn run_int_function(hugr_json: &str, fn_name: &str) -> PyResult<i64> {
    run_function::<i64>(hugr_json, fn_name, |_, llvm_val| {
        // GenericVal is 64 bits wide
        let int_with_sign = llvm_val.as_int(true);
        let signed_int = int_with_sign as i64;
        Ok(signed_int)
    })
}

#[pyfunction]
fn run_float_function(hugr_json: &str, fn_name: &str) -> PyResult<f64> {
    run_function::<f64>(hugr_json, fn_name, |ctx, llvm_val| {
        Ok(llvm_val.as_float(&ctx.f64_type()))
    })
}

#[pymodule]
fn execute_llvm(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(compile_module_to_string, m)?)?;
    m.add_function(wrap_pyfunction!(run_int_function, m)?)?;
    m.add_function(wrap_pyfunction!(run_float_function, m)?)?;
    Ok(())
}
