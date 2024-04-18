class FastAPIResolveInfo:
    def __init__(self, context, field_name, parent_type):
        self.context = context
        self.field_name = field_name
        self.parent_type = parent_type

    def __repr__(self):
        return (
            f"FastAPIResolveInfo(context={self.context}, "
            f"field_name={self.field_name}, parent_type={self.parent_type})"
        )
