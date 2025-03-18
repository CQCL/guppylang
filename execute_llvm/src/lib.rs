//! This module provides a Python interface to compile and execute a Hugr program to LLVM IR.
use hugr::llvm::custom::CodegenExtsMap;
use hugr::llvm::utils::fat::FatExt;
use hugr::llvm::CodegenExtsBuilder;
use hugr::package::Package;
use hugr::Hugr;
use hugr::{self, ops, std_extensions, HugrView};
use inkwell::{context::Context, module::Module, values::GenericValue};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

macro_rules! pyerr {
    ($fmt:literal $(,$arg:tt)*) => { PyValueError::new_err(format!($fmt, $($arg),*)) }
}

fn parse_hugr(pkg_bytes: &[u8]) -> PyResult<hugr::Hugr> {
    let mut pkg = Package::load(pkg_bytes, Some(&std_extensions::std_reg()))
        .map_err(|e| pyerr!("Couldn't deserialize hugr: {}", e))?;
    let hugr = std::mem::take(&mut pkg.modules[0]);
    println!("{}", hugr.mermaid_string());
    Ok(hugr)
}

// Find the FuncDefn node for the function we're trying to execute.
fn find_funcdef_node<H: HugrView>(hugr: H, fn_name: &str) -> PyResult<H::Node> {
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

fn guppy_pass(hugr: &mut Hugr, entry_fn: &str) {
    hugr::algorithms::MonomorphizePass::default()
        .run(hugr)
        .unwrap();
    hugr::algorithms::RemoveDeadFuncsPass::default()
        .with_module_entry_points([
            find_funcdef_node(&hugr, entry_fn).expect("entry point function error.")
        ])
        .run(hugr)
        .unwrap();
}

fn codegen_extensions() -> CodegenExtsMap<'static, Hugr> {
    CodegenExtsBuilder::default()
        .add_default_prelude_extensions()
        .add_int_extensions()
        .add_float_extensions()
        .add_conversion_extensions()
        .add_logic_extensions()
        .add_default_array_extensions()
        .finish()
}

fn compile_module<'a>(
    hugr: &'a hugr::Hugr,
    ctx: &'a Context,
    namer: hugr::llvm::emit::Namer,
) -> PyResult<Module<'a>> {
    let llvm_module = ctx.create_module("guppy_llvm");
    // TODO: Handle tket2 codegen extension
    let extensions = codegen_extensions();

    let emitter =
        hugr::llvm::emit::EmitHugr::new(ctx, llvm_module, namer.into(), extensions.into());
    let hugr_module = hugr.fat_root().unwrap();
    let emitter = emitter
        .emit_module(hugr_module)
        .map_err(|e| pyerr!("Error compiling to llvm: {}", e))?;

    Ok(emitter.finish())
}

fn run_function<T>(
    pkg_bytes: &[u8],
    fn_name: &str,
    parse_result: impl FnOnce(&Context, GenericValue) -> PyResult<T>,
) -> PyResult<T> {
    let mut hugr = parse_hugr(pkg_bytes)?;
    guppy_pass(&mut hugr, fn_name);
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

#[pymodule]
mod execute_llvm {
    use inkwell::context::Context;
    use pyo3::pyfunction;

    use super::*;

    #[pyfunction]
    fn compile_module_to_string(pkg_bytes: &[u8]) -> PyResult<String> {
        let mut hugr = parse_hugr(pkg_bytes)?;
        let ctx = Context::create();

        guppy_pass(&mut hugr, "main");
        let module = compile_module(&hugr, &ctx, Default::default())?;

        Ok(module.print_to_string().to_str().unwrap().to_string())
    }

    #[pyfunction]
    fn run_int_function(pkg_bytes: &[u8], fn_name: &str) -> PyResult<i64> {
        run_function::<i64>(pkg_bytes, fn_name, |_, llvm_val| {
            // GenericVal is 64 bits wide
            let int_with_sign = llvm_val.as_int(true);
            let signed_int = int_with_sign as i64;
            Ok(signed_int)
        })
    }

    #[pyfunction]
    fn run_float_function(pkg_bytes: &[u8], fn_name: &str) -> PyResult<f64> {
        run_function::<f64>(pkg_bytes, fn_name, |ctx, llvm_val| {
            Ok(llvm_val.as_float(&ctx.f64_type()))
        })
    }
}
