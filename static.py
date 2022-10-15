def valid_doc_datatype(
    document: dict,
    template: dict,
    strict=True) -> bool:
    """Checks document datatype validity i.e. the datatype of
    every value in `document` match the corresponding one at
    `template`.

    Args:
        document (`dict`): Document to validate.
        template (`dict`): Datatype template
        strict (`bool`, `optional`): `document` shall contain
        every key of `template`. Defaults to `True`.

    Returns:
        `bool`: Document validity.
    """

    def strict_validation():
        for field in template:
            try:
                if type(document[field]) is not template[field]:
                    return False
            except KeyError:
                return False

        return True

    def non_strict_validation():
        for field in template:
            try:
                if type(document[field]) is not template[field]:
                    return False
            except KeyError:
                pass

        return True

    return strict_validation() if strict else non_strict_validation()

def response(status_code: int, data = None) -> dict:
    """Generates void response.

    Args:
        status_code (`int`): Status code.

    Returns:
        `dict`: Response.
    """

    return {
        "status": status_code,
        "response": data
    }