use hugr::{self, ops::custom::resolve_extension_ops, std_extensions};
use hugr::{
    extension::ExtensionRegistry,
    hugr::views::{HierarchyView, SiblingGraph},
    ops, HugrView,
};
use hugr_llvm;
use hugr_llvm::fat::FatExt;
use inkwell::{context::Context, module::Module, values::GenericValue};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

macro_rules! pyerr {
    ($fmt:literal $(,$arg:tt)*) => { PyValueError::new_err(format!($fmt, $($arg),*)) }
}

fn parse_hugr(hugr_json: &str) -> PyResult<hugr::Hugr> {
    // Deserializing should be a given if we validate before running
    let mut hugr =
        serde_json::from_str(hugr_json).map_err(|_| pyerr!("Couldn't deserialize hugr"))?;
    let reg = ExtensionRegistry::try_new([
        hugr::extension::PRELUDE.to_owned(),
        std_extensions::arithmetic::int_ops::EXTENSION.to_owned(),
        std_extensions::arithmetic::int_types::EXTENSION.to_owned(),
        std_extensions::arithmetic::float_ops::EXTENSION.to_owned(),
        std_extensions::arithmetic::float_types::EXTENSION.to_owned(),
        std_extensions::arithmetic::conversions::EXTENSION.to_owned(),
        std_extensions::collections::EXTENSION.to_owned(),
        std_extensions::logic::EXTENSION.to_owned(),
    ])
    .map_err(|e| pyerr!("Making extension registry: {}", e))?;
    resolve_extension_ops(&mut hugr, &reg)
        .map_err(|e| pyerr!("Instantiating extension ops: {}", e))
    Ok(hugr)
}

// Find the FuncDefn node for the function we're trying to execute.
fn find_funcdef_node(hugr: impl HugrView, fn_name: &str) -> PyResult<hugr::Node> {
    let root = hugr.root();
    let sibs: SiblingGraph = SiblingGraph::try_new(&hugr, root).map_err(|e| pyerr!("{}", e))?;
    let mut fn_nodes = Vec::new();
    for n in sibs.nodes() {
        let op = sibs.get_optype(n);
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

fn compile_module<'a>(
    hugr: &'a hugr::Hugr,
    ctx: &'a Context,
    namer: hugr_llvm::emit::Namer,
) -> PyResult<Module<'a>> {
    let llvm_module = ctx.create_module("guppy_llvm");
    // TODO: Handle tket2 codegen extension
    let extensions = hugr_llvm::custom::CodegenExtsMap::default()
        .add_int_extensions()
        .add_default_prelude_extensions()
        .add_float_extensions();
    let emitter =
        hugr_llvm::emit::EmitHugr::new(&ctx, llvm_module, namer.into(), extensions.into());
    let hugr_module = hugr.fat_root().unwrap();
    let emitter = emitter
        .emit_module(hugr_module)
        .map_err(|e| pyerr!("Error compiling to llvm: {}", e))?;

    let module = emitter.finish();

    Ok(module)
}

#[pyfunction]
fn compile_module_to_string(hugr_json: &str) -> PyResult<String> {
    let hugr = parse_hugr(hugr_json)?;
    let ctx = Context::create();

    let module = compile_module(&hugr, &ctx, Default::default())?;

    Ok(module.print_to_string().to_str().unwrap().to_string())
}

fn run_function<T>(
    hugr_json: &str,
    fn_name: &str,
    parse_result: impl FnOnce(GenericValue) -> PyResult<T>,
) -> PyResult<T>
{
    let hugr = parse_hugr(hugr_json)?;
    let ctx = Context::create();

    let namer = hugr_llvm::emit::Namer::default();
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
    parse_result(llvm_result)
}

#[pyfunction]
fn run_int_function(hugr_json: &str, fn_name: &str) -> PyResult<i64> {
    run_function::<i64>(hugr_json, fn_name, |llvm_val| {
        // GenericVal is 64 bits wide
        let int_with_sign = llvm_val.as_int(true);
        let unsigned_int = u64::try_from(int_with_sign).map_err(|e| pyerr!("Reading back llvm value: {}", e))?;
        let signed_int = unsigned_int as i64;
        Ok(signed_int)
    })
}

#[pymodule]
fn execute_llvm(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(compile_module_to_string, m)?)?;
    m.add_function(wrap_pyfunction!(run_int_function, m)?)?;
    Ok(())
}
