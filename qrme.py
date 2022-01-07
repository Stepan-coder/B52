import os
import qrcode


def create_qrcode(data: str, path_to_folder: str, filename: str) -> str:
    """
    Этот метод создаёт изображение с qr-кодом
    :param data: Строка-информация, которую необходимо преобразовать в qr-код
    :param path_to_folder: Путь до
    :return: None
    """
    if not filename.endswith(".png") and not filename.endswith(".jpeg") and not filename.endswith(".svg"):
        raise Exception("Unsupported file format!")
    if not os.path.exists(path_to_folder):
        raise Exception("The specified path was not found!")
    img = qrcode.make(data)
    img.save(os.path.join(path_to_folder, filename))
    return os.path.join(path_to_folder, filename)

