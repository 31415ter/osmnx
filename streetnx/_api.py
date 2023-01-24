"""Expose most common parts of public API directly in `osmnx.` namespace."""

from .graph_preparation import download_graph
from .graph_preparation import process_graph
from .graph_preparation import save_graph
from .graph_preparation import load_graph

from .penalties import add_penalties
