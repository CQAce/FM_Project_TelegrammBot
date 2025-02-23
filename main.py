import telebot # библиотека для управления телеграмм ботом
from telebot import types # библиотека для добавления кнопок
bot = telebot.TeleBot('7733019791:AAFZYEnlOx3XoPRzCWocdsiAJ1pRprwzl18') # Токен телеграмм бота

import pytesseract # импортируем библиотеку для распознавания текста на картинке/фото
from PIL import Image
import io
# https://github.com/tesseract-ocr/tesseract/releases/download/5.5.0/tesseract-ocr-w64-setup-5.5.0.20241111.exe - скачать Teseract для Window 64-bit
# https://digi.bib.uni-mannheim.de/tesseract/ - скачать Teseract для Window 32-bit
pytesseract.pytesseract.tesseract_cmd = r'd:/Programs/tesseract.exe' # указываем путь к установленной программе Tesseract

# Библиотека для распознания ШК
from pyzbar.pyzbar import decode

import gspread
from oauth2client.service_account import ServiceAccountCredentials

import re # Этот модуль обеспечивает операции сопоставления регулярных выражений
patternEAN = r'^\d{1,14}$' # Шаблон для ввода EAN. Не более 14-ти символов
patternCell = r'^[A-Z]\d{3} \d{4} \d{2}$'  # Шаблон, который должен соответствовать введенному сообщению. Пример: A502 2010 30

# ================================================================== БЛОК-1: Выбор типа ошибки ================================================================================================
# Создаём словарь для хранения данных
error_data = {
    'errorType': None,
    'fixEAN': None,
    'fixCell': None,
    'userName': None
}
current_step = None

@bot.message_handler(['start'])
def start(message):
    error_data['userName'] = message.from_user.first_name
    print(error_data['userName'])
    markup = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width=1) # метод создания кнопок
    errorBtn = [
        types.KeyboardButton('Габариты товара не соответствуют ячейки'),
        types.KeyboardButton('Неверное место размещения'),
        types.KeyboardButton('Номер ячейки нарушает порядок'),
        types.KeyboardButton('Размещён группаж')
    ]
    markup.add(*errorBtn) # добавление кнопок
    bot.send_message(message.chat.id, 'Выберите тип ошибки.', reply_markup=markup) # комментарий, после нажатия Start
    bot.register_next_step_handler(message, showButtomEan) # создаём отклик, который вызывает функцию showButtom 


# ================================================================== БЛОК-2: Фиксация EAN ==================================================================================================
def showButtomEan(message):
    if message.text != '/start':
        # записываем тип ошибки в словарь
        error_data['errorType'] = message.text.strip()
        print(error_data['errorType'])
        markup = types.ReplyKeyboardMarkup(row_width = 2, resize_keyboard=True)
        buttons = [
            types.KeyboardButton('Использовать камеру 📷'),
            types.KeyboardButton('Зафиксировать вручную ✏️'),
            types.KeyboardButton('Вернуться назад 🔙')
        ]
        markup.add(*buttons) # добавление кнопок
        bot.send_message(message.chat.id, "Зафиксируйте EAN товара, используя один из двух вариантов:", reply_markup=markup)
        bot.register_next_step_handler(message, fixitEAN) # создаём отклик, который вызывает функцию fixitError
    else:
        start(message)


# Фиксация EAN-кода
def fixitEAN(message):
    if message.text == 'Использовать камеру 📷':
        global current_step
        current_step = 'fixEAN'  # Устанавливаем текущий шаг
        bot.send_message(message.chat.id, "Сфотографируйте EAN товара и пришлите фото")
    elif message.text == 'Зафиксировать вручную ✏️':
        current_step = 'fixEAN'  # Устанавливаем текущий шаг
        bot.send_message(message.chat.id, "Введите штрих-код товара")
    elif message.text == 'Вернуться назад 🔙':
        start(message)


# Слушатель--> Фото
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    global error_data, current_step
# Проверяем, на каком шаге мы находимся
    if current_step == 'fixEAN':
        process_fixEAN_photo(message)
    elif current_step == 'fixCell':
        process_fixCell_photo(message)

# Слушатель--> Текст
@bot.message_handler(func=lambda massage:True)
def handle_text(message):
    global error_data, current_step
# Проверяем, на каком шаге мы находимся
    if current_step == 'fixEAN':
        process_fixEAN_text(message)
    elif current_step == 'fixCell':
        process_fixCell_text(message)


#Процесс обработки фото с EAN-кодом
def process_fixEAN_photo(message):
    global error_data
    file_info = bot.get_file(message.photo[-1].file_id)  # получаем фото
    photo_path = bot.download_file(file_info.file_path)  # сохраняем фото
    # Используем pytesseract для распознавания текста
    image = Image.open(io.BytesIO(photo_path))
    decoded_objects = decode(image)
    if decoded_objects:  # если фото видит ШК, то преобразует его в текст и записывает в словарь
        barcode_data = decoded_objects[0].data.decode('utf-8')
        error_data['fixEAN'] = barcode_data.strip()
    else:  # если фото не видит ШК, то преобразует надпись на фото и записывает в словарь
        recognized_text = pytesseract.image_to_string(image, lang='eng+rus')
        error_data['fixEAN'] = recognized_text.strip()
    print(error_data['fixEAN'])
    bot.send_message(message.chat.id, "Фото загружено!")
    showButtomCell(message)  # создаём отклик, который вызывает функцию btnFixСell

#Процесс обработки EAN-кода
def process_fixEAN_text(message):
    if re.match(patternEAN, message.text): # условие проверяет формат вводимых данных
        # записываем место ошибки в словарь
        error_data['fixEAN'] = message.text.strip()
        print(error_data['fixEAN'])
        bot.send_message(message.chat.id, "EAN записан!")
        showButtomCell(message) # создаём отклик, который вызывает функцию btnFixСell
    elif message.text == 'Вернуться назад 🔙':
        start(message)
    else:
        bot.send_message(message.chat.id, "Ошибка! Неверный формат записи! Попробуйте снова.")    


# ================================================================== БЛОК-3: Фиксация ячейки ==================================================================================================
def showButtomCell(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width = 2)
    buttons = [
        types.KeyboardButton('Использовать камеру 📷'),
        types.KeyboardButton('Зафиксировать вручную ✏️'),
        types.KeyboardButton('Вернуться назад 🔙')
    ]
    markup.add(*buttons) # добавление кнопок
    bot.send_message(message.chat.id, "Теперь зафиксируйте место ошибки", reply_markup=markup)
    bot.register_next_step_handler(message, fixitCell) # создаём отклик, который вызывает функцию fixitCell


# Фиксация ячейки
def fixitCell(message):
    if message.text == 'Использовать камеру 📷':
        global current_step
        current_step = 'fixCell' # Устанавливаем текущий шаг
        bot.send_message(message.chat.id, "Сфотографируйте ячейку товара и пришлите фото")
    elif message.text == 'Зафиксировать вручную ✏️':
        current_step = 'fixCell'  # Устанавливаем текущий шаг
        bot.send_message(message.chat.id, "Введите номер ячейки в формате: A123 4567 89")
    elif message.text == 'Вернуться назад 🔙': 
        start(message) # создаём отклик, который вызывает функцию start (возвращает пользователя в начало)


#Процесс обработки фото с номером ячейки
def process_fixCell_photo(message):
    global error_data
    file_info = bot.get_file(message.photo[-1].file_id)  # получаем фото
    photo_path = bot.download_file(file_info.file_path)  # сохраняем фото
    # Используем pytesseract для распознавания текста
    image = Image.open(io.BytesIO(photo_path))
    decoded_objects = decode(image)
    if decoded_objects:  # если фото видит ШК, то преобразует его в текст и записывает в словарь
        barcode_data = decoded_objects[0].data.decode('utf-8')
        error_data['fixCell'] = barcode_data.strip()
    else:  # если фото не видит ШК, то преобразует надпись на фото и записывает в словарь
        recognized_text = pytesseract.image_to_string(image, lang='eng+rus')
        error_data['fixCell'] = recognized_text.strip()
    print(error_data['fixCell'])
    bot.send_message(message.chat.id, "Фото загружено!")
    ControlCheck(message)  # создаём отклик, который вызывает функцию btnFixСell

#Процесс обработки формата номера ячейки
def process_fixCell_text(message):
    global error_data
    if re.match(patternCell, message.text): # условие проверяет формат вводимых данных
        # записываем место ошибки в словарь
        error_data['fixCell'] = message.text.strip()
        print(error_data['fixCell'])
        bot.send_message(message.chat.id, "Место зафиксировано!")
        ControlCheck(message) # создаём отклик, который вызывает функцию ControlCheck
    elif message.text == 'Вернуться назад 🔙':
        start(message)
    else:
        bot.send_message(message.chat.id, "Ошибка! Неверный формат записи! Попробуйте снова.")

# ================================================================== БЛОК-3: Контрольная проверка ==================================================================================================
def ControlCheck(message):
    global error_data
    markup = types.InlineKeyboardMarkup()
    buttonOk = types.InlineKeyboardButton('✅', callback_data='dataIsCorrect')
    buttonNotOk = types.InlineKeyboardButton('❌', callback_data='dataIsNotCorrect')
    markup.add(buttonOk, buttonNotOk)
    bot.send_message(message.chat.id, 
    f"<b>Проверьте, всё ли корректно?</b>\n <u>Тип ошибки:</u>\n {error_data['errorType']}\n <u>EAN:</u>\n {error_data['fixEAN']}\n <u>Место ошибки:</u>\n {error_data['fixCell']}", parse_mode='html', reply_markup=markup)

# ================================================================== БЛОК-4: Отправка формы на гугл таблицы ==================================================================================================
# credentials = ServiceAccountCredentials.from_json_keyfile_name(
#     CREDENTIALS_FILE,
#     []
# )

# Команда, для непрерывной работы скрипта.
bot.polling(non_stop=True) # Так же можно использовать команду bot.infinity_polling()
