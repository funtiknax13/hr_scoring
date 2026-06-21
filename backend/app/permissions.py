import enum

from app.models.user import Role


class Permission(str, enum.Enum):
    SCORING_RUN    = "scoring:run"
    SCORING_VIEW   = "scoring:view"
    VACANCY_FETCH  = "vacancy:fetch"
    VACANCY_VIEW   = "vacancy:view"


ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.admin: {
        Permission.SCORING_RUN,
        Permission.SCORING_VIEW,
        Permission.VACANCY_FETCH,
        Permission.VACANCY_VIEW,
    },
    Role.hr: {
        Permission.SCORING_RUN,
        Permission.SCORING_VIEW,
        Permission.VACANCY_FETCH,
        Permission.VACANCY_VIEW,
    },
    Role.analyst: {
        Permission.SCORING_VIEW,
        Permission.VACANCY_VIEW,
    },
}
