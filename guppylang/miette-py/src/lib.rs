use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use miette::{Diagnostic, GraphicalReportHandler, Report, NamedSource, LabeledSpan, SourceSpan, Severity, GraphicalTheme};
use thiserror::Error;
use std::fmt;

// Helper function to extract data for a SimpleError from a PyDict.
// Does not handle recursion for children.
fn pydict_to_simple_error_fields(py_dict: &Bound<'_, PyDict>) -> PyResult<(
    String,                 // message
    Option<String>,         // error_code
    Option<String>,         // help_message
    Option<Severity>,       // severity
    Option<NamedSource<String>>, // diagnostic_source_code
    Vec<LabeledSpan>        // labels
)> {
    let message = py_dict.get_item("message")?
        .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Child 'message' field is required"))?
        .extract::<String>()?;

    let error_code = py_dict.get_item("code")?
        .map(|item| item.extract::<String>())
        .transpose()?;

    let help_message = py_dict.get_item("help_text")?
        .map(|item| item.extract::<String>())
        .transpose()?;

    let severity_str: Option<String> = py_dict.get_item("severity_str")?
        .map(|item| item.extract::<String>())
        .transpose()?;
    
    let severity = severity_str.map(|s| {
        match s.to_uppercase().as_str() {
            "ERROR" => Severity::Error,
            "WARNING" => Severity::Warning,
            "ADVICE" | "INFO" => Severity::Advice,
            _ => Severity::Error, // Default
        }
    });

    let source_name: Option<String> = py_dict.get_item("source_name")?
        .map(|item| item.extract::<String>())
        .transpose()?;
    let source_text: Option<String> = py_dict.get_item("source_text")?
        .map(|item| item.extract::<String>())
        .transpose()?;
    
    let diagnostic_source_code = match (source_name, source_text) {
        (Some(name), Some(text)) => Some(NamedSource::new(name, text.into())),
        (None, Some(text)) => Some(NamedSource::new("source", text.into())), // Default name if only text provided
        _ => None,
    };

    let mut labels = Vec::new();
    if let Some(py_labels_list_any) = py_dict.get_item("labels_data")? {
        if let Ok(py_labels_list) = py_labels_list_any.downcast::<PyList>() {
            for py_label_dict_any in py_labels_list.iter() {
                if let Ok(py_label_dict) = py_label_dict_any.downcast::<PyDict>() {
                    let text: Option<String> = py_label_dict.get_item("text")?.map(|i|i.extract()).transpose()?;
                    let offset: Option<usize> = py_label_dict.get_item("offset")?.map(|i|i.extract()).transpose()?;
                    let length: Option<usize> = py_label_dict.get_item("length")?.map(|i|i.extract()).transpose()?;
                    if let (Some(txt), Some(off), Some(len)) = (text, offset, length) {
                        labels.push(LabeledSpan::new_with_span(Some(txt), SourceSpan::new(off.into(), len.into())));
                    }
                }
            }
        }
    }
    Ok((message, error_code, help_message, severity, diagnostic_source_code, labels))
}

// Recursive helper to convert PyDict to a full miette::Report
fn pydict_to_report(py_dict: &Bound<'_, PyDict>, py: Python<'_>) -> PyResult<Report> {
    let (message, error_code, help_message, severity, diagnostic_source_code, labels) =
        pydict_to_simple_error_fields(py_dict)?;

    let mut related_reports_vec = Vec::new();
    if let Some(py_children_list_any) = py_dict.get_item("children")? {
        if let Ok(py_children_list) = py_children_list_any.downcast::<PyList>() {
            for py_child_dict_any in py_children_list.iter() {
                if let Ok(py_child_dict) = py_child_dict_any.downcast::<PyDict>() {
                    related_reports_vec.push(pydict_to_report(py_child_dict, py)?);
                }
            }
        }
    }

    let err = SimpleError {
        message,
        error_code,
        help_message,
        severity,
        diagnostic_source_code,
        labels,
        related_reports: related_reports_vec,
    };
    Ok(Report::new(err))
}


#[derive(Error, Debug)]
#[error("{message}")]
struct SimpleError {
    message: String,
    error_code: Option<String>,
    help_message: Option<String>,
    severity: Option<Severity>,
    diagnostic_source_code: Option<NamedSource<String>>,
    labels: Vec<LabeledSpan>,
    related_reports: Vec<Report>, // Field for related diagnostics
}

impl Diagnostic for SimpleError {
    fn code<'a>(&'a self) -> Option<Box<dyn fmt::Display + 'a>> {
        self.error_code.as_ref().map(|s| Box::new(s) as Box<dyn fmt::Display + 'a>)
    }

    fn source_code(&self) -> Option<&dyn miette::SourceCode> {
        self.diagnostic_source_code.as_ref().map(|s| s as &dyn miette::SourceCode)
    }

    fn labels(&self) -> Option<Box<dyn Iterator<Item = LabeledSpan> + '_>> {
        if self.labels.is_empty() {
            None
        } else {
            Some(Box::new(self.labels.clone().into_iter()))
        }
    }

    fn help<'a>(&'a self) -> Option<Box<dyn fmt::Display + 'a>> {
        self.help_message.as_ref().map(|s| Box::new(s) as Box<dyn fmt::Display + 'a>)
    }

    fn severity(&self) -> Option<Severity> {
        self.severity
    }

    fn related<'a>(&'a self) -> Option<Box<dyn Iterator<Item = &'a dyn Diagnostic> + 'a>> {
        if self.related_reports.is_empty() {
            None
        } else {
            Some(Box::new(self.related_reports.iter().map(|report| report.as_ref() as &dyn Diagnostic)))
        }
    }
}
    
#[pyfunction]
fn render_miette_diagnostic_rust(py_diag_dict: &Bound<'_, PyDict>, py: Python<'_>) -> PyResult<String> {
    let report = pydict_to_report(py_diag_dict, py)?;
    
    let use_colors = py_diag_dict.get_item("use_colors_param")?
        .map_or(Ok(true), |item| item.extract::<bool>())?; // Default to true if not present

    let footer_opt: Option<String> = py_diag_dict.get_item("footer_param")?
        .map(|item| item.extract::<String>())
        .transpose()?;

    let context_lines_opt: Option<usize> = py_diag_dict.get_item("context_lines_param")?
        .map(|item| item.extract::<usize>())
        .transpose()?;

    let mut out_buf = String::new();
    
    let mut handler = if use_colors {
        GraphicalReportHandler::new_themed(GraphicalTheme::unicode())
    } else {
        GraphicalReportHandler::new_themed(GraphicalTheme::ascii())
    };

    if let Some(footer_string) = footer_opt {
        handler = handler.with_footer(footer_string);
    }

    if let Some(lines) = context_lines_opt {
        handler = handler.with_context_lines(lines);
    }

    handler.render_report(&mut out_buf, report.as_ref())
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to render report: {}", e)))?;
    Ok(out_buf)
}

#[pymodule]
fn miette_py(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(render_miette_diagnostic_rust, m)?)?;
    Ok(())
}
