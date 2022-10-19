def valid_doc_datatype(
    document: dict,
    template: dict,
    strict=True) -> bool:
    """Checks document datatype validity i.e. the datatype of
    every value in `document` match the corresponding one at
    `template`.

    Documents with keys not in `template` are never valid.

    Args:
        document (`dict`): Document to validate.
        template (`dict`): Datatype template
        strict (`bool`, `optional`): `document` shall contain
        every key of `template`. Defaults to `True`.

    Returns:
        `bool`: Document validity.
    """
        
    if strict and len(document.keys()) != len(template.keys()):
        return False

    for field in document:
        try:
            if type(document[field]) is not template[field]:
                return False
        except KeyError:
            return False

    return True

def response(status_code: int, data = None) -> dict:
    """Generates formatted response.

    Args:
        status_code (`int`): Status code.
        data (`Any`): Data. Defaults to `None`.
    Returns:
        `dict`: Response.
    """

    return {
        "status": status_code,
        "response": data
    }