Models
======

Models provide a convenient object representation for rows in the database, as well as a 
convenient way to access related objects by Foreign Keys. Most models will subclass one 
or more mixins, which provide convenient abstractions for commonly used methods. However, 
compared to classic SQLAlchemy models, pulsar's may be larger and require more manual 
code. In order to take advantage of caching at a model level, we do not define 
``relationship``'s, instead opting to create properties which return other models with 
their methods which support caching. Caching is handled by the mixins subclassed by 
models. I recommend viewing the mixins page to view vital methods which belong to 
subclassing models.

Users
-----

.. automodule:: pulsar.users.models
    :members:
    :show-inheritance:

Permissions
-----------

.. automodule:: pulsar.permissions.models
    :members:
    :show-inheritance:

Forums
------

.. automodule:: pulsar.forums.models
    :members:
    :show-inheritance:
