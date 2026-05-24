class AnyFilter:
    """
    Простой фильтр, который пропускает абсолютно все сообщения.
    """
    def __call__(self, client, message) -> bool:
        return True
