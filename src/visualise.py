"""Visualise HUGR using graphviz."""

import graphviz as gv
from typing import Iterable

from src.hugr import *


# old palettte: https://colorhunt.co/palette/343a407952b3ffc107e1e8eb
# _COLOURS = {
#     "background": "white",
#     "node": "#7952B3",
#     "edge": "#FFC107",
#     "dark": "#343A40",
#     "const": "#7c55b4",
#     "discard": "#ff8888",
#     "node_border": "#9d80c7",
#     "port_border": "#ffd966",
# }

# ZX colours
# _COLOURS = {
#     "background": "white",
#     "node": "#629DD1",
#     "edge": "#297FD5",
#     "dark": "#112D4E",
#     "const": "#a1eea1",
#     "discard": "#ff8888",
#     "node_border": "#D8F8D8",
#     "port_border": "#E8A5A5",
# }

# Conference talk colours
_COLOURS = {
    "background": "white",
    "node": "#ACCBF9",
    "edge": "#1CADE4",
    "dark": "black",
    "const": "#77CEEF",
    "discard": "#ff8888",
    "node_border": "white",
    "port_border": "#1CADE4",
}


_FONTFACE = "monospace"

_HTML_LABEL_TEMPLATE = """
<TABLE BORDER="{border_width}" CELLBORDER="0" CELLSPACING="1" CELLPADDING="1" BGCOLOR="{node_back_color}" COLOR="{border_colour}">
{inputs_row}
    <TR>
        <TD>
            <TABLE BORDER="0" CELLBORDER="0">
                <TR>
                    <TD><FONT POINT-SIZE="{fontsize}" FACE="{fontface}" COLOR="{label_color}"><B>{node_label}</B>{node_data}</FONT></TD>
                </TR>
            </TABLE>
        </TD>
    </TR>
{outputs_row}
</TABLE>
"""


def _format_html_label(**kwargs):
    _HTML_LABEL_DEFAULTS = {
        "label_color": _COLOURS["dark"],
        "node_back_color": _COLOURS["node"],
        "inputs_row": "",
        "outputs_row": "",
        "border_colour": _COLOURS["port_border"],
        "border_width": "1",
        "fontface": _FONTFACE,
        "fontsize": 11.0,
    }
    return _HTML_LABEL_TEMPLATE.format(**{**_HTML_LABEL_DEFAULTS, **kwargs})


_HTML_PORTS_ROW_TEMPLATE = """
    <TR>
        <TD>
            <TABLE BORDER="0" CELLBORDER="0" CELLSPACING="3" CELLPADDING="2">
                <TR>
                    {port_cells}
                </TR>
            </TABLE>
        </TD>
    </TR>
"""

_HTML_PORT_TEMPLATE = (
    '<TD BGCOLOR="{back_colour}" COLOR="{border_colour}"'
    ' PORT="{port_id}" BORDER="{border_width}">'
    '<FONT POINT-SIZE="10.0" FACE="{fontface}" COLOR="{font_colour}">{port}</FONT></TD>'
)

_INPUT_PREFIX = "in."
_OUTPUT_PREFIX = "out."


def _html_ports(ports: Iterable[str], id_prefix: str) -> str:
    return _HTML_PORTS_ROW_TEMPLATE.format(
        port_cells="".join(
            _HTML_PORT_TEMPLATE.format(
                port=port,
                # differentiate input and output node identifiers
                # with a prefix
                port_id=id_prefix + port,
                back_colour=_COLOURS["background"],
                font_colour=_COLOURS["dark"],
                border_width="1",
                border_colour=_COLOURS["port_border"],
                fontface=_FONTFACE,
            )
            for port in ports
        )
    )


def _in_port_name(p: InPort):
    return f"{p.node_idx}:{_INPUT_PREFIX}{p.offset}"


def _out_port_name(p: OutPort):
    return f"{p.node_idx}:{_OUTPUT_PREFIX}{p.offset}"


def viz_node(node: Node, hugr: Hugr, graph: gv.Digraph):
    in_ports = [str(i) for i in range(node.num_in_ports)]
    out_ports = [str(i) for i in range(node.num_out_ports)]
    if len(node.meta_data) > 0:
        data = "<BR/><BR/>" + "<BR/>".join(f"{key}: {value}" for key, value in node.meta_data.items())
    else:
        data = ""
    if len(hugr.children(node)) > 0:
        with graph.subgraph(name=f"cluster{node.idx}") as sub:
            for child in hugr.children(node):
                viz_node(child, hugr, sub)
            html_label = _format_html_label(
                node_back_color=_COLOURS["edge"],
                node_label=node.name,
                node_data=data,
                border_colour=_COLOURS["port_border"],
                inputs_row=_html_ports(in_ports, _INPUT_PREFIX) if len(in_ports) > 0 else "",
                outputs_row=_html_ports(out_ports, _OUTPUT_PREFIX) if len(out_ports) > 0 else "",
            )
            sub.node(f"{node.idx}", shape="plain", label=f"<{html_label}>")
            sub.attr(label="", margin="10", color=_COLOURS["edge"])
    else:
        html_label = _format_html_label(
            node_back_color=_COLOURS["node"],
            node_label=node.name,
            node_data=data,
            inputs_row=_html_ports(in_ports, _INPUT_PREFIX) if len(in_ports) > 0 else "",
            outputs_row=_html_ports(out_ports, _OUTPUT_PREFIX) if len(out_ports) > 0 else "",
            border_colour=_COLOURS["background"]
        )
        graph.node(f"{node.idx}", label=f"<{html_label}>", shape="plain")


def hugr_to_graphviz(hugr: Hugr) -> gv.Digraph:
    graph_atrr = {
        "rankdir": "",
        "ranksep": "0.1",
        "nodesep": "0.15",
        "margin": "0",
        "bgcolor": _COLOURS["background"],
    }
    graph = gv.Digraph(hugr.name, strict=False)
    graph.attr(**graph_atrr)
    for node in hugr.top_level_nodes():
        viz_node(node, hugr, graph)
    edge_attr = {
        "penwidth": "1.5",
        "arrowhead": "none",
        "arrowsize": "1.0",
        "fontname": _FONTFACE,
        "fontsize": "9",
        "fontcolor": "black",
    }
    for edge in hugr.edges():
        graph.edge(_out_port_name(edge.src_port), _in_port_name(edge.target_port),
                   label=str(edge.type) if edge.type else "",
                   color=_COLOURS["edge"] if edge.kind == EKind.Value else _COLOURS["dark"],
                   **edge_attr)
    return graph


def render_hugr(hugr: Hugr, filename: str, format_st: str = "svg") -> None:
    gv_graph = hugr_to_graphviz(hugr)
    gv_graph.render(filename, format=format_st)
