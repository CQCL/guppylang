//! Simple binary that locally installs `hugr-cli` and runs it.
//!
//! Uses the version of `hugr-cli` specified in the workspace Cargo.toml file.
//!
//! Inspired by `cargo`'s _xtasks_ modules.
//! https://github.com/rust-lang/cargo/blob/master/crates/xtask-lint-docs/src/main.rs

use core::panic;
use std::path::PathBuf;

use cargo_toml::Manifest;
use validator::DependencyInfo;

const PKG_NAME: &str = "hugr-cli";
const BIN_NAME: &str = "hugr";

fn main() {
    // Install the hugr-cli binary using `cargo install`.
    // First we check if the binary has already been installed since the last build,
    // and skip the installation if it is up to date.
    let hugr_cli = if let Some(bin) = cached_bin_path(BIN_NAME) {
        bin
    } else {
        // Otherwise, read the dependency version and overrides from the package and workspace manifests,
        // and call `cargo install`.
        let pkg_manifest =
            package_manifest().unwrap_or_else(|e| panic!("Failed to read package manifest: {e}"));
        let ws_manifest = workspace_manifest();
        if let Err(e) = &ws_manifest {
            eprintln!("Failed to read workspace manifest: {e}. Skipping.");
        }
        let dep: DependencyInfo =
            DependencyInfo::from_manifest(PKG_NAME, &pkg_manifest, &ws_manifest.ok())
                .unwrap_or_else(|e| panic!("{e}"))
                .with_bin_name(BIN_NAME);
        dep.cargo_install(&target_dir())
            .unwrap_or_else(|e| panic!("{e}"))
    };

    // Run the binary with all the passed arguments
    let mut cmd = std::process::Command::new(&hugr_cli);
    cmd.args(std::env::args().skip(1));
    let mut spawned = cmd
        .spawn()
        .unwrap_or_else(|e| panic!("Failed to spawn `{hugr_cli:?}`: {e}"));
    let exit_status = spawned.wait().unwrap_or_else(|e| panic!("{e}"));

    std::process::exit(exit_status.code().unwrap_or(1));
}

/// The path to the workspace manifest.
fn workspace_manifest() -> Result<Manifest, cargo_toml::Error> {
    let pkg_root = env!("CARGO_MANIFEST_DIR");
    let ws_toml = PathBuf::from(pkg_root).join("..").join("Cargo.toml");
    Manifest::from_path(&ws_toml)
}

/// The path to the package manifest.
fn package_manifest() -> Result<Manifest, cargo_toml::Error> {
    let pkg_root = env!("CARGO_MANIFEST_DIR");
    let pkg_toml = PathBuf::from(pkg_root).join("Cargo.toml");
    Manifest::from_path(&pkg_toml)
}

/// Target directory for the `hugr-cli` binary.
fn target_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("target")
}

/// Fast path when the binary has been installed since the last build
/// of the validator.
///
/// Compares the modification time of the binary with the last build time,
/// and skips the installation if the binary is up to date.
fn cached_bin_path(bin_name: &str) -> Option<PathBuf> {
    let self_path = std::env::current_exe().unwrap();
    let bin_path = target_dir().join("bin").join(bin_name);

    // Check that the binary has been modified since the last build.
    let bin_build_time = std::fs::symlink_metadata(&bin_path)
        .ok()?
        .modified()
        .unwrap();
    let self_build_time = std::fs::symlink_metadata(&self_path)
        .ok()?
        .modified()
        .unwrap();
    if bin_build_time > self_build_time {
        return Some(bin_path);
    }
    None
}
