//! Utilities for validating Guppy programs.

use std::path::{Path, PathBuf};
use std::time::SystemTime;
use thiserror::Error;

use cargo_toml::{Dependency, Manifest};

/// Attributes describing a package dependency with a binary artifact.
#[derive(Debug, Clone, PartialEq)]
pub struct DependencyInfo {
    /// Name of the package.
    pub name: String,
    /// Name of the binary artifact. If not specified, defaults to `name`.
    pub bin_name: Option<String>,
    /// Resolved dependency specification.
    pub dep: Dependency,
}

/// Error type for `DependencyInfo`.
#[derive(Debug, Clone, PartialEq, Error)]
pub enum DependencyError {
    /// Failed to find the dependency in the package manifest.
    #[error("Dependency `{0}` not found in package manifest")]
    DependencyNotFound(String),
    /// An error occurred while running `cargo install`.
    #[error("Failed to install dependency `{0}`: {1}")]
    InstallError(String, String),
}

impl DependencyInfo {
    /// Given a package manifest and a workspace manifest, reads the dependency
    /// definition for `pkg`, including the version and git sources.
    ///
    /// If the package manifest contains a `[patch.*]` override for `pkg`, that
    /// definition is returned. Otherwise, the `[dependencies]` section is checked.
    pub fn from_manifest(
        pkg: &str,
        pkg_manifest: &Manifest,
        ws_manifest: &Option<Manifest>,
    ) -> Result<Self, DependencyError> {
        // First, read the dependency version and overrides from the package and workspace manifests
        let dep = Self::read_dependency(pkg_manifest, ws_manifest, pkg)
            .ok_or(DependencyError::DependencyNotFound(pkg.to_string()))?;

        Ok(Self {
            name: pkg.to_string(),
            bin_name: None,
            dep,
        })
    }

    /// Selects a binary artifact with a different name than the package name.
    pub fn with_bin_name(self, bin_name: &str) -> Self {
        Self {
            bin_name: Some(bin_name.to_string()),
            ..self
        }
    }

    /// The path to the binary artifact.
    pub fn bin_path(&self, target_dir: &Path) -> PathBuf {
        let bin = self.bin_name.as_ref().unwrap_or(&self.name);
        target_dir.join("bin").join(bin)
    }

    /// Given a package manifest and a workspace manifest, return the dependency
    /// definition for `pkg`.
    ///
    /// If the package manifest contains a `[patch.*]` override for `pkg`, that
    /// definition is returned. Otherwise, the `[dependencies]` section is checked.
    fn read_dependency(
        pkg_manifest: &Manifest,
        ws_manifest: &Option<Manifest>,
        pkg: &str,
    ) -> Option<Dependency> {
        // First check the workspace for `[patch.*]` overrides
        for patch in ws_manifest.iter().flat_map(|m| m.patch.iter()) {
            if let Some(dep) = patch.1.get(pkg) {
                return Some(dep.clone());
            }
        }

        // Then check the `[dependencies]` section in the package manifest
        if let Some(dep) = pkg_manifest.dependencies.get(pkg) {
            return Some(dep.clone());
        }

        None
    }

    /// Install the package's binary artifact using `cargo install`, on a local directory.
    ///
    /// Returns the path to the installed binary.
    pub fn cargo_install(self, target_dir: &Path) -> Result<PathBuf, DependencyError> {
        let mut cmd = std::process::Command::new("cargo");
        cmd.arg("install")
            .arg("--root")
            .arg(target_dir)
            .arg("--quiet");

        let pkg_name = match &self.dep {
            Dependency::Simple(version) => format!("{}@{version}", self.name),
            _ => self.name.to_string(),
        };
        cmd.arg(pkg_name);

        // Add git source information if available
        if let Some(git) = &self.dep.git() {
            cmd.arg("--git").arg(git);

            if let Some(rev) = &self.dep.git_rev() {
                cmd.arg("--rev").arg(rev);
            }

            if let Some(branch) = &self.dep.detail().and_then(|d| d.branch.clone()) {
                cmd.arg("--branch").arg(branch);
            }

            if let Some(tag) = &self.dep.detail().and_then(|d| d.tag.clone()) {
                cmd.arg("--tag").arg(tag);
            }
        }

        let mut spawned = cmd
            .spawn()
            .map_err(|e| DependencyError::InstallError(self.name.clone(), e.to_string()))?;
        spawned
            .wait()
            .map_err(|e| DependencyError::InstallError(self.name.clone(), e.to_string()))?;

        // Ensure that we see the binary as modified the next time we run the validator
        let bin_path = self.bin_path(target_dir);
        let file = std::fs::File::open(&bin_path).unwrap();
        file.set_modified(SystemTime::now()).unwrap();

        Ok(bin_path)
    }
}
