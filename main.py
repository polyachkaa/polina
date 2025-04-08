from PyQt6 import QtWidgets, QtGui, QtCore
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont
from PyQt6.QtWidgets import QLabel, QLineEdit, QPushButton, QMessageBox
import pymysql
import random
import string
from main1 import Ui_MainWindow
from second import Ui_Form


class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.failed_attempts = 0  # Счетчик неудачных попыток

    def connect(self):
        try:
            self.connection = pymysql.connect(
                host="localhost",
                user="root",
                password="",
                database="Kredits",
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            return True
        except pymysql.Error as e:
            print(f"Ошибка подключения к БД: {e}")
            return False

    def get_connection(self):
        if self.connection is None or not self.connection.open:
            self.connect()
        return self.connection

    def close(self):
        if self.connection and self.connection.open:
            self.connection.close()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, db_manager):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.db_manager = db_manager
        self.second_window = None
        self.login_blocked = False

        # Инициализация виджетов капчи
        self.captcha_label = QLabel(self)
        self.captcha_label.setGeometry(200, 230, 171, 50)
        self.captcha_label.hide()

        self.captcha_input = QLineEdit(self)
        self.captcha_input.setGeometry(200, 280, 171, 31)
        self.captcha_input.hide()

        self.submit_captcha_button = QPushButton("Отправить капчу", self)
        self.submit_captcha_button.setGeometry(380, 280, 100, 31)
        self.submit_captcha_button.hide()
        self.submit_captcha_button.clicked.connect(self.check_captcha)

        self.ui.pushButton.clicked.connect(self.check_credentials)
        self.captcha_text = ""

    def generate_captcha(self):
        """Генерация случайной капчи"""
        self.captcha_text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        captcha_pixmap = QPixmap(171, 50)
        captcha_pixmap.fill(QColor(255, 255, 255))
        painter = QPainter(captcha_pixmap)
        painter.setFont(QFont("Arial", 20))
        painter.setPen(QColor(0, 0, 0))

        for i, char in enumerate(self.captcha_text):
            painter.drawText(20 + i * 30 + random.randint(-5, 5), 35 + random.randint(-5, 5), char)
        painter.end()

        self.captcha_label.setPixmap(captcha_pixmap)
        self.captcha_label.show()
        self.captcha_input.show()
        self.submit_captcha_button.show()
        print(f"Сгенерирована капча: {self.captcha_text}")

    def check_captcha(self):
        """Проверка введённой капчи"""
        if self.captcha_input.text().upper() == self.captcha_text:
            print("Капча введена верно")
            self.captcha_label.hide()
            self.captcha_input.hide()
            self.submit_captcha_button.hide()
            self.captcha_input.clear()
            self.db_manager.failed_attempts = 0  # Сбрасываем неудачные попытки
        else:
            print("Капча введена неверно")
            QMessageBox.warning(self, "Ошибка", "Неверная капча!")
            self.generate_captcha()  # Генерируем новую капчу

    def unblock_login(self):
        """Разблокировка кнопки входа после таймаута"""
        self.login_blocked = False
        self.ui.pushButton.setEnabled(True)

    def check_credentials(self):
        if self.login_blocked:
            return

        login = self.ui.lineEdit.text().strip()
        password = self.ui.lineEdit_2.text().strip()

        if not login or not password:
            QMessageBox.warning(self, "Ошибка", "Введите логин и пароль")
            return

        try:
            conn = self.db_manager.get_connection()
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM Client WHERE login = %s AND password = %s",
                    (login, password))
                user = cursor.fetchone()

                if user:
                    self.db_manager.failed_attempts = 0
                    self.show_second_window()
                else:
                    self.db_manager.failed_attempts += 1
                    print(f"Неудачных попыток: {self.db_manager.failed_attempts}")
                    QMessageBox.warning(self, "Ошибка", "Неверный логин или пароль!")

                    if self.db_manager.failed_attempts >= 2:  # Показываем капчу после 2 неудачных попыток
                        print("Требуется капча, отображаем")
                        self.generate_captcha()
                    else:
                        self.login_blocked = True
                        self.ui.pushButton.setEnabled(False)
                        QtCore.QTimer.singleShot(10000, self.unblock_login)

        except pymysql.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка БД:\n{str(e)}")

    def show_second_window(self):
        if self.second_window is None:
            self.second_window = SecondWindow(self, self.db_manager)
            self.second_window.destroyed.connect(lambda: setattr(self, 'second_window', None))

        self.second_window.show()
        self.hide()


class SecondWindow(QtWidgets.QMainWindow):
    def __init__(self, main_window, db_manager):
        super().__init__()
        self.main_window = main_window
        self.db_manager = db_manager
        self.ui = Ui_Form()
        self.ui.setupUi(self)

        # Настройка таблицы
        self.tableView = self.ui.tableView
        self.tableView.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableView.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)

        if hasattr(self.ui, 'loadButton'):
            self.ui.loadButton.clicked.connect(self.load_data)

        if hasattr(self.ui, 'backButton'):
            self.ui.backButton.clicked.connect(self.go_back)

    def go_back(self):
        self.main_window.show()
        self.close()

    def load_data(self):
        try:
            conn = self.db_manager.get_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT name, lastname FROM Client")
                data = cursor.fetchall()

                model = QtGui.QStandardItemModel()
                if data:
                    model.setHorizontalHeaderLabels(["Имя", "Фамилия"])
                    for row in data:
                        model.appendRow([
                            QtGui.QStandardItem(row['name']),
                            QtGui.QStandardItem(row['lastname'])
                        ])

                self.tableView.setModel(model)
                self.tableView.resizeColumnsToContents()
                self.statusBar().showMessage(f"Загружено {len(data)} записей", 3000)

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки данных:\n{str(e)}")


if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    # Создаем менеджер БД для всего приложения
    db_manager = DatabaseManager()
    if not db_manager.connect():
        QtWidgets.QMessageBox.critical(None, "Ошибка", "Не удалось подключиться к БД")
        exit(1)

    main_window = MainWindow(db_manager)
    main_window.show()

    ret = app.exec()
    db_manager.close()
    exit(ret)



'''
class DataBaseManager:
    def __init__(self):
        self.connection = None

    def connect(self):
        try:
            self.connection = pymysql.connect(
                host = 'localhost',
                user = 'root',
                password = '',
                database = 'Kredit',
                charset='utf8mb4',
                cursorclass = pymysql.cursors.DictCursor
            )
            return True
        except pymysql.Error as e:
            print(f'fail with database {e}')
            return False

    def get_connection(self):
        if self.connection is None or not self.connection.open:
            self.connection()
            return self.connection

    def connection_close(self):
        if self.connection or self.connection.open:
            self.connection.close()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, db_manager):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.db_manager = db_manager

        self.second_window = None
        
        self.captcha_group = QtWidgets.QGroupBox("Put captcha")
        self.captcha_label = QtWidgets.QLabel()
        self.captcha_input = QtWidgets.QLineEdit()
        self.captcha_button = QtWidgets.QPushButton("Check")

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.captcha_label)
        layout.addWidget(self.captcha_input)
        layout.addWidget(self.captcha_button)
        
        self.captcha_group.setLayout(layout)
        self.captcha_group.hide()
        
        self.ui.verticalLayout.addWidget(self.captcha_group)
        self.current_captcha = ""
        
        
        self.ui.pushButton.clicked(self.check_pass)
        self.ui.pushButton.clicked(self.check_captcha)

    def check_pass(self):
        login = self.ui.lineEdit.text().strip()
        password = self.ui.lineEdit_2.text().strip()

        if not login or not password:
            QtWidgets.QMessageBox.warning(self, "fail. put your data")
            return
    try:
        conn = self.db_manager.get_connection()
        with conn.cursor() as cursor
            cursor.execute(
                "SELECT * from Client where login = %s AND password = %s", (login, password))
            user = cursor.fetchone()
    except.QMe
'''