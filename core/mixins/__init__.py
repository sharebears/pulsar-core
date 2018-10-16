from enum import Enum
from itertools import chain
from typing import List

from .class_ import ClassMixin  # noqa: F401
from .multi_pk import MultiPKMixin  # noqa: F401
from .serializer import Attribute, Serializer  # noqa: F401
from .single_pk import SinglePKMixin  # noqa: F401


class Permission(Enum):
    """This class is used to track the permission subclasses."""

    @staticmethod
    def get_all_permissions() -> List[str]:
        """
        Aggregate all the permissions in permission enum subclasses. Restrict all
        uses of this function to users with the `get_all_permissions` permission.
        Returns the list of aggregated permissions

        :return: The list of permissions
        """
        return list(chain([e.value for c in Permission.__subclasses__() for e in c]))
