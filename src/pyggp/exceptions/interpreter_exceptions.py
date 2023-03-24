class InvalidGDLError(Exception):
    pass


class MoreThanOneModelError(InvalidGDLError):
    pass


class UnsatError(InvalidGDLError):
    pass


class UnsatRolesError(UnsatError):
    pass


class UnsatInitError(UnsatError):
    pass


class UnsatNextError(UnsatError):
    pass


class UnsatSeesError(UnsatError):
    pass


class UnsatLegalError(UnsatError):
    pass


class UnsatGoalError(UnsatError):
    pass


class UnexpectedRoleError(InvalidGDLError):
    pass


class MultipleGoalsError(InvalidGDLError):
    pass


class GoalNotIntegerError(InvalidGDLError):
    pass