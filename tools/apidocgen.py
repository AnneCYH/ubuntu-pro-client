"""
Generate RST documentation for an ubuntu-pro-client api endpoint.

Usage: env PYTHONPATH=. python3 tools/apidocgen.py $ENDPOINT_NAME
"""

import sys
import textwrap
from importlib import import_module

from uaclient import data_types
from uaclient.exceptions import UbuntuProError

NO_ARGS = "- This endpoint takes no arguments."


def data_value_type_to_str(data_value_cls):
    if data_value_cls.__name__ == "_DataList":
        return "List[{}]".format(
            data_value_type_to_str(data_value_cls.item_cls)
        )
    if issubclass(data_value_cls, data_types.DataObject):
        return data_value_cls.__name__
    return data_value_cls.python_type_name


def create_fields_table(cls):
    table_template = """\
.. list-table::
    :header-rows: 1

    * - Field Name
      - Type
      - Description
{fields}"""
    field_definition_template = """\
* - ``{name}``
  - ``{type}``
  - {description}"""

    fields = []
    for field in cls.fields:
        type_str = data_value_type_to_str(field.data_cls)
        if not field.required:
            type_str = "Optional[{}]".format(type_str)
        fields.append(
            textwrap.indent(
                field_definition_template.format(
                    name=field.key, type=type_str, description=field.doc or ""
                ).strip(),
                prefix="    ",
            )
        )
    return table_template.format(
        fields="\n".join(fields),
    ).strip()


def collect_data_object_classes(target_cls, collection):
    for field in target_cls.fields:
        cls = field.data_cls
        if cls.__name__ == "_DataList":
            cls = cls.item_cls
        if issubclass(cls, data_types.DataObject) and cls not in collection:
            collection.append(cls)
            collect_data_object_classes(cls, collection)


endpoint_name = sys.argv[1]

module = import_module("uaclient.api." + endpoint_name)


if module.endpoint.options_cls is None:
    args_section = NO_ARGS
else:
    args_section = create_fields_table(module.endpoint.options_cls)

result_class = module._doc.get("result_cls")
result_classes = [result_class]
collect_data_object_classes(result_class, result_classes)
class_definition_template = """
- ``{module}.{name}``

  {fields_table}
"""
result_class_definitions = []
for cls in result_classes:
    result_class_definitions.append(
        class_definition_template.format(
            module=cls.__module__,
            name=cls.__qualname__,
            fields_table=create_fields_table(cls),
        ).strip()
    )
result_class_definitions_str = textwrap.indent(
    "\n\n".join(result_class_definitions), prefix="        "
).strip()

possible_exceptions = [
    (
        UbuntuProError,
        (
            "``UbuntuProError`` is the base class of all exceptions raised by"
            " Ubuntu Pro Client and it is best practice to handle this error"
            " on any API call. (Note: if any API call raises an exception that"
            " does not inherit from ``UbuntuProError``, please report a bug)."
        ),
    )
] + module._doc.get("exceptions", [])
exception_str_list = []
for err_cls, msg in possible_exceptions:
    exception_str_list.append(
        "- ``{name}``: {msg}".format(name=err_cls.__name__, msg=msg)
    )
exceptions_str = textwrap.indent(
    "\n".join(exception_str_list), prefix="        "
).strip()


data = {
    "name": endpoint_name,
    "underline": "=" * len(endpoint_name),
    "description": textwrap.dedent(module.endpoint.fn.__doc__).strip(),
    "introduced_in": module._doc.get("introduced_in"),
    "args_section": args_section,
    "example_python": textwrap.indent(
        module._doc.get("example_python").strip(), prefix="    " * 3
    ).strip(),
    "result_classes": result_class_definitions_str,
    "exceptions": exceptions_str,
    "example_cli": module._doc.get("example_cli").strip(),
    "example_json": textwrap.indent(
        module._doc.get("example_json").strip(), prefix="    " * 3
    ).strip(),
}

template = """\
{name}
{underline}

{description}

- Introduced in Ubuntu Pro Client Version: ``{introduced_in}~``
- Args:

  {args_section}

.. tab-set::

   .. tab-item:: Python API interaction
      :sync: python

      - Calling from Python code:

        .. code-block:: python

            {example_python}

      - Expected return object:

        {result_classes}

      - Raised exceptions:

        {exceptions}

   .. tab-item:: CLI interaction
      :sync: CLI

      - Calling from the CLI:

        .. code-block:: bash

           {example_cli}

      - Expected attributes in JSON structure:

        .. code-block:: js

            {example_json}
"""

print(template.format(**data))
