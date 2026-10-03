"""LangChain tools (PRD §5: 11 tools). Each has a typed args schema so the model sees
clear argument names/descriptions. Tools that need dependencies are built by small
factories (closures) so nothing global or hidden is involved."""
