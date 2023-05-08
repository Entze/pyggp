class NodeError(Exception):
    """Base class for all exceptions regarding nodes."""


class ValuationIsNoneNodeError(NodeError):
    """Accessed valuation when it was None."""


class InformationSetNodeError(NodeError):
    """Base class for all exceptions regarding information set nodes."""


class RoleIsNoneInformationSetNodeError(InformationSetNodeError):
    """Accessed role when it was None."""
