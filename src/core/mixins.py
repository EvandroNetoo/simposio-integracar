class NoRequiredAttrFormMixin:
    """Remove o atributo HTML5 'required' de todos os campos do formulário."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('use_required_attribute', False)
        super().__init__(*args, **kwargs)
