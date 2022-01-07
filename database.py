import os
import enum
import sqlite3
import threading
from typing import List, Dict, Any


class DBType(enum.Enum):
    """
    Enum, для хранения возможных типов полей таблиц
    """
    NULL = "NULL"  # Значение Null
    INTEGER = "INTEGER"  # Целое число
    REAL = "REAL"  # Число с плавающей точкой
    TEXT = "TEXT"  # Текст
    BLOB = "BLOB"  # Бинарное представление крупных объектов, хранящееся в точности с тем, как его ввели


class Table:
    def __init__(self, name: str, cursor: sqlite3.Cursor, connector: sqlite3.Connection):
        self.__name = name
        self.__cursor = cursor
        self.__connector = connector
        self.__primary_key = None
        self.__table_labels = None
        self.__is_loaded = False

    def __nonzero__(self) -> bool:
        return self.__is_loaded

    def create_table(self, labels: Dict[str, DBType], primary_key: str = None) -> None:
        """
        Этот метод создаёт таблицу с заданными колонками. Если primary_key не задан, то идентификатором будет считаться
        первая колонка, в противном случае - выбранная пользователем.
        :param labels: Словарь, где ключом является название колонки, а значение - тип данных
        :param primary_key: Колонка, которая будет считаться у пользователя основной
        :return: None
        """
        if self.__is_loaded:
            raise Exception("DataBase is already exist!")
        if primary_key is not None:
            if primary_key not in labels:
                raise Exception(f"Column \'{primary_key}\' not exist in table labels!")
            self.__primary_key = primary_key
        else:
            self.__primary_key = list(labels.keys())[0]
        self.__cursor.execute(f"CREATE TABLE IF NOT EXISTS {self.__name} ({Table.__prep_labels(labels)})")
        self.__connector.commit()
        self.__table_labels = labels
        self.__is_loaded = True


    def get_column_names(self) -> List[str]:
        """
        Этот метод возвращает список, названий колонок
        :return: List[str]
        """
        if not self.__is_loaded:
            raise Exception(f"DataBase \'{self.__name}\' is not exist!. Try using \'Table.create_table\'.")
        return list(self.__table_labels.keys())

    def get_from_cell(self, key: str, column_name: str):
        """
        Этот метод достаёт значение по ключу key (уникальное поля для пользователя) и колонке column_name
        :param key: Идентификатор пользователя
        :param column_name: Название колонки
        :return:
        """
        if not self.__is_loaded:
            raise Exception(f"DataBase \'{self.__name}\' is not exist!. Try using \'Table.create_table\'.")
        if column_name not in self.__table_labels:
            raise Exception(f"Column \'{column_name}\' not exist in table labels!")
        self.__cursor.execute(f"SELECT {column_name} FROM {self.__name} WHERE {self.__primary_key} = '{key}'")
        return self.__cursor.fetchone()[0]

    def set_to_cell(self, key: str, column_name: str, new_value: Any, commit: bool = True) -> None:
        """
        Этот метод записывает значение new_value в колонку column_name в строку с идентификатором key
        :param key: Идентификатор пользователя
        :param column_name: Название колонки
        :param new_value: Значение, которое хотим записать
        :param commit: Нужно ли сохранение
        :return:
        """
        if not self.__is_loaded:
            raise Exception(f"DataBase \'{self.__name}\' is not exist!. Try using \'Table.create_table\'.")
        if column_name not in self.__table_labels:
            raise Exception(f"Column \'{column_name}\' not exist in table labels!")
        self.__cursor.execute(f"UPDATE {self.__name} SET {column_name} = '{new_value}' WHERE {self.__primary_key} = '{key}'")
        if commit:
            self.__connector.commit()

    def add_row(self, row: list, commit: bool = True) -> None:
        """
        Этот метод добавляет в базу данных новую строку
        :param row: Список значений строки
        :param commit: Стоит ли коммитить (зачастую коммит нужен 1 раз в 10-100 операций)
        :return: None
        """
        if not self.__is_loaded:
            raise Exception(f"DataBase \'{self.__name}\' is not exist!. Try using \'Table.create_table\'.")
        if len(row) != len(self.__table_labels):
            raise Exception(f"There are only {len(self.__table_labels)} columns in the database "
                            f"\'{self.__name}\', and you are trying to write {len(row)}")
        values = ", ".join(["'" + str(i) + "'" for i in row])
        self.__cursor.execute(f"INSERT INTO {self.__name} VALUES ({values})")
        if commit:
            self.__connector.commit()

    def get_row(self, key: str) -> Dict[str, Any]:
        """
        Это метод получает значение "строки" из таблицы
        :param key: Идентификатор пользователя
        :return: tuple
        """
        if not self.__is_loaded:
            raise Exception(f"DataBase \'{self.__name}\' is not exist!. Try using \'Table.create_table\'.")
        self.__cursor.execute(f"SELECT * FROM {self.__name} WHERE {self.__primary_key} = '{key}'")
        request = self.__cursor.fetchall()
        if len(request) == 0:
            raise Exception("There are no values for this query!")
        if len(request[0]) != len(self.get_column_names()):
            raise Exception("The number of columns and values does not match!"
                            f"{len(self.get_column_names())} columns and {len(request[0])} values were detected!")
        return {column: value for column, value in zip(self.get_column_names(), request[0])}

    def delete_row(self, key: str) -> None:
        """
        Этот метод удаляет "строку" из таблицы
        :param key: Идентификатор пользователя
        :return: None
        """
        if not self.__is_loaded:
            raise Exception(f"DataBase \'{self.__name}\' is not exist!. Try using \'Table.create_table\'.")
        self.__cursor.execute(f"DELETE FROM {self.__name} WHERE {self.__primary_key} = '{key}'")
        self.__connector.commit()

    def get_column(self, column_name: str) -> List[Any]:
        """
        Этот метод остаёт значения по колонке со всей таблице
        :param column_name: Название колонки
        :return: Список значений в колонке
        """
        if not self.__is_loaded:
            raise Exception(f"DataBase \'{self.__name}\' is not exist!. Try using \'Table.create_table\'.")
        if column_name not in self.__table_labels:
            raise Exception(f"Column \'{column_name}\' not exist in table labels!")
        self.__cursor.execute(f"SELECT {column_name} FROM {self.__name}")
        return [sfa[0] for sfa in self.__cursor.fetchall()]

    def get_all_UIDs(self) -> List[Any]:
        """
        Этот метод возвращяет все значения индексаторов (столбец, который является уникальным, для каждого пользователя)
        :return: Список этих самых идентификаторов
        """
        if not self.__is_loaded:
            raise Exception(f"DataBase \'{self.__name}\' is not exist!. Try using \'Table.create_table\'.")
        self.__cursor.execute(f"SELECT {self.__primary_key} FROM {self.__name}")
        return [sfa[0] for sfa in self.__cursor.fetchall()]

    def commit(self) -> None:
        """
        Подтверждает запись в базу
        :return: None
        """
        self.__connector.commit()

    @staticmethod
    def __prep_labels(labels: Dict[str, DBType]) -> str:
        """
        Этот метод преобразует пользовательский словарь с колонками и их типами в пригодную для SQL часть команды
        :param labels: Словарь, где ключ это название колонки, а значения - тип данных из множества DBType
        :return: Готовую часть строки
        """
        return ",".join([f"{label} {labels[label].value}" for label in labels])


class DataBase:
    def __init__(self, path: str, filename: str):
        """
        Этот метод инициализирует основной класс для работы (и управления) базой данных
        :param path: Путь, по которому располоежна (необходимо расположить базу данных)
        :param filename: Имя базы данных (вместе с расширением). Например: 'some.bd'
        """
        self.__tables = {}
        self.__path = DataBase.__is_path_valid(path=path)
        self.__filename = DataBase.__is_filename_valid(filename=filename)
        self.__create_cursor(path_to_file=os.path.join(self.__path, self.__filename))

    def __len__(self):
        return len(self.__tables)

    def create_table(self, name: str, labels: Dict[str, DBType], primary_key: str = None) -> None:
        """
        Этот метод создаёт таблицу в базе данных
        :param name: Название таблицы
        :param labels: Словарь, где ключом является название колонки, а значение - тип данных
        :param primary_key: Ключевой столбец
        :return: None
        """
        table = Table(name=name,
                      cursor=self.__cursor,
                      connector=self.__connector)
        table.create_table(labels=labels, primary_key=primary_key)
        self.__tables[name] = table

    def get_table(self, table_name: str) -> Table:
        """
        Получаем объект Table, для дальнейшего взаимодействия с ним.
        :param table_name: Название таблицы
        :return: Таблицу класса 'Table'
        """
        if table_name not in self.__tables:
            raise Exception(f"Table \'{table_name}\' not exist in DataBase!")
        return self.__tables[table_name]

    def get_cursor(self) -> sqlite3.Cursor:
        """
        Этот метод возвращает курсор для базы данных (непосредственна та штука, которая работает с ячейками БД)
        :return:
        """
        return self.__cursor

    def get_connector(self) -> sqlite3.Connection:
        """
        Этот метод возвращает коннектор для базы данных (Штука, через которую устанавливается соединение с БД)
        :return:
        """
        return self.__connector

    def __create_cursor(self, path_to_file: str) -> None:
        """
        Этот метод создаёт курсор (сущность, для взаимодействия с бд)
        :param path_to_file: Путь до базы данных, прямо вместе с файлом. Например: *\some.db
        :return: None
        """
        self.__connector = sqlite3.connect(path_to_file, check_same_thread=False)
        self.__cursor = self.__connector.cursor()

    @staticmethod
    def __is_path_valid(path: str) -> str:
        """
        Этот метод проверяет, является ли эта строка путём к папке/файлу
        :param path: Предполагаемый путь к файлу
        :return:
        """
        if os.path.exists(path):
            return path
        else:
            raise Exception(f"The path \'{path}\' is not valid!")

    @staticmethod
    def __is_filename_valid(filename: str) -> str:
        """
        Этот метод проверяет, является ли эта строка путём к папке/файлу
        :param filename: Предполагаемый путь к файлу
        :return: str
        """
        if filename.endswith(".db"):
            return filename
        else:
            raise Exception(f"The filename \'{filename}\' is not valid!")